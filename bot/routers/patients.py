import contextlib
from datetime import datetime
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InaccessibleMessage,
    Message,
)
from loguru import logger

from bot.api.client import GorzdravAPIClient, GorzdravAPIError
from bot.api.utils import format_phone, validate_phone
from bot.db.context import get_or_create_session
from bot.db.services import PatientsService, UsersService
from bot.settings.settings import settings
from bot.utils.callbacks import (
    PatientsMenuFactory,
)
from bot.utils.keyboards import (
    get_add_patient_keyboard,
    get_patient_delete_keyboard,
    get_patient_deleted_keyboard,
    get_patient_view_keyboard,
    get_patients_cancel_back_keyboard,
    get_patients_cancel_back_skip_keyboard,
    get_patients_cancel_keyboard,
    get_patients_keyboard,
)
from bot.utils.states import PatientFormStates

if TYPE_CHECKING:
    from bot.api.models import Attachment
    from bot.db.models.users import User

router = Router(name="patients")


def get_tariff_info(user: "User") -> str:
    """Return information about the user's tariff."""
    if hasattr(user, "is_subscribed") and user.is_subscribed:
        patients_count = len(getattr(user, "patients", []))
        # Склонение для слова "пациент"
        if patients_count % 10 == 1 and patients_count % 100 != 11:
            patients_word = "пациент"
        elif patients_count % 10 in [2, 3, 4] and patients_count % 100 not in [
            12,
            13,
            14,
        ]:
            patients_word = "пациента"
        else:
            patients_word = "пациентов"

        return (
            f"<b>💳 Платный тариф:</b> "
            f"{patients_count}/{settings.MAX_SUBSCRIBED_PATIENTS} {patients_word}"
        )

    patients_count = len(getattr(user, "patients", []))
    # Склонение для слова "пациент"
    if patients_count % 10 == 1 and patients_count % 100 != 11:
        patients_word = "пациент"
    elif patients_count % 10 in [2, 3, 4] and patients_count % 100 not in [12, 13, 14]:
        patients_word = "пациента"
    else:
        patients_word = "пациентов"

    return (
        f"<b>🆓 Бесплатный тариф:</b> "
        f"{patients_count}/{settings.MAX_UNSUBSCRIBED_PATIENTS} {patients_word}"
    )


async def get_filled_data_text(state: FSMContext) -> str:
    """Return text with filled data."""
    text = "📋 <b>Заполненные данные:</b>\n"

    data = await state.get_data()
    if data.get("last_name"):
        text += f"👤 Фамилия: {data['last_name']}\n"
    if data.get("first_name"):
        text += f"👤 Имя: {data['first_name']}\n"
    if data.get("middle_name"):
        text += f"👤 Отчество: {data['middle_name']}\n"
    if data.get("birth_date"):
        birth_date = datetime.fromisoformat(data["birth_date"])
        text += f"📅 Дата рождения: {birth_date.strftime('%d.%m.%Y')}\n"
    if data.get("phone"):
        text += f"📞 Телефон: {data['phone']}\n"
    if data.get("email"):
        text += f"📧 Email: {data['email']}\n"

    text += "\n" + "─" * 20 + "\n\n"
    return text


async def send_patients_menu(
    user_id: int,
    message: Message,
    *,
    edit_message: bool = False,
) -> Message:
    """Set the patients menu."""
    async with get_or_create_session() as session:
        users_service = UsersService(session)
        patients_service = PatientsService(session)

        user = await users_service.get_user_by_id(user_id)
        if not user:
            if edit_message:
                await message.edit_text(
                    "❌ Пользователь не найден. Используйте /start для регистрации.",
                )
                return message
            return await message.answer(
                "❌ Пользователь не найден. Используйте /start для регистрации.",
            )

        patients = await patients_service.get_patients_by_user_id(user_id)
        same_day_info = (
            "📋 <b>О настройке записи в текущий день:</b>\n\n"
            "• ✅ <b>Включена:</b> бот будет искать свободные слоты на "
            "<u>сегодня и позже</u>\n"
            "  <i>Например, если освободится талончик через час, "
            "бот запишет вас</i>\n\n"
            "• 🚫 <b>Выключена:</b> бот будет искать записи только на "
            "<u>завтра и позже</u>\n\n"
            "💡 <i>Для изменения настройки используйте кнопку ниже</i>\n\n"
        )

        if not patients:
            text = (
                f"👥 <b>Ваши пациенты</b>\n\n{get_tariff_info(user)}\n\n"
                f"{same_day_info}"
                'У вас нет добавленных пациентов. Нажмите "Добавить пациента".'
            )
            keyboard = get_add_patient_keyboard()
        else:
            text = (
                f"👥 <b>Ваши пациенты</b>\n\n{get_tariff_info(user)}\n\n{same_day_info}"
            )
            keyboard = get_patients_keyboard(patients, user)

        if edit_message:
            await message.edit_text(text, reply_markup=keyboard)
            return message
        return await message.answer(text, reply_markup=keyboard)


