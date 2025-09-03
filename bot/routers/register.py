from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from datetime import datetime, timedelta
from typing import Dict

from bot.database.repositories import UserRepository, PatientRepository
from bot.database.models import Patient
from bot.api.client import GorzdravAPIClient, GorzdravAPIException
from bot.api.utils import validate_phone, format_phone, parse_date
from bot.api.models import PatientAppointmentsResponse, PatientUpdateRequest

router = Router(name="register")


def yes_no_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]],
        resize_keyboard=True,
        one_time_keyboard=True,
        selective=True,
    )


class RegistrationStates(StatesGroup):
    waiting_for_last_name = State()
    waiting_for_first_name = State()
    waiting_for_middle_name = State()
    waiting_for_birth_date = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    choose_lpu_confirm = State()
    waiting_for_district = State()
    waiting_for_lpu = State()


@router.message(Command("register"))
async def register_handler(message: Message, state: FSMContext):
    """Начинает процесс регистрации пользователя"""
    if not message.from_user:
        raise ValueError("Message from user is required")

    user_id = message.from_user.id

    try:
        user_repo = UserRepository()

        # Проверяем, зарегистрирован ли уже пользователь
        existing_user = await user_repo.get_user_by_id(user_id)
        if existing_user and existing_user.is_registered:
            await message.answer("Вы уже зарегистрированы в системе!")
            return

        # Создаем или обновляем пользователя
        user_data = {
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
        }

        await user_repo.get_or_create_user(user_id, None, **user_data)

        # Переходим к сбору данных пациента
        await state.set_state(RegistrationStates.waiting_for_last_name)
        await message.answer("Введите вашу фамилию (только буквы):")

    except Exception:
        logger.exception(f"Ошибка при регистрации пользователя {user_id}")
        await message.answer("Произошла ошибка при регистрации. Попробуйте позже.")


@router.message(RegistrationStates.waiting_for_last_name)
async def last_name_handler(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text or not all(ch.isalpha() or ch in " -" for ch in text) or len(text) < 2:
        await message.answer("Некорректная фамилия. Введите снова:")
        return
    await state.update_data(last_name=text.title())
    await state.set_state(RegistrationStates.waiting_for_first_name)
    await message.answer("Введите ваше имя:")


@router.message(RegistrationStates.waiting_for_first_name)
async def first_name_handler(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not all(ch.isalpha() or ch in " -" for ch in text) or len(text) < 2:
        await message.answer("Некорректное имя. Введите снова:")
        return
    await state.update_data(first_name=text.title())
    await state.set_state(RegistrationStates.waiting_for_middle_name)
    await message.answer("Введите ваше отчество (если нет, напишите: Нет):")


@router.message(RegistrationStates.waiting_for_middle_name)
async def middle_name_handler(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    value = None if text.lower() == "нет" else text
    if value and (
        not all(ch.isalpha() or ch in " -" for ch in value) or len(value) < 2
    ):
        await message.answer("Некорректное отчество. Введите снова или напишите: Нет")
        return
    await state.update_data(middle_name=(value.title() if value else ""))
    await state.set_state(RegistrationStates.waiting_for_birth_date)
    await message.answer("Введите дату рождения в формате ДД.ММ.ГГГГ:")


@router.message(RegistrationStates.waiting_for_birth_date)
async def birth_date_handler(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    parsed = parse_date(text)
    if not parsed:
        await message.answer("Неверный формат. Введите дату как ДД.ММ.ГГГГ:")
        return
    birth_dt = datetime(parsed.year, parsed.month, parsed.day)
    await state.update_data(birth_date=birth_dt.isoformat())
    await state.set_state(RegistrationStates.waiting_for_phone)
    await message.answer("Введите номер телефона в формате +7XXXXXXXXXX:")


@router.message(RegistrationStates.waiting_for_phone)
async def phone_handler(message: Message, state: FSMContext):
    """Обрабатывает ввод номера телефона"""
    phone_raw = message.text or ""
    if not validate_phone(phone_raw):
        await message.answer(
            "Пожалуйста, укажите корректный номер телефона в формате +7XXXXXXXXXX"
        )
        return
    phone_fmt = format_phone(phone_raw)
    await state.update_data(phone=phone_fmt)
    await state.set_state(RegistrationStates.waiting_for_email)
    await message.answer("Отлично! Теперь укажите ваш email адрес (или напишите: Нет):")


@router.message(
    RegistrationStates.waiting_for_email,
    F.text.regexp(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
)
async def email_handler(message: Message, state: FSMContext):
    """Завершает регистрацию пользователя"""
    email = message.text
    if not message.from_user:
        await message.answer("Техническая ошибка: отсутствует пользователь сообщения")
        return
    user_id = message.from_user.id

    try:
        # Сохраняем email в состоянии и переходим к выбору района
        await state.update_data(email=email)

        async with GorzdravAPIClient() as client:
            districts = (await client.get_districts()).result
        mapping: Dict[str, str] = {d.name: d.id for d in districts}
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=name)] for name in mapping.keys()],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await state.update_data(districts_map=mapping)
        await state.set_state(RegistrationStates.waiting_for_district)
        await message.answer(
            "Выберите район для закрепления ЛПУ:",
            reply_markup=kb,
        )

    except Exception as e:
        logger.error(f"Ошибка при завершении регистрации пользователя {user_id}: {e}")
        await message.answer(
            "Произошла ошибка при завершении регистрации. Попробуйте позже."
        )


@router.message(RegistrationStates.waiting_for_email)
async def invalid_email_handler(message: Message, state: FSMContext):
    """Обрабатывает некорректный email"""
    text = (message.text or "").strip()
    if text.lower() == "нет":
        if not message.from_user:
            await message.answer(
                "Техническая ошибка: отсутствует пользователь сообщения"
            )
            return
        user_id = message.from_user.id
        try:
            async with GorzdravAPIClient() as client:
                districts = (await client.get_districts()).result
            mapping: Dict[str, str] = {d.name: d.id for d in districts}
            kb = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=name)] for name in mapping.keys()],
                resize_keyboard=True,
                one_time_keyboard=True,
            )
            await state.update_data(districts_map=mapping)
            await state.set_state(RegistrationStates.waiting_for_district)
            await message.answer(
                "Выберите район для закрепления ЛПУ:",
                reply_markup=kb,
            )

        except Exception as e:
            logger.error(
                f"Ошибка при завершении регистрации пользователя {user_id}: {e}"
            )
            await message.answer(
                "Произошла ошибка при завершении регистрации. Попробуйте позже."
            )
    else:
        await message.answer(
            "Пожалуйста, укажите корректный email адрес или напишите: Нет"
        )