@router.message(Command("patients"))
@router.message(F.text == "👥 Пациенты")
async def patients_handler(message: Message) -> None:
    """Показывает меню пациентов."""
    if not message.from_user:
        await message.answer(
            "❌ Техническая ошибка: отсутствует пользователь сообщения",
        )
        return

    user_id = message.from_user.id

    try:
        await send_patients_menu(user_id, message)
    except Exception as e:
        logger.error(
            f"Ошибка при получении списка пациентов для пользователя {user_id}: {e}",
        )
        await message.answer(
            "❌ Произошла ошибка при получении списка пациентов. Попробуйте позже.",
        )


@router.callback_query(PatientsMenuFactory.filter(F.action == "list"))
async def list_patients_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает меню пациентов."""
    await callback.answer()
    if not callback.message or isinstance(callback.message, InaccessibleMessage):
        return
    await send_patients_menu(callback.from_user.id, callback.message, edit_message=True)


@router.callback_query(PatientsMenuFactory.filter(F.action == "add"))
async def add_patient_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начинает процесс добавления пациента."""
    await callback.answer()

    if (
        not callback.from_user
        or not callback.message
        or isinstance(callback.message, InaccessibleMessage)
    ):
        return

    user_id = callback.from_user.id

    try:
        async with get_or_create_session() as session:
            users_service = UsersService(session)
            patients_service = PatientsService(session)

            # Получаем пользователя
            user = await users_service.get_user_by_id(user_id)
            if not user:
                if callback.message:
                    await callback.message.edit_text(
                        "❌ Пользователь не найден. "
                        "Используйте /start для регистрации.",
                    )
                return

            # Проверяем лимит пациентов
            patients = await patients_service.get_patients_by_user_id(user_id)
            max_patients = (
                settings.MAX_SUBSCRIBED_PATIENTS
                if user.is_subscribed
                else settings.MAX_UNSUBSCRIBED_PATIENTS
            )

            if len(patients) >= max_patients:
                if user.is_subscribed:
                    await callback.message.edit_text(
                        f"❌ <b>Лимит пациентов достигнут</b>\n\n"
                        f"📊 Текущий лимит: "
                        f"{settings.MAX_SUBSCRIBED_PATIENTS}/"
                        f"{settings.MAX_SUBSCRIBED_PATIENTS} "
                        "пациентов",
                    )
                    return
                await callback.message.edit_text(
                    f"❌ <b>Лимит пациентов достигнут</b>\n\n"
                    f"📊 Текущий лимит: "
                    f"{settings.MAX_UNSUBSCRIBED_PATIENTS}/"
                    f"{settings.MAX_UNSUBSCRIBED_PATIENTS} "
                    "пациент",
                    "💎 Для увеличения лимита оформите подписку: /subscribe",
                )
                return
            # Начинаем форму добавления
            await state.set_state(PatientFormStates.waiting_for_last_name)
            await state.update_data(message_id=callback.message.message_id)
            await callback.message.edit_text(
                "📝 <b>Введите фамилию пациента:</b>\n\n"
                "💡 <i>Используйте только буквы русского или латинского алфавита</i>",
                reply_markup=get_patients_cancel_keyboard(),
            )

    except Exception as e:
        logger.error(
            f"Ошибка при начале добавления пациента для пользователя {user_id}: {e}",
        )
        if callback.message:
            await callback.message.edit_text(
                "❌ Произошла ошибка при добавлении пациента. Попробуйте позже.",
            )


@router.callback_query(PatientsMenuFactory.filter(F.action == "cancel"))
async def cancel_patient_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает кнопку 'Отмена'."""
    await callback.answer()
    await state.clear()
    if not callback.message or isinstance(callback.message, InaccessibleMessage):
        return
    await send_patients_menu(callback.from_user.id, callback.message, edit_message=True)


@router.callback_query(PatientsMenuFactory.filter(F.action == "back"))
async def back_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает кнопку 'Назад'."""
    await callback.answer()
    if not callback.message or isinstance(callback.message, InaccessibleMessage):
        return

    current_state = await state.get_state()
    if not current_state:
        return

    filled_data = await get_filled_data_text(state)

    match current_state:
        case PatientFormStates.waiting_for_first_name:
            await state.set_state(PatientFormStates.waiting_for_last_name)

            await callback.message.edit_text(
                filled_data + "📝 <b>Введите фамилию пациента:</b>\n\n"
                "💡 <i>Используйте только буквы русского или "
                "латинского алфавита</i>",
                reply_markup=get_patients_cancel_keyboard(),
            )
        case PatientFormStates.waiting_for_middle_name:
            await state.set_state(PatientFormStates.waiting_for_first_name)

            await callback.message.edit_text(
                filled_data + "📝 <b>Введите имя пациента:</b>\n\n"
                "💡 <i>Используйте только буквы русского или "
                "латинского алфавита</i>",
                reply_markup=get_patients_cancel_back_keyboard(),
            )
        case PatientFormStates.waiting_for_birth_date:
            await state.set_state(PatientFormStates.waiting_for_middle_name)

            await callback.message.edit_text(
                (
                    filled_data + "📝 <b>Введите отчество пациента:</b>\n\n"
                    '💡 <i>Введите отчество или нажмите "Пропустить", '
                    "если отчества нет</i>"
                ),
                reply_markup=get_patients_cancel_back_skip_keyboard(),
            )
        case PatientFormStates.waiting_for_phone:
            await state.set_state(PatientFormStates.waiting_for_birth_date)

            await callback.message.edit_text(
                filled_data + "📅 <b>Введите дату рождения пациента:</b>\n\n"
                "📝 <i>Формат: ДД.ММ.ГГГГ (например, 15.06.1990)</i>",
                reply_markup=get_patients_cancel_back_keyboard(),
            )
        case PatientFormStates.waiting_for_email:
            await state.set_state(PatientFormStates.waiting_for_phone)

            await callback.message.edit_text(
                filled_data + "📝 <b>Введите номер телефона пациента:</b>\n\n"
                "💡 <i>Формат: +7XXXXXXXXXX (например, +79161234567)</i>",
                reply_markup=get_patients_cancel_back_skip_keyboard(),
            )
        case PatientFormStates.waiting_for_oms:
            await state.set_state(PatientFormStates.waiting_for_email)

            await callback.message.edit_text(
                text=(
                    filled_data + "📧 <b>Введите email пациента:</b>\n\n"
                    "💡 <i>На указанный email будет отправлен талон из "
                    "Горздрава после записи к врачу</i>\n\n"
                ),
                reply_markup=get_patients_cancel_back_keyboard(),
            )
        case _:
            pass


@router.callback_query(PatientsMenuFactory.filter(F.action == "skip"))
async def skip_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает кнопку 'Пропустить'."""
    await callback.answer()
    if not callback.message or isinstance(callback.message, InaccessibleMessage):
        return

    current_state = await state.get_state()
    filled_data = await get_filled_data_text(state)

    if current_state == PatientFormStates.waiting_for_middle_name:
        await state.update_data(middle_name="")
        await state.set_state(PatientFormStates.waiting_for_birth_date)

        await callback.message.edit_text(
            filled_data + "📅 <b>Введите дату рождения пациента:</b>\n\n"
            "📝 <i>Формат: ДД.ММ.ГГГГ (например, 15.06.1990)</i>",
            reply_markup=get_patients_cancel_back_keyboard(),
        )
    elif current_state == PatientFormStates.waiting_for_phone:
        await state.update_data(phone="")
        await state.set_state(PatientFormStates.waiting_for_email)

        await callback.message.edit_text(
            (
                filled_data + "📧 <b>Введите email пациента:</b>\n\n"
                "💡 <i>На указанный email будет отправлен талон из "
                "Горздрава после записи к врачу</i>\n\n"
            ),
            reply_markup=get_patients_cancel_back_keyboard(),
        )


@router.message(PatientFormStates.waiting_for_last_name)
async def last_name_handler(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод фамилии."""
    text = (message.text or "").strip()
    data = await state.get_data()
    filled_data = await get_filled_data_text(state)
    message_id = data.get("message_id")

    if not message_id:
        await message.answer(
            "❌ <b>Ошибка:</b> не найдено сообщение для редактирования.",
        )
        return
    if not message.bot:
        return

    with contextlib.suppress(Exception):
        await message.delete()

    if not text or not all(ch.isalpha() or ch in " -" for ch in text) or len(text) < 2:
        with contextlib.suppress(Exception):
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=(
                    filled_data + "❌ <b>Некорректная фамилия!</b>\n\n"
                    "📝 Пожалуйста, введите фамилию заново:\n\n"
                    "💡 <i>Используйте только буквы русского или "
                    "латинского алфавита, минимум 2 символа</i>"
                ),
                reply_markup=get_patients_cancel_keyboard(),
            )
        return

    await state.update_data(last_name=text.title())
    filled_data = await get_filled_data_text(state)
    await state.set_state(PatientFormStates.waiting_for_first_name)

    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message_id,
        text=(
            filled_data + "📝 <b>Введите имя пациента:</b>\n\n"
            "💡 <i>Используйте только буквы русского или "
            "латинского алфавита</i>"
        ),
        reply_markup=get_patients_cancel_back_keyboard(),
    )