@router.message(Command("profile"))
async def profile_handler(message: Message):
    """Показывает профиль пользователя"""
    if not message.from_user:
        await message.answer("Техническая ошибка: отсутствует пользователь сообщения")
        return
    user_id = message.from_user.id

    try:
        user_repo = UserRepository()
        user = await user_repo.get_user_by_id(user_id)

        if not user:
            await message.answer(
                "Вы не зарегистрированы в системе. Используйте /register для регистрации."
            )
            return

        if not user.is_registered:
            await message.answer(
                "Ваша регистрация не завершена. Используйте /register для завершения."
            )
            return

        profile_text = f"""
📋 **Ваш профиль:**

🆔 ID: `{user.id}`
👤 Имя: {user.first_name or "Не указано"}
👥 Фамилия: {user.last_name or "Не указана"}
📱 Телефон: {user.phone or "Не указан"}
📧 Email: {user.email or "Не указан"}
✅ Статус: {"Зарегистрирован" if user.is_registered else "Не завершена регистрация"}
📅 Дата регистрации: {(user.created_at + timedelta(hours=3)).strftime("%d.%m.%Y %H:%M")}
        """

        await message.answer(profile_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка при получении профиля пользователя {user_id}: {e}")
        await message.answer(
            "Произошла ошибка при получении профиля. Попробуйте позже."
        )


@router.message(Command("patient"))
async def patient_handler(message: Message):
    """Показывает данные пациента пользователя, включая информацию о ЛПУ"""
    if not message.from_user:
        await message.answer("Техническая ошибка: отсутствует пользователь сообщения")
        return
    user_id = message.from_user.id

    try:
        patient_repo = PatientRepository()
        patient = await patient_repo.get_patient_by_user(user_id)

        if not patient:
            await message.answer(
                "У вас пока нет добавленных данных пациента. Используйте /add_patient для добавления."
            )
            return

        lpu_info = "Не указана"
        if patient.prefer_lpu_id:
            try:
                async with GorzdravAPIClient() as client:
                    lpu = await client.get_lpu_by_id(int(patient.prefer_lpu_id))
                if lpu:
                    lpu_info = f"{lpu.lpuShortName}"
                    if lpu.address:
                        lpu_info += f"\n📍 Адрес: {lpu.address}"
                    if lpu.phone:
                        lpu_info += f"\n☎ Телефон: {lpu.phone}"
                else:
                    lpu_info = f"ЛПУ с ID {patient.prefer_lpu_id} не найдено"
            except Exception as e:
                logger.error(f"Ошибка при получении ЛПУ для пациента {user_id}: {e}")
                lpu_info = f"Ошибка при получении ЛПУ (ID {patient.prefer_lpu_id})"

        patient_text = f"""
👤 **Данные пациента:**

📝 ФИО: {patient.last_name} {patient.first_name} {patient.middle_name}
📅 Дата рождения: {patient.birth_date.strftime("%d.%m.%Y")}
🏥 Предпочитаемая поликлиника: {lpu_info}
🆔 ID в Горздрав: {patient.gorzdrav_id or "Не указан"}
        """

        await message.answer(patient_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(
            f"Ошибка при получении данных пациента пользователя {user_id}: {e}"
        )
        await message.answer(
            "Произошла ошибка при получении данных пациента. Попробуйте позже."
        )


@router.message(RegistrationStates.choose_lpu_confirm)
async def choose_lpu_confirm_handler(message: Message, state: FSMContext):
    # Выбор ЛПУ обязателен: сразу переводим к выбору района
    try:
        async with GorzdravAPIClient() as client:
            districts = (await client.get_districts()).result
        mapping = {d.name: d.id for d in districts}
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=name)] for name in mapping.keys()],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await state.update_data(districts_map=mapping)
        await state.set_state(RegistrationStates.waiting_for_district)
        await message.answer("Выберите район:", reply_markup=kb)
    except Exception as e:
        logger.error(f"Ошибка получения районов: {e}")
        await message.answer(
            "Не удалось получить районы. Попробуйте позже.",
            reply_markup=ReplyKeyboardRemove(),
        )