@router.message(PatientFormStates.waiting_for_first_name)
async def first_name_handler(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод имени."""
    text = (message.text or "").strip()
    data = await state.get_data()
    filled_data = await get_filled_data_text(state)
    message_id = data.get("message_id")

    if not message_id:
        await message.answer(
            "❌ <b>Ошибка:</b> не найдено сообщение для редактирования.",
        )
        return
    if not message.bot:
        return

    with contextlib.suppress(Exception):
        await message.delete()

    if not text or not all(ch.isalpha() or ch in " -" for ch in text) or len(text) < 2:
        with contextlib.suppress(Exception):
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=(
                    filled_data + "❌ <b>Некорректное имя!</b>\n\n"
                    "📝 Пожалуйста, введите имя заново:\n\n"
                    "💡 <i>Используйте только буквы русского или "
                    "латинского алфавита, минимум 2 символа</i>"
                ),
                reply_markup=get_patients_cancel_back_keyboard(),
            )
        return

    await state.update_data(first_name=text.title())
    filled_data = await get_filled_data_text(state)
    await state.set_state(PatientFormStates.waiting_for_middle_name)

    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message_id,
        text=(
            filled_data + "📝 <b>Введите отчество пациента:</b>\n\n"
            '💡 <i>Введите отчество или нажмите "Пропустить", если отчества нет</i>'
        ),
        reply_markup=get_patients_cancel_back_skip_keyboard(),
    )


@router.message(PatientFormStates.waiting_for_middle_name)
async def middle_name_handler(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод отчества."""
    text = (message.text or "").strip()
    data = await state.get_data()
    filled_data = await get_filled_data_text(state)
    message_id = data.get("message_id")

    if not message_id:
        await message.answer(
            "❌ <b>Ошибка:</b> не найдено сообщение для редактирования.",
        )
        return
    if not message.bot:
        return
    with contextlib.suppress(Exception):
        await message.delete()

    if text and (not all(ch.isalpha() or ch in " -" for ch in text) or len(text) < 2):
        with contextlib.suppress(Exception):
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=(
                    filled_data + "❌ <b>Некорректное отчество!</b>\n\n"
                    "📝 Пожалуйста, введите отчество заново или нажмите 'Пропустить', "
                    "если отчества нет: \n\n"
                    "💡 <i>Используйте только буквы русского или "
                    "латинского алфавита, минимум 2 символа</i>"
                ),
                reply_markup=get_patients_cancel_back_skip_keyboard(),
            )
        return

    await state.update_data(middle_name=(text.title()))
    filled_data = await get_filled_data_text(state)
    await state.set_state(PatientFormStates.waiting_for_birth_date)

    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message_id,
        text=(
            filled_data + "📝 <b>Введите дату рождения пациента:</b>\n\n"
            "💡 <i>Формат: ДД.ММ.ГГГГ (например, 15.03.1990)</i>"
        ),
        reply_markup=get_patients_cancel_back_keyboard(),
    )


@router.message(PatientFormStates.waiting_for_birth_date)
async def birth_date_handler(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод даты рождения."""
    text = (message.text or "").strip()
    data = await state.get_data()
    filled_data = await get_filled_data_text(state)
    message_id = data.get("message_id")

    if not message_id:
        await message.answer(
            "❌ <b>Ошибка:</b> не найдено сообщение для редактирования.",
        )
        return
    if not message.bot:
        return
    # Удаляем сообщение пользователя
    with contextlib.suppress(Exception):
        await message.delete()

    # Парсим дату в формате ДД.ММ.ГГГГ
    try:
        date_parts = text.split(".")
        if len(date_parts) != 3:
            raise ValueError("Неверный формат даты")

        day, month, year = map(int, date_parts)
        birth_dt = datetime(year, month, day)

        # Проверяем, что дата не в будущем
        if birth_dt > datetime.now():
            raise ValueError("Дата рождения не может быть в будущем")

    except (ValueError, TypeError):
        with contextlib.suppress(Exception):
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=(
                    filled_data + "❌ <b>Неверный формат даты!</b>\n\n"
                    "📝 <b>Введите дату рождения пациента:</b>\n\n"
                    "💡 <i>Формат: ДД.ММ.ГГГГ (например, 15.03.1990)</i>"
                ),
                reply_markup=get_patients_cancel_back_keyboard(),
            )
        return

    await state.update_data(birth_date=birth_dt.isoformat())
    filled_data = await get_filled_data_text(state)
    await state.set_state(PatientFormStates.waiting_for_phone)

    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message_id,
        text=(
            filled_data + "📝 <b>Введите номер телефона пациента:</b>\n\n"
            "💡 <i>Формат: +7XXXXXXXXXX (например, +79161234567)</i>"
        ),
        reply_markup=get_patients_cancel_back_skip_keyboard(),
    )


@router.message(PatientFormStates.waiting_for_phone)
async def phone_handler(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод номера телефона."""
    text = (message.text or "").strip()
    data = await state.get_data()
    filled_data = await get_filled_data_text(state)
    message_id = data.get("message_id")

    if not message_id:
        await message.answer(
            "❌ <b>Ошибка:</b> не найдено сообщение для редактирования.",
        )
        return
    if not message.bot:
        return
    # Удаляем сообщение пользователя
    with contextlib.suppress(Exception):
        await message.delete()

    if not validate_phone(text):
        with contextlib.suppress(Exception):
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=(
                    filled_data + "❌ <b>Неверный формат номера телефона!</b>\n\n"
                    "📝 <b>Введите номер телефона пациента:</b>\n\n"
                    "💡 <i>Формат: +7XXXXXXXXXX (например, +79161234567)</i>"
                ),
                reply_markup=get_patients_cancel_back_skip_keyboard(),
            )
        return

    phone_fmt = format_phone(text)
    await state.update_data(phone=phone_fmt)
    filled_data = await get_filled_data_text(state)
    await state.set_state(PatientFormStates.waiting_for_email)

    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message_id,
        text=(
            filled_data + "📧 <b>Введите email пациента:</b>\n\n"
            "💡 <i>На указанный email будет отправлен талон из "
            "Горздрава после записи к врачу</i>\n\n"
        ),
        reply_markup=get_patients_cancel_back_keyboard(),
    )