@router.message(RegistrationStates.waiting_for_district)
async def district_choice_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    mapping: Dict[str, str] = data.get("districts_map", {})
    district_name = (message.text or "").strip()
    if district_name not in mapping:
        await message.answer("Выберите район из списка ниже:")
        return
    district_id = mapping[district_name]
    await state.update_data(selected_district_id=district_id)

    # Загружаем ЛПУ по району
    try:
        async with GorzdravAPIClient() as client:
            lpus = (await client.get_lpus_by_district(int(district_id))).result
        if not lpus:
            await message.answer("В выбранном районе нет ЛПУ. Выберите другой район:")
            return
        # Строим клавиатуру ID — shortName
        options = {f"{lpu.lpuShortName}": str(lpu.id) for lpu in lpus}
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=label)] for label in options.keys()],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await state.update_data(lpus_map=options)
        await state.set_state(RegistrationStates.waiting_for_lpu)
        await message.answer("Выберите ЛПУ:", reply_markup=kb)
    except GorzdravAPIException as e:
        logger.error(f"Ошибка получения ЛПУ: {e}")
        await message.answer(
            e.message + "\n\n" + "Начните регистрацию заново: /register",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка получения ЛПУ: {e}")
        await message.answer(
            "Не удалось получить ЛПУ. Начните регистрацию заново: /register",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.clear()


@router.message(RegistrationStates.waiting_for_lpu)
async def lpu_choice_handler(message: Message, state: FSMContext):
    if not message.from_user:
        await message.answer("Техническая ошибка: отсутствует пользователь сообщения")
        return
    user_id = message.from_user.id
    data = await state.get_data()
    options: Dict[str, str] = data.get("lpus_map", {})
    label = (message.text or "").strip()
    if label not in options:
        await message.answer("Выберите ЛПУ из списка:")
        return
    lpu_id = int(options[label])

    # Если это регистрационный поток — ищем пациента в ГЗ и только при успехе завершаем регистрацию
    try:
        reg_last_name = data.get("last_name")
        reg_first_name = data.get("first_name")
        reg_middle_name = data.get("middle_name") or ""
        birth_date_iso = data.get("birth_date")
        phone = data.get("phone")
        email = data.get("email")

        if reg_last_name and birth_date_iso and reg_first_name is not None:
            async with GorzdravAPIClient() as client:
                d = datetime.fromisoformat(birth_date_iso)
                iso = d.strftime("%Y-%m-%dT00:00:00")
                dmy = d.strftime("%d.%m.%Y")
                try:
                    search = await client.search_patient(
                        lpu_id=lpu_id,
                        last_name=reg_last_name,
                        first_name=reg_first_name,
                        middle_name=reg_middle_name,
                        birthdate_iso=iso,
                        birthdate_value=dmy,
                    )
                    if not search.success or not search.result:
                        await message.answer(
                            "Пациент не найден в системе ГорЗдрав. Проверьте данные и выберите другое ЛПУ."
                        )
                        return
                except GorzdravAPIException as e:
                    logger.error(f"Ошибка при поиске пациента: {e}")
                    await state.clear()
                    await message.answer(
                        e.message + "\n\n" + "Начните регистрацию заново: /register",
                        reply_markup=ReplyKeyboardRemove(),
                    )
                    return

                gorzdrav_id = search.result

            user_repo = UserRepository()
            await user_repo.update_user(user_id, None, phone=phone, email=email)

            patient_repo = PatientRepository()
            # создаем нового пациента
            await patient_repo.create_patient(
                patient=Patient(
                    user_id=user_id,
                    last_name=reg_last_name,
                    first_name=reg_first_name,
                    middle_name=reg_middle_name,
                    birth_date=datetime.fromisoformat(birth_date_iso),
                    gorzdrav_id=gorzdrav_id,
                    prefer_lpu_id=str(lpu_id),
                )
            )

            # Обновим телефон в ГЗ
            if phone:
                async with GorzdravAPIClient() as client:
                    digits = "".join(ch for ch in phone if ch.isdigit())
                    if digits.startswith("7") and len(digits) == 11:
                        try:
                            await client.update_patient(
                                PatientUpdateRequest(
                                    lpuId=lpu_id,
                                    patientId=gorzdrav_id,
                                    mobilePhoneNumber=digits[1:],
                                )
                            )
                        except Exception as e:
                            logger.warning(
                                f"Не удалось обновить телефон пациента в ГЗ: {e}"
                            )

            await message.answer(
                "Регистрация завершена. ЛПУ закреплено.",
                reply_markup=ReplyKeyboardRemove(),
            )
            await state.clear()
            return

        else:
            await message.answer(
                "Не удалось завершить регистрацию. Начните регистрацию заново: /register"
            )
            await state.clear()
            return

    except GorzdravAPIException as e:
        logger.error(f"Ошибка при сохранении ЛПУ/пациента: {e}")
        await message.answer(
            e.message + "\n\n" + "Начните регистрацию заново: /pin_lpu",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при сохранении ЛПУ/пациента: {e}")
        await message.answer(
            "Не удалось сохранить ЛПУ. Начните регистрацию заново: /register",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.clear()


@router.message(Command("appointments"))
async def appointments_handler(message: Message):
    """Показывает список записей пациента через API"""
    if not message.from_user:
        return
    user_id = message.from_user.id

    patient_repo = PatientRepository()
    patient = await patient_repo.get_patient_by_user(user_id)
    if not patient or not patient.gorzdrav_id:
        await message.answer("Сначала пройдите регистрацию: /register")
        return

    try:
        async with GorzdravAPIClient() as client:
            resp: PatientAppointmentsResponse = await client.get_patient_appointments(
                lpu_id=int(patient.prefer_lpu_id), patient_id=patient.gorzdrav_id
            )
        if not resp.result:
            await message.answer("У вас нет активных записей.")
            return

        lines: list[str] = []
        for _, item in enumerate(resp.result[:10], 1):
            when = (
                item.visitStart.strftime("%d.%m.%Y %H:%M") if item.visitStart else "—"
            )
            doctor = (
                item.doctorRendingConsultation.name
                if item.doctorRendingConsultation
                and item.doctorRendingConsultation.name
                else "Врач"
            )
            spec = (
                item.specialityRendingConsultation.name
                if item.specialityRendingConsultation
                and item.specialityRendingConsultation.name
                else "Специализация"
            )
            lpu_line = item.lpuShortName or "ЛПУ не указано"
            addr = item.lpuAddress or "Адрес не указан"
            phone = f"☎ {item.lpuPhone}" if item.lpuPhone else ""
            room = (
                f"Кабинет: {item.positionRendingConsultation.name}"
                if item.positionRendingConsultation
                and item.positionRendingConsultation.name
                else ""
            )
            status = f"Статус: {item.status}" if item.status else ""
            # Можно добавить номер записи, если нужно: item.appointmentId

            text = (
                f"🗓 <b>{when}</b>\n"
                f"👨‍⚕️ <b>{doctor}</b> ({spec})\n"
                f"🏥 <b>{lpu_line}</b>\n"
                f"📍 {addr}\n"
            )
            if room:
                text += f"🚪 {room}\n"
            if phone:
                text += f"{phone}\n"
            if status:
                text += f"{status}\n"

            lines.append(text.strip())

        await message.answer(
            "<b>Ваши записи на приём:</b>\n\n" + "\n\n".join(lines),
        )
    except Exception as e:
        logger.error(f"/appointments error: {e}")
        await message.answer("Не удалось получить список записей. Попробуйте позже.")