@router.message(PatientFormStates.waiting_for_email)
async def email_handler(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод email."""
    text = (message.text or "").strip()
    data = await state.get_data()
    filled_data = await get_filled_data_text(state)
    message_id = data.get("message_id")

    if not message_id:
        await message.answer(
            "❌ <b>Ошибка:</b> не найдено сообщение для редактирования.",
        )
        return
    if not message.bot:
        return
    # Удаляем сообщение пользователя
    with contextlib.suppress(Exception):
        await message.delete()

    # Валидация и сохранение email
    if text.lower() == "нет":
        await state.update_data(email=None)
    else:
        # Простая проверка email
        if "@" not in text or "." not in text.split("@")[1]:
            with contextlib.suppress(Exception):
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=message_id,
                    text=(
                        filled_data + "❌ <b>Некорректный email!</b>\n\n"
                        "📧 <b>Введите email пациента:</b>\n\n"
                        "💡 <i>На указанный email будет отправлен талон из "
                        "Горздрава после записи к врачу</i>\n\n"
                    ),
                    reply_markup=get_patients_cancel_back_keyboard(),
                )

            return
        await state.update_data(email=text)

    filled_data = await get_filled_data_text(state)
    await state.set_state(PatientFormStates.waiting_for_oms)

    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message_id,
        text=(
            filled_data + "🆔 <b>Введите данные полиса ОМС:</b>\n\n"
            "📋 <b>Для полисов старого образца:</b>\n"
            "💡 <i>Формат: Серия Номер (например: 1234567890 1234567890)</i>\n\n"
            "📋 <b>Для полисов нового образца (16 цифр):</b>\n"
            "💡 <i>Формат: 1234567890123456</i>\n\n"
            "ℹ️ <i>Серию необходимо указывать только для полисов старого образца</i>"
        ),
        reply_markup=get_patients_cancel_back_keyboard(),
    )


@router.message(PatientFormStates.waiting_for_oms)
async def oms_handler(
    message: Message, state: FSMContext
) -> None:  # noqa: C901, PLR0911, PLR0912, PLR0915
    """Handles input of OMS data."""
    text = (message.text or "").strip()
    data = await state.get_data()
    filled_data = await get_filled_data_text(state)
    message_id = data.get("message_id")

    if not message_id:
        await message.answer(
            "❌ <b>Ошибка:</b> не найдено сообщение для редактирования.",
        )
        return
    if not message.bot:
        return
    if not message.from_user:
        return
    # Remove user message
    with contextlib.suppress(Exception):
        await message.delete()

    # Validate OMS data
    if not text or len(text.replace(" ", "")) < 10:
        with contextlib.suppress(Exception):
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=(
                    filled_data + "❌ <b>Некорректные данные полиса ОМС!</b>\n\n"
                    "🆔 <b>Введите данные полиса ОМС:</b>\n\n"
                    "📋 <b>Для полисов старого образца:</b>\n"
                    "💡 <i>Формат: Серия Номер "
                    "(например: 1234567890 1234567890)</i>\n\n"
                    "📋 <b>Для полисов нового образца (16 цифр):</b>\n"
                    "💡 <i>Формат: 1234567890123456</i>\n\n"
                    "ℹ️ <i>Серию необходимо указывать только для "
                    "полисов старого образца</i>"
                ),
                reply_markup=get_patients_cancel_back_keyboard(),
            )
        return

    # Parse OMS data
    parts = text.split()
    if len(parts) == 2:
        # Old sample policy: series and number
        polis_s, polis_n = parts
        await state.update_data(polis_s=polis_s, polis_n=polis_n)
    elif len(parts) == 1 and len(text.replace(" ", "")) == 16:
        # New sample policy: only number
        await state.update_data(polis_s="", polis_n=text.replace(" ", ""))
    else:
        with contextlib.suppress(Exception):
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=(
                    filled_data + "❌ <b>Некорректный формат полиса ОМС!</b>\n\n"
                    "🆔 <b>Введите данные полиса ОМС:</b>\n\n"
                    "📋 <b>Для полисов старого образца:</b>\n"
                    "💡 <i>Формат: Серия Номер "
                    "(например: 1234567890 1234567890)</i>\n\n"
                    "📋 <b>Для полисов нового образца (16 цифр):</b>\n"
                    "💡 <i>Формат: 1234567890123456</i>\n\n"
                    "ℹ️ <i>Серию необходимо указывать только для "
                    "полисов старого образца</i>"
                ),
                reply_markup=get_patients_cancel_back_keyboard(),
            )
        return

    # Проверяем лимит пациентов перед созданием
    try:
        async with get_or_create_session() as session:
            users_service = UsersService(session)
            patients_service = PatientsService(session)

            user = await users_service.get_user_by_id(message.from_user.id)
            if not user:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=message_id,
                    text=(
                        "❌ <b>Пользователь не найден.</b>\n\n"
                        "Используйте /start для регистрации."
                    ),
                )
                await state.clear()
                return

            patients = await patients_service.get_patients_by_user_id(
                message.from_user.id,
            )
            max_patients = (
                settings.MAX_SUBSCRIBED_PATIENTS
                if user.is_subscribed
                else settings.MAX_UNSUBSCRIBED_PATIENTS
            )

            if len(patients) >= max_patients:
                if user.is_subscribed:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=message_id,
                        text=(
                            f"❌ <b>Лимит пациентов достигнут</b>\n\n"
                            f"📊 Текущий лимит: "
                            f"{settings.MAX_SUBSCRIBED_PATIENTS}/"
                            f"{settings.MAX_SUBSCRIBED_PATIENTS} "
                            "пациентов"
                        ),
                    )
                else:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=message_id,
                        text=(
                            f"❌ <b>Лимит пациентов достигнут</b>\n\n"
                            f"📊 Текущий лимит: "
                            f"{settings.MAX_UNSUBSCRIBED_PATIENTS}/"
                            f"{settings.MAX_UNSUBSCRIBED_PATIENTS} "
                            "пациент\n\n"
                            "💎 Для увеличения лимита оформите подписку: /subscribe"
                        ),
                    )
                await state.clear()
                return
    except Exception as e:
        logger.error(f"Ошибка при проверке лимита пациентов: {e}")
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=(
                "❌ <b>Ошибка при проверке лимита пациентов.</b>\n\n"
                "Попробуйте начать заново: /patients"
            ),
        )
        await state.clear()
        return

    # Завершаем создание пациента
    try:
        patient_data = await state.get_data()
        failed_lpus: "list[tuple[Attachment, str]]" = []
        successful_lpus: "list[Attachment]" = []
        # Валидация пациента через API
        try:
            # Проверяем корректность полиса через запрос прикреплений
            async with GorzdravAPIClient() as api_client:
                attachments_response = await api_client.get_attachments(
                    polis_s=patient_data.get("polis_s"),
                    polis_n=patient_data.get("polis_n"),
                )

                if not attachments_response.success or not attachments_response.result:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=message_id,
                        text=(
                            "❌ <b>Некорректные данные полиса ОМС!</b>\n\n"
                            "<i>Проверьте правильность введенных данных полиса "
                            "и попробуйте снова.</i>\n\n"
                            "Начать заново: /patients"
                        ),
                    )
                    await state.clear()
                    return

                # Проверяем пациента во всех доступных ЛПУ
                birth_date_iso = patient_data.get("birth_date", "").replace(".", "-")

                for attachment in attachments_response.result:
                    try:
                        patient_search_response = await api_client.search_patient(
                            lpu_id=attachment.id,
                            last_name=patient_data.get("last_name", ""),
                            first_name=patient_data.get("first_name", ""),
                            middle_name=patient_data.get("middle_name", ""),
                            birthdate_iso=birth_date_iso,
                        )

                        if not (
                            patient_search_response.success
                            and patient_search_response.result
                        ):
                            failed_lpus.append(
                                (
                                    attachment,
                                    patient_search_response.message
                                    or "Неизвестная ошибка",
                                ),
                            )
                        else:
                            successful_lpus.append(attachment)
                    except GorzdravAPIError as e:
                        logger.error(
                            f"Erro while searching for a patient in LPU "
                            f"{attachment.id}: {e}",
                        )
                        failed_lpus.append((attachment, e.message))
                        continue

        except Exception as e:
            logger.error(f"Ошибка при валидации пациента: {e}")
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=(
                    "❌ <b>Ошибка при проверке данных пациента.</b>\n\n"
                    "Попробуйте начать заново: /patients"
                ),
            )
            await state.clear()
            return

        async with get_or_create_session() as session:
            patients_service = PatientsService(session)
            await patients_service.create_patient(
                {
                    "user_id": message.from_user.id,
                    "last_name": patient_data.get("last_name"),
                    "first_name": patient_data.get("first_name"),
                    "middle_name": patient_data.get("middle_name"),
                    "birth_date": datetime.fromisoformat(
                        patient_data.get("birth_date") or "",
                    ),
                    "polis_s": patient_data.get("polis_s"),
                    "polis_n": patient_data.get("polis_n"),
                    "phone": patient_data.get("phone"),
                    "email": patient_data.get("email"),
                },
            )

        # Форматируем данные для корректного отображения
        full_name = (
            f"{patient_data.get('last_name', '')} {patient_data.get('first_name', '')}"
        )
        if patient_data.get("middle_name"):
            full_name += f" {patient_data.get('middle_name')}"

        birth_date = patient_data.get("birth_date", "")
        phone = patient_data.get("phone") or "не указан"
        email = patient_data.get("email") or "не указан"

        # Форматируем полис ОМС
        polis_s = patient_data.get("polis_s", "")
        polis_n = patient_data.get("polis_n", "")
        polis_text = (
            f"{polis_s} {polis_n}".strip() if (polis_s or polis_n) else "не указан"
        )

        # Формируем текст о проблемных ЛПУ
        failed_lpus_text = ""
        if failed_lpus:
            failed_lpus_details: "list[str]" = []
            for lpu, error_msg in failed_lpus:
                lpu_name = lpu.lpu_full_name or lpu.lpu_short_name
                failed_lpus_details.append(
                    f"🏥 <b>{lpu_name}</b>\n   ❌ {error_msg}",
                )

            failed_lpus_text = (
                "⚠️ <b>В некоторых медицинских учреждениях не "
                "удалось найти вашу карточку:</b>\n\n"
                + "\n\n".join(failed_lpus_details)
                + "\n\n"
                + "─" * 20
                + "\n\n"
            )

        # Форматируем список успешных ЛПУ
        successful_lpus_text = ""
        if successful_lpus:
            successful_lpus_names = [
                lpu.lpu_full_name or lpu.lpu_short_name for lpu in successful_lpus
            ]
            successful_lpus_text = (
                "\n\n🏥 <b>Прикрепленные медицинские учреждения:</b>\n"
                + "\n".join(
                    [f"• {name}" for name in successful_lpus_names],
                )
            )

        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=(
                f"{failed_lpus_text}"
                "✅ <b>Пациент успешно создан!</b>\n\n"
                f"👤 <b>ФИО:</b> {full_name}\n"
                "📅 <b>Дата рождения:</b> "
                f"{datetime.fromisoformat(birth_date).strftime('%d.%m.%Y')}\n"
                f"📱 <b>Телефон:</b> {phone}\n"
                f"📧 <b>Email:</b> {email}\n"
                f"🆔 <b>Полис ОМС:</b> {polis_text}"
                f"{successful_lpus_text}\n\n"
                "📋 Для просмотра записей: /appointments\n"
                "⏰ Для создания расписания на запись: /schedules\n"
                "📋 Для просмотра пациентов: /patients"
            ),
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при создании пациента: {e}")
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=(
                "❌ <b>Ошибка при создании пациента.</b>\n\n"
                "Попробуйте начать заново: /patients"
            ),
        )
        await state.clear()


@router.callback_query(PatientsMenuFactory.filter(F.action == "view"))
async def view_patient_callback(  # noqa: C901
    callback: CallbackQuery,
    callback_data: PatientsMenuFactory,
) -> None:
    """Показывает данные пациента."""
    await callback.answer()

    if (
        not callback.from_user
        or not callback.message
        or isinstance(callback.message, InaccessibleMessage)
    ):
        return

    user_id = callback.from_user.id
    patient_id = callback_data.patient_id

    if patient_id is None:
        if callback.message:
            await callback.message.edit_text(
                "❌ <b>Некорректный ID пациента</b>\n\n"
                "Попробуйте перейти к списку пациентов заново.",
            )
        return

    try:
        async with get_or_create_session() as session:
            patients_service = PatientsService(session)
            patient = await patients_service.get_patient_by_id(patient_id)

            if not patient or patient.user_id != user_id:
                if callback.message:
                    await callback.message.edit_text(
                        "❌ <b>Пациент не найден</b>\n\n"
                        "Возможно, он был удален или у вас нет доступа к нему.",
                    )
                return

            # Форматируем ФИО
            full_name = f"{patient.last_name} {patient.first_name}"
            if patient.middle_name:
                full_name += f" {patient.middle_name}"

            # Форматируем полис ОМС
            polis_text = "Не указан"
            if patient.polis_s or patient.polis_n:
                polis_parts: "list[str]" = []
                if patient.polis_s:
                    polis_parts.append(patient.polis_s)
                if patient.polis_n:
                    polis_parts.append(patient.polis_n)
                polis_text = " ".join(polis_parts)

            patient_text = (
                "👤 <b>Информация о пациенте</b>\n\n"
                f"📝 <b>ФИО:</b> {full_name}\n"
                f"📅 <b>Дата рождения:</b> {patient.birth_date.strftime('%d.%m.%Y')}\n"
                f"📱 <b>Телефон:</b> {patient.phone or 'Не указан'}\n"
                f"📧 <b>Email:</b> {patient.email or 'Не указан'}\n"
                f"🆔 <b>Полис ОМС:</b> {polis_text}\n\n"
                "💡 <i>Используйте кнопки ниже для управления пациентом</i>"
            )

            keyboard = get_patient_view_keyboard(patient.id)

            if callback.message:
                await callback.message.edit_text(
                    patient_text,
                    reply_markup=keyboard,
                )

    except Exception as e:
        logger.error(
            f"Ошибка при просмотре пациента {patient_id}: {e}",
        )
        if callback.message:
            await callback.message.edit_text(
                "❌ <b>Произошла ошибка</b>\n\n"
                "Не удалось загрузить информацию о пациенте. "
                "Попробуйте позже или обратитесь в поддержку.",
            )


@router.callback_query(PatientsMenuFactory.filter(F.action == "delete"))
async def delete_patient_callback(
    callback: CallbackQuery,
    callback_data: PatientsMenuFactory,
) -> None:
    """Показывает подтверждение удаления пациента."""
    await callback.answer()

    if (
        not callback.from_user
        or not callback.message
        or isinstance(callback.message, InaccessibleMessage)
    ):
        return

    user_id = callback.from_user.id
    patient_id = callback_data.patient_id

    if patient_id is None:
        if callback.message:
            await callback.message.edit_text(
                "❌ <b>Некорректный ID пациента</b>\n\n"
                "Попробуйте перейти к списку пациентов заново.",
            )
        return

    try:
        async with get_or_create_session() as session:
            patients_service = PatientsService(session)
            patient = await patients_service.get_patient_by_id(patient_id)

            if not patient or patient.user_id != user_id:
                if callback.message:
                    await callback.message.edit_text(
                        "❌ <b>Пациент не найден</b>\n\n"
                        "Возможно, он был удален или у вас нет доступа к нему.",
                    )
                return

            # Форматируем ФИО
            full_name = f"{patient.last_name} {patient.first_name}"
            if patient.middle_name:
                full_name += f" {patient.middle_name}"

            keyboard = get_patient_delete_keyboard(patient.id)

            if callback.message:
                await callback.message.edit_text(
                    f"⚠️ <b>Подтверждение удаления</b>\n\n"
                    f"Вы уверены, что хотите удалить пациента?\n\n"
                    f"👤 <b>ФИО:</b> {full_name}\n"
                    "📅 <b>Дата рождения:</b> "
                    f"{patient.birth_date.strftime('%d.%m.%Y')}\n\n"
                    f"⚠️ <i>Это действие нельзя будет отменить</i>",
                    reply_markup=keyboard,
                )

    except Exception as e:
        logger.error(
            f"Ошибка при удалении пациента {patient_id}: {e}",
        )
        if callback.message:
            await callback.message.edit_text(
                "❌ <b>Произошла ошибка</b>\n\n"
                "Не удалось подготовить удаление пациента. "
                "Попробуйте позже или обратитесь в поддержку.",
            )


@router.callback_query(PatientsMenuFactory.filter(F.action == "delete_confirm"))
async def delete_patient_confirm_callback(
    callback: CallbackQuery,
    callback_data: PatientsMenuFactory,
) -> None:
    """Подтверждает удаление пациента."""
    await callback.answer()

    if (
        not callback.from_user
        or not callback.message
        or isinstance(callback.message, InaccessibleMessage)
    ):
        return

    user_id = callback.from_user.id
    patient_id = callback_data.patient_id

    if patient_id is None:
        if callback.message:
            await callback.message.edit_text(
                "❌ <b>Некорректный ID пациента</b>\n\n"
                "Попробуйте перейти к списку пациентов заново.",
            )
        return

    try:
        async with get_or_create_session() as session:
            patients_service = PatientsService(session)
            patient = await patients_service.get_patient_by_id(patient_id)

            if not patient or patient.user_id != user_id:
                if callback.message:
                    await callback.message.edit_text(
                        "❌ <b>Пациент не найден</b>\n\n"
                        "Возможно, он уже был удален или у вас нет доступа к нему.",
                    )
                return

            # Сохраняем ФИО для сообщения об успехе
            full_name = f"{patient.last_name} {patient.first_name}"
            if patient.middle_name:
                full_name += f" {patient.middle_name}"

            # Удаляем пациента
            await patients_service.delete_patient(patient_id)

            keyboard = get_patient_deleted_keyboard()

            if callback.message:
                await callback.message.edit_text(
                    f"✅ <b>Пациент успешно удален</b>\n\n"
                    f"👤 <b>ФИО:</b> {full_name}\n\n"
                    f"🗑️ <i>Все данные пациента были удалены из системы</i>",
                    reply_markup=keyboard,
                )

            logger.info(f"Пользователь {user_id} удалил пациента {patient_id}")

    except Exception as e:
        logger.error(
            f"Ошибка при подтверждении удаления пациента {patient_id}: {e}",
        )
        if callback.message:
            await callback.message.edit_text(
                "❌ <b>Ошибка удаления</b>\n\n"
                "Не удалось удалить пациента. "
                "Попробуйте позже или обратитесь в поддержку.",
            )


@router.callback_query(PatientsMenuFactory.filter(F.action == "toggle_same_day"))
async def toggle_same_day_callback(
    callback: CallbackQuery,
) -> None:
    """Switch same day booking setting."""
    await callback.answer()

    if (
        not callback.from_user
        or not callback.message
        or isinstance(callback.message, InaccessibleMessage)
    ):
        return

    user_id = callback.from_user.id

    try:
        async with get_or_create_session() as session:
            users_service = UsersService(session)
            user = await users_service.get_user_by_id(user_id)

            if not user:
                if callback.message:
                    await callback.message.edit_text(
                        "❌ <b>Пользователь не найден</b>\n\n"
                        "Используйте /start для регистрации.",
                    )
                return

            # Переключаем флаг
            new_value = not user.no_same_day_booking
            await users_service.update(user_id, no_same_day_booking=new_value)
            await users_service.save()

            # Обновляем меню пациентов
            await send_patients_menu(user_id, callback.message, edit_message=True)

            action_text = "disabled" if new_value else "enabled"
            logger.info(f"User {user_id} {action_text} same day booking")

    except Exception as e:
        logger.error(
            f"Error changing same day booking setting for user {user_id}: {e}",
        )
        if callback.message:
            await callback.message.edit_text(
                "❌ <b>Ошибка обновления настроек</b>\n\n"
                "Попробуйте позже или обратитесь в поддержку.",
            )
