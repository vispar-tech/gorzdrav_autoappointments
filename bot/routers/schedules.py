"""Router for handling schedules."""

import contextlib
import time
from datetime import time as dt_time
from typing import TYPE_CHECKING

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage, Message
from loguru import logger

from bot.api.client import GorzdravAPIClient, GorzdravAPIError
from bot.db.context import get_or_create_session
from bot.db.models.enums import ScheduleStatus
from bot.db.models.schedules import Schedule
from bot.db.services import PatientsService, SchedulesService, UsersService
from bot.settings.settings import settings
from bot.utils.callbacks import SchedulesMenuFactory
from bot.utils.keyboards import (
    get_doctors_select_keyboard,
    get_lpu_select_keyboard,
    get_patient_select_keyboard,
    get_schedule_cancel_keyboard,
    get_schedule_create_confirmation_keyboard,
    get_schedule_delete_keyboard,
    get_schedule_deleted_keyboard,
    get_schedule_view_keyboard,
    get_schedules_empty_keyboard,
    get_schedules_keyboard,
    get_specialist_select_keyboard,
)
from bot.utils.states import ScheduleFormStates

if TYPE_CHECKING:
    from bot.api.models import Attachment
    from bot.db.models.users import User

router = Router(name="schedules")

RATE_LIMIT_SECONDS = 5


async def check_rate_limit(state: FSMContext) -> tuple[bool, int]:
    """
    Проверяет rate limit для пользователя используя FSMContext.

    Returns:
        tuple[bool, int]: (можно_выполнить, оставшееся_время_в_секундах)
    """
    current_time = time.time()
    data = await state.get_data()
    last_call_time = data.get("last_schedules_call", 0)

    if current_time - last_call_time >= RATE_LIMIT_SECONDS:
        await state.update_data(last_schedules_call=current_time)
        return True, 0

    remaining_time = RATE_LIMIT_SECONDS - int(current_time - last_call_time)
    return False, remaining_time


def get_tariff_info(user: "User") -> str:
    """Return information about the user's tariff."""
    if user.is_subscribed:
        count = settings.MAX_SUBSCRIBED_SCHEDULES
        if count % 10 == 1 and count % 100 != 11:
            word = "расписание"
        elif count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
            word = "расписания"
        else:
            word = "расписаний"
        return f"💎 <b>Платный тариф:</b> до {count} {word} (активных)"

    count = settings.MAX_UNSUBSCRIBED_SCHEDULES
    if count % 10 == 1 and count % 100 != 11:
        word = "расписание"
    elif count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
        word = "расписания"
    else:
        word = "расписаний"
    return f"🆓 <b>Бесплатный тариф:</b> {count} {word}"


async def send_schedules_menu(
    user_id: int,
    message: Message,
    *,
    edit_message: bool = False,
) -> Message:
    """Set the schedules menu."""
    async with get_or_create_session() as session:
        users_service = UsersService(session)
        schedules_service = SchedulesService(session)

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

        schedules = list(await schedules_service.find_all_by_user_id(user_id))

        pending_schedules = [s for s in schedules if s.status == ScheduleStatus.PENDING]
        [s for s in schedules if s.status == ScheduleStatus.FOUND]

        if not schedules:
            text = (
                f"📅 <b>Ваши расписания</b>\n\n"
                f"{get_tariff_info(user)}\n\n"
                'У вас нет созданных расписаний. Нажмите "Создать расписание".'
            )
            keyboard = get_schedules_empty_keyboard(user)
        else:
            # Подсчитываем статистику
            found_schedules = [s for s in schedules if s.status == ScheduleStatus.FOUND]
            found_count = len(found_schedules)

            # Подсчитываем статистику в зависимости от тарифа
            if user.is_subscribed:
                active_count = len(pending_schedules)
                max_schedules = settings.MAX_SUBSCRIBED_SCHEDULES

                # Определяем текст для лимита
                bottom_text = ""
                if active_count >= max_schedules:
                    bottom_text = (
                        "❌ Лимит активных расписаний достигнут, он освободится, "
                        "когда выполнится хотя бы одно из них."
                    )

                text = (
                    f"📅 <b>Ваши расписания</b>\n\n"
                    f"{get_tariff_info(user)}\n"
                    f"✅ Выполнено расписаний: {found_count}\n\n"
                    f"{bottom_text}"
                )
            else:
                total_schedules = len(schedules)
                max_schedules = settings.MAX_UNSUBSCRIBED_SCHEDULES

                # Проверяем ограничения для бесплатных пользователей:
                # а) не больше 2 активных расписаний
                # б) создание доступно только если нет двух выполненных

                if total_schedules >= max_schedules:
                    # Достигнут лимит найденных записей
                    text = (
                        f"📅 <b>Ваши расписания</b>\n\n"
                        f"{get_tariff_info(user)}\n"
                        f"✅ Выполнено расписаний: {found_count}\n\n"
                        f"❌ У вас закончились бесплатные расписания.\n"
                        f"💎 Используйте /subscribe для получения премиум доступа."
                    )
                else:
                    # Можно создавать новые расписания
                    text = (
                        f"📅 <b>Ваши расписания</b>\n\n"
                        f"{get_tariff_info(user)}\n"
                        f"✅ Выполнено расписаний: {found_count}\n"
                    )
            keyboard = await get_schedules_keyboard(schedules, user)

        if edit_message:
            await message.edit_text(text, reply_markup=keyboard)
            return message
        return await message.answer(text, reply_markup=keyboard)


@router.message(Command("schedules"))
@router.message(F.text == "📅 Расписания")
async def schedules_handler(message: Message, state: FSMContext) -> None:
    """Показывает меню расписаний."""
    if not message.from_user:
        await message.answer(
            "❌ Техническая ошибка: отсутствует пользователь сообщения",
        )
        return

    user_id = message.from_user.id

    # Проверяем rate limit
    can_execute, remaining_time = await check_rate_limit(state)
    if not can_execute:
        await message.answer(
            f"⏳ <b>Слишком частые запросы</b>\n\n"
            f"Пожалуйста, подождите {remaining_time} секунд "
            f"перед следующим запросом расписаний.",
        )
        return

    try:
        await send_schedules_menu(user_id, message)
    except Exception as e:
        logger.error(
            f"Ошибка при получении списка расписаний для пользователя {user_id}: {e}",
        )
        await message.answer(
            "❌ Произошла ошибка при получении списка расписаний. Попробуйте позже.",
        )


@router.callback_query(SchedulesMenuFactory.filter(F.action == "list"))
async def list_schedules_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает меню расписаний."""
    await callback.answer()
    if not callback.message or isinstance(callback.message, InaccessibleMessage):
        return
    await send_schedules_menu(
        callback.from_user.id,
        callback.message,
        edit_message=True,
    )


@router.callback_query(SchedulesMenuFactory.filter(F.action == "create"))
async def create_schedule_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начинает процесс создания расписания."""
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
            schedules_service = SchedulesService(session)

            # Получаем пользователя
            user = await users_service.get_user_by_id(user_id)
            if not user:
                if callback.message:
                    await callback.message.edit_text(
                        "❌ Пользователь не найден. "
                        "Используйте /start для регистрации.",
                    )
                return

            # Проверяем лимит расписаний в зависимости от тарифа
            schedules = list(await schedules_service.find_all_by_user_id(user_id))

            if user.is_subscribed:
                # Платные: максимум 10 активных расписаний (не отмененных)
                active_schedules = [
                    s for s in schedules if s.status != ScheduleStatus.PENDING
                ]
                max_schedules = settings.MAX_SUBSCRIBED_SCHEDULES
                current_count = len(active_schedules)

                if current_count >= max_schedules:
                    await callback.message.edit_text(
                        f"❌ <b>Лимит активных расписаний достигнут</b>\n\n"
                        f"📊 Активных расписаний: {current_count}/{max_schedules}\n"
                        f"💡 <i>Удалите одно из существующих расписаний или "
                        f"дождитесь исполнения записи</i>",
                    )
                    return
            else:
                # Бесплатные: максимум 2 найденные записи (единоразово)
                found_schedules = [
                    s for s in schedules if s.status == ScheduleStatus.FOUND
                ]
                max_found = 2
                found_count = len(found_schedules)

                if found_count >= max_found:
                    await callback.message.edit_text(
                        f"❌ <b>Лимит найденных записей достигнут</b>\n\n"
                        f"✅ Найдено записей: {found_count}/{max_found}\n"
                        f"💎 <i>Для увеличения лимита оформите подписку: "
                        "/subscribe</i>\n\n"
                        f"ℹ️ <i>Бесплатный тариф позволяет найти только 2 записи "
                        f"за все время использования</i>",
                    )
                    return

            # Получаем пациентов пользователя
            patients = await patients_service.get_patients_by_user_id(user_id)
            if not patients:
                await callback.message.edit_text(
                    "❌ <b>Нет пациентов для создания расписания</b>\n\n"
                    "Сначала добавьте пациента в разделе /patients",
                )
                return

            # Начинаем создание расписания
            await state.set_state(ScheduleFormStates.waiting_for_patient)
            await state.update_data(message_id=callback.message.message_id)
            await callback.message.edit_text(
                "👤 <b>Выберите пациента для создания расписания:</b>",
                reply_markup=get_patient_select_keyboard(patients),
            )

    except Exception as e:
        logger.error(
            f"Ошибка при начале создания расписания для пользователя {user_id}: {e}",
        )
        if callback.message:
            await callback.message.edit_text(
                "❌ Произошла ошибка при создании расписания. Попробуйте позже.",
            )


@router.callback_query(SchedulesMenuFactory.filter(F.action == "select_patient"))
async def select_patient_callback(
    callback: CallbackQuery,
    callback_data: SchedulesMenuFactory,
    state: FSMContext,
) -> None:
    """Обрабатывает выбор пациента."""
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
        await callback.message.edit_text(
            "❌ <b>Некорректный ID пациента</b>\n\n"
            "Попробуйте перейти к созданию расписания заново.",
        )
        return

    # Показываем сообщение загрузки
    await callback.message.edit_text(
        "⏳ <b>Загрузка...</b>\n\nПолучаем данные о прикреплениях пациента...",
    )

    try:
        async with get_or_create_session() as session:
            patients_service = PatientsService(session)
            patient = await patients_service.get_patient_by_id(patient_id)

            if not patient or patient.user_id != user_id:
                await callback.message.edit_text(
                    "❌ <b>Пациент не найден</b>\n\n"
                    "Возможно, он был удален или у вас нет доступа к нему.",
                )
                return

            # Сохраняем выбранного пациента
            await state.update_data(selected_patient_id=patient_id)

            # Получаем прикрепления для пациента
            async with GorzdravAPIClient() as api_client:
                attachments_response = await api_client.get_attachments(
                    polis_s=patient.polis_s,
                    polis_n=patient.polis_n,
                )

                if not attachments_response.success or not attachments_response.result:
                    await callback.message.edit_text(
                        "❌ <b>Не удалось получить прикрепления</b>\n\n"
                        "Проверьте данные полиса ОМС пациента.",
                    )
                    await state.clear()
                    return

                # Проверяем, в каких ЛПУ найден пациент
                available_attachments: "list[Attachment]" = []
                for attachment in attachments_response.result:
                    try:
                        search_response = await api_client.search_patient(
                            lpu_id=attachment.id,
                            last_name=patient.last_name,
                            first_name=patient.first_name,
                            middle_name=patient.middle_name or "",
                            birthdate_iso=patient.birth_date.isoformat(),
                        )

                        if search_response.success and search_response.result:
                            available_attachments.append(attachment)
                    except GorzdravAPIError:
                        continue

                if not available_attachments:
                    await callback.message.edit_text(
                        "❌ <b>Пациент не найден в системе ГорЗдрав</b>\n\n"
                        "Проверьте данные пациента или попробуйте позже.",
                    )
                    await state.clear()
                    return

                # Переходим к выбору ЛПУ
                await state.set_state(ScheduleFormStates.waiting_for_lpu)
                await callback.message.edit_text(
                    "🏥 <b>Выберите медицинское учреждение:</b>",
                    reply_markup=get_lpu_select_keyboard(available_attachments),
                )

    except Exception as e:
        logger.error(
            f"Ошибка при выборе пациента {patient_id}: {e}",
        )
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Не удалось обработать выбор пациента. "
            "Попробуйте позже или обратитесь в поддержку.",
        )


@router.callback_query(SchedulesMenuFactory.filter(F.action == "select_lpu"))
async def select_lpu_callback(
    callback: CallbackQuery,
    callback_data: SchedulesMenuFactory,
    state: FSMContext,
) -> None:
    """Обрабатывает выбор ЛПУ."""
    await callback.answer()

    if (
        not callback.from_user
        or not callback.message
        or isinstance(callback.message, InaccessibleMessage)
    ):
        return

    lpu_id = callback_data.lpu_id

    if lpu_id is None:
        await callback.message.edit_text(
            "❌ <b>Некорректный ID ЛПУ</b>\n\n"
            "Попробуйте перейти к созданию расписания заново.",
        )
        return

    try:
        # Сохраняем выбранное ЛПУ
        selected_patient_id = (await state.get_data()).get("selected_patient_id")
        await state.update_data(selected_lpu_id=lpu_id)

        # Получаем специализации для выбранного ЛПУ
        async with GorzdravAPIClient() as api_client:
            specialists_response = await api_client.get_specialists(int(lpu_id or 0))
            lpu_response = await api_client.get_lpu_by_id(int(lpu_id or 0))

        if (
            not specialists_response.success
            or not specialists_response.result
            or not lpu_response
        ):
            await callback.message.edit_text(
                "❌ <b>Не удалось получить специализации</b>\n\n"
                "Попробуйте выбрать другое медицинское учреждение.",
            )
            return

        # Переходим к выбору специализации
        await state.set_state(ScheduleFormStates.waiting_for_specialist)
        if not selected_patient_id:
            await callback.message.edit_text(
                "❌ <b>Некорректный ID пациента</b>\n\n"
                "Попробуйте перейти к созданию расписания заново.",
            )
            return
        await callback.message.edit_text(
            (
                f"🩺 <b>Выберите специализацию в "
                f"{lpu_response.lpu_full_name or lpu_response.lpu_short_name or 'ЛПУ'}"
                f":</b>"
            ),
            reply_markup=get_specialist_select_keyboard(
                specialists_response.result,
                selected_patient_id,
            ),
        )

    except Exception as e:
        logger.error(
            f"Ошибка при выборе ЛПУ {lpu_id}: {e}",
        )
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Не удалось обработать выбор ЛПУ. "
            "Попробуйте позже или обратитесь в поддержку.",
        )


@router.callback_query(SchedulesMenuFactory.filter(F.action == "select_specialist"))
async def select_specialist_callback(
    callback: CallbackQuery,
    callback_data: SchedulesMenuFactory,
    state: FSMContext,
) -> None:
    """Обрабатывает выбор специализации."""
    await callback.answer()

    if (
        not callback.from_user
        or not callback.message
        or isinstance(callback.message, InaccessibleMessage)
    ):
        return

    specialist_id = callback_data.specialist_id

    if specialist_id is None:
        await callback.message.edit_text(
            "❌ <b>Некорректный ID специализации</b>\n\n"
            "Попробуйте перейти к созданию расписания заново.",
        )
        return

    try:
        # Сохраняем выбранную специализацию
        await state.update_data(selected_specialist_id=specialist_id)

        data = await state.get_data()
        lpu_id = data.get("selected_lpu_id")

        if not lpu_id:
            await callback.message.edit_text(
                "❌ <b>Ошибка: не выбрано ЛПУ</b>\n\n"
                "Попробуйте создать расписание заново.",
            )
            await state.clear()
            return

        # Получаем врачей для выбранной специализации
        async with GorzdravAPIClient() as api_client:
            doctors_response = await api_client.get_doctors(
                int(lpu_id or 0),
                str(specialist_id or ""),
            )

        if not doctors_response.success or not doctors_response.result:
            await callback.message.edit_text(
                "❌ <b>Не удалось получить врачей</b>\n\n"
                "Попробуйте выбрать другую специализацию.",
            )
            return

        # Переходим к выбору врачей
        await state.set_state(ScheduleFormStates.waiting_for_doctors)
        await state.update_data(selected_doctors=[])
        await callback.message.edit_text(
            "👨‍⚕️ <b>Выберите врачей (можно несколько):</b>\n\n"
            "✅ - выбран\n☑️ - не выбран",
            reply_markup=get_doctors_select_keyboard(
                doctors_response.result,
                lpu_id,
                [],
            ),
        )

    except Exception as e:
        logger.error(
            f"Ошибка при выборе специализации {specialist_id}: {e}",
        )
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Не удалось обработать выбор специализации. "
            "Попробуйте позже или обратитесь в поддержку.",
        )


@router.callback_query(SchedulesMenuFactory.filter(F.action == "toggle_doctor"))
async def toggle_doctor_callback(
    callback: CallbackQuery,
    callback_data: SchedulesMenuFactory,
    state: FSMContext,
) -> None:
    """Обрабатывает переключение выбора врача."""
    await callback.answer()

    if (
        not callback.from_user
        or not callback.message
        or isinstance(callback.message, InaccessibleMessage)
    ):
        return

    doctor_id = callback_data.doctor_id

    if doctor_id is None:
        return

    try:
        data = await state.get_data()
        selected_doctors = data.get("selected_doctors", [])

        if doctor_id in selected_doctors:
            selected_doctors.remove(doctor_id)
        else:
            selected_doctors.append(doctor_id)

        await state.update_data(selected_doctors=selected_doctors)

        # Обновляем клавиатуру
        data = await state.get_data()
        lpu_id = data.get("selected_lpu_id")
        specialist_id = data.get("selected_specialist_id")

        if not lpu_id or not specialist_id:
            await callback.message.edit_text(
                "❌ <b>Ошибка: потеряны данные</b>\n\n"
                "Попробуйте создать расписание заново.",
            )
            await state.clear()
            return

        async with GorzdravAPIClient() as api_client:
            doctors_response = await api_client.get_doctors(lpu_id, specialist_id)

            if not doctors_response.success or not doctors_response.result:
                await callback.message.edit_text(
                    "❌ <b>Не удалось получить врачей</b>\n\n"
                    "Попробуйте выбрать другую специализацию.",
                )
                return

            # Обновляем клавиатуру с учетом выбранных врачей
            keyboard = get_doctors_select_keyboard(
                doctors_response.result,
                lpu_id,
                selected_doctors,
            )

            await callback.message.edit_text(
                "👨‍⚕️ <b>Выберите врачей (можно несколько):</b>\n\n"
                "✅ - выбран\n☑️ - не выбран",
                reply_markup=keyboard,
            )

    except Exception as e:
        logger.error(
            f"Ошибка при переключении врача {doctor_id}: {e}",
        )
        await callback.answer("❌ Ошибка при выборе врача", show_alert=True)


@router.callback_query(SchedulesMenuFactory.filter(F.action == "confirm_doctors"))
async def confirm_doctors_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Обрабатывает подтверждение выбора врачей."""

    if (
        not callback.from_user
        or not callback.message
        or isinstance(callback.message, InaccessibleMessage)
    ):
        return

    try:
        data = await state.get_data()
        selected_doctors = data.get("selected_doctors", [])

        if not selected_doctors:
            await callback.answer(
                text="❌ Выберите хотя бы одного врача",
                show_alert=True,
            )
            return

        await callback.answer()

        # Проверяем подписку для ввода времени
        user_id = callback.from_user.id
        async with get_or_create_session() as session:
            users_service = UsersService(session)
            user = await users_service.get_user_by_id(user_id)

            if not user:
                await callback.message.edit_text(
                    "❌ <b>Пользователь не найден</b>\n\n"
                    "Используйте /start для регистрации.",
                )
                await state.clear()
                return

            if user.is_subscribed:
                # Платные пользователи могут выбрать время
                await state.set_state(ScheduleFormStates.waiting_for_time)
                await callback.message.edit_text(
                    "⏰ <b>Введите предпочтительное время приема:</b>\n\n"
                    "📝 <b>Формат:</b> ЧЧ:ММ-ЧЧ:ММ (например, 09:00-18:00)\n"
                    "💡 <i>Отправьте 'весь день' для поиска в любое время</i>",
                    reply_markup=get_schedule_cancel_keyboard(),
                )
            else:
                # Бесплатные пользователи не могут выбрать время
                await state.update_data(
                    preferred_time_start=None,
                    preferred_time_end=None,
                )
                await state.set_state(ScheduleFormStates.waiting_for_confirmation)

                if callback.message.bot is None:
                    raise ValueError("Bot is None")
                # Показываем подтверждение создания
                await show_schedule_confirmation(
                    callback.message.bot,
                    callback.message.chat.id,
                    callback.message.message_id,
                    state,
                )

    except Exception as e:
        logger.error(
            f"Ошибка при подтверждении врачей: {e}",
        )
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Не удалось обработать выбор врачей. "
            "Попробуйте позже или обратитесь в поддержку.",
        )


async def show_schedule_confirmation(  # noqa: C901, PLR0912, PLR0915
    bot: "Bot",
    chat_id: int,
    message_id: int,
    state: FSMContext,
) -> None:
    """Показывает подтверждение создания расписания."""
    data = await state.get_data()

    # Получаем данные для отображения
    patient_id = data.get("selected_patient_id")
    lpu_id = data.get("selected_lpu_id")
    specialist_id = data.get("selected_specialist_id")
    selected_doctors = data.get("selected_doctors", [])
    time_start = data.get("preferred_time_start")
    time_end = data.get("preferred_time_end")

    if not all([patient_id, lpu_id, specialist_id, selected_doctors]):
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                "❌ <b>Ошибка: неполные данные</b>\n\n"
                "Попробуйте создать расписание заново."
            ),
        )
        await state.clear()
        return

    try:
        # Получаем информацию о пациенте и пользователе
        async with get_or_create_session() as session:
            patients_service = PatientsService(session)
            users_service = UsersService(session)
            schedules_service = SchedulesService(session)

            patient = await patients_service.get_patient_by_id(int(patient_id or 0))

            if not patient:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=(
                        "❌ <b>Пациент не найден</b>\n\n"
                        "Попробуйте создать расписание заново."
                    ),
                )
                await state.clear()
                return

            # Получаем информацию о пользователе для проверки подписки и лимитов
            user = await users_service.get_user_by_id(patient.user_id)
            if not user:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=(
                        "❌ <b>Пользователь не найден</b>\n\n"
                        "Используйте /start для регистрации."
                    ),
                )
                await state.clear()
                return

            # Подсчитываем количество существующих расписаний в зависимости от тарифа
            existing_schedules = list(
                await schedules_service.find_all_by_user_id(patient.user_id),
            )

            if user.is_subscribed:
                # Платные: считаем активные расписания (не отмененные)
                active_schedules = [
                    s for s in existing_schedules if s.status == ScheduleStatus.PENDING
                ]
                current_count = len(active_schedules)
                max_schedules = settings.MAX_SUBSCRIBED_SCHEDULES
            else:
                # Бесплатные: считаем только найденные записи (единоразово)
                found_schedules = [
                    s for s in existing_schedules if s.status == ScheduleStatus.FOUND
                ]
                current_count = len(found_schedules)
                max_schedules = settings.MAX_UNSUBSCRIBED_SCHEDULES

            patient_name = f"{patient.last_name} {patient.first_name}"
            if patient.middle_name:
                patient_name += f" {patient.middle_name}"

        # Получаем информацию о ЛПУ и специализации
        async with GorzdravAPIClient() as api_client:
            # Получаем информацию о ЛПУ
            attachments_response = await api_client.get_attachments(
                polis_s=patient.polis_s,
                polis_n=patient.polis_n,
            )

            lpu_name = "Неизвестно"
            for attachment in attachments_response.result:
                if attachment.id == lpu_id:
                    lpu_name = (
                        attachment.lpu_full_name
                        or attachment.lpu_short_name
                        or "Неизвестно"
                    )
                    break

            # Получаем информацию о специализации
            specialists_response = await api_client.get_specialists(int(lpu_id or 0))
            specialist_name = "Неизвестно"
            for specialist in specialists_response.result:
                if specialist.id == specialist_id:
                    specialist_name = specialist.name or "Неизвестно"
                    break

            # Получаем информацию о врачах
            doctors_response = await api_client.get_doctors(
                int(lpu_id or 0),
                str(specialist_id or ""),
            )
            doctors_names: "list[str]" = []
            for doctor in doctors_response.result:
                if doctor.id in selected_doctors:
                    doctors_names.append(doctor.name or f"Врач #{doctor.id}")

        # Формируем текст подтверждения
        text = "📅 <b>Подтверждение создания расписания</b>\n\n"
        text += f"👤 <b>Пациент:</b> {patient_name}\n"
        text += f"🏥 <b>ЛПУ:</b> {lpu_name}\n"
        text += f"🩺 <b>Специализация:</b> {specialist_name}\n"
        text += (
            f"👨‍⚕️ <b>Врачи:</b> "
            f"{', '.join(doctors_names) if doctors_names else 'Не выбраны'}\n"
        )

        if time_start and time_end:
            text += (
                f"⏰ <b>Время:</b> "
                f"{dt_time.fromisoformat(time_start).strftime('%H:%M')}-{dt_time.fromisoformat(time_end).strftime('%H:%M')}\n"
            )
        else:
            text += "⏰ <b>Время:</b> Любое доступное"
            if not user.is_subscribed:
                text += " (выбор времени недоступен без подписки)\n"
            else:
                text += "\n"

        # Добавляем информацию о лимитах
        if user.is_subscribed:
            # Платные пользователи: показываем информацию об активных расписаниях
            remaining_schedules = (
                max_schedules - current_count - 1
            )  # -1 за текущее создаваемое расписание
            text += (
                f"\n📊 <b>Активных расписаний:</b> "
                f"{current_count + 1}/{max_schedules} "
                f"(осталось: {remaining_schedules})\n"
            )
        else:
            # Бесплатные пользователи: показываем информацию о найденных записях
            remaining_found = (
                max_schedules - current_count - 1
            )  # -1 за текущее создаваемое расписание
            text += (
                f"\n📊 <b>Найдено записей:</b> "
                f"{current_count + 1}/{max_schedules} "
                f"(осталось: {remaining_found})\n"
            )
            text += (
                "💎 <i>Для выбора удобного времени и "
                "увеличения лимита: /subscribe</i>\n"
            )

        text += "\n✅ <b>Создать расписание?</b>"

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=get_schedule_create_confirmation_keyboard(),
        )

    except Exception as e:
        logger.error(f"Ошибка при показе подтверждения: {e}")
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                "❌ <b>Произошла ошибка</b>\n\n"
                "Не удалось подготовить подтверждение. "
                "Попробуйте позже или обратитесь в поддержку."
            ),
        )


@router.message(ScheduleFormStates.waiting_for_time)
async def time_input_handler(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод времени."""
    text = (message.text or "").strip()
    data = await state.get_data()
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

    if text.lower() == "весь день":
        # Если время не указано, используем любое доступное
        await state.update_data(preferred_time_start=None, preferred_time_end=None)
        await state.set_state(ScheduleFormStates.waiting_for_confirmation)
        await show_schedule_confirmation(
            message.bot,
            message.chat.id,
            message_id,
            state,
        )
        return

    # Парсим время в формате ЧЧ:ММ-ЧЧ:ММ
    try:
        if "-" not in text:
            raise ValueError("Неверный формат времени")

        time_parts = text.split("-")
        if len(time_parts) != 2:
            raise ValueError("Неверный формат времени")

        start_time_str, end_time_str = time_parts
        start_time = dt_time.fromisoformat(start_time_str.strip())
        end_time = dt_time.fromisoformat(end_time_str.strip())

        if start_time >= end_time:
            raise ValueError("Время начала должно быть раньше времени окончания")

        await state.update_data(
            preferred_time_start=start_time.isoformat(),
            preferred_time_end=end_time.isoformat(),
        )
        await state.set_state(ScheduleFormStates.waiting_for_confirmation)
        await show_schedule_confirmation(
            message.bot,
            message.chat.id,
            message_id,
            state,
        )

    except ValueError as e:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=(
                f"❌ <b>Неверный формат времени!</b>\n\n"
                f"📝 <b>Введите предпочтительное время приема:</b>\n\n"
                f"💡 <i>Формат: ЧЧ:ММ-ЧЧ:ММ (например, 09:00-18:00)</i>\n"
                f"💡 <i>Отправьте 'весь день' для поиска в любое время</i>\n\n"
                f"❌ <b>Ошибка:</b> {e!s}"
            ),
            reply_markup=get_schedule_cancel_keyboard(),
        )


@router.callback_query(SchedulesMenuFactory.filter(F.action == "create_confirm"))
async def create_confirm_callback(  # noqa: C901
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Подтверждает создание расписания."""
    await callback.answer()

    if (
        not callback.from_user
        or not callback.message
        or isinstance(callback.message, InaccessibleMessage)
    ):
        return

    try:
        data = await state.get_data()
        patient_id = data.get("selected_patient_id")
        lpu_id = data.get("selected_lpu_id")
        specialist_id = data.get("selected_specialist_id")
        selected_doctors = data.get("selected_doctors", [])
        time_start = data.get("preferred_time_start")
        time_end = data.get("preferred_time_end")

        if not all([patient_id, lpu_id, specialist_id, selected_doctors]):
            await callback.message.edit_text(
                "❌ <b>Ошибка: неполные данные</b>\n\n"
                "Попробуйте создать расписание заново.",
            )
            await state.clear()
            return

        # Получаем ID пациента в системе ГорЗдрав
        async with get_or_create_session() as session:
            patients_service = PatientsService(session)
            patient = await patients_service.get_patient_by_id(int(patient_id or 0))

            if not patient:
                await callback.message.edit_text(
                    "❌ <b>Пациент не найден</b>\n\n"
                    "Попробуйте создать расписание заново.",
                )
                await state.clear()
                return

        async with GorzdravAPIClient() as api_client:
            # Ищем пациента в системе ГорЗдрав
            search_response = await api_client.search_patient(
                lpu_id=int(lpu_id or 0),
                last_name=patient.last_name,
                first_name=patient.first_name,
                middle_name=patient.middle_name or "",
                birthdate_iso=patient.birth_date.isoformat(),
            )

            if not search_response.success or not search_response.result:
                await callback.message.edit_text(
                    "❌ <b>Пациент не найден в системе ГорЗдрав</b>\n\n"
                    "Проверьте данные пациента или попробуйте позже.",
                )
                await state.clear()
                return

            gorzdrav_patient_id = search_response.result

            # Получаем информацию об ЛПУ
            lpu = await api_client.get_lpu_by_id(int(lpu_id or 0))
            lpu_name = (
                lpu.lpu_short_name or lpu.lpu_full_name or f"ЛПУ #{lpu_id}"
                if lpu
                else f"ЛПУ #{lpu_id}"
            )

            # Получаем информацию о специализации
            specialists_response = await api_client.get_specialists(int(lpu_id or 0))
            specialist_name = f"Специализация #{specialist_id}"
            if specialists_response.success and specialists_response.result:
                for spec in specialists_response.result:
                    if spec.id == specialist_id:
                        specialist_name = spec.name or specialist_name
                        break

        # Создаем расписание
        async with get_or_create_session() as session:
            schedules_service = SchedulesService(session)

            schedule_data = {
                "patient_id": int(patient_id or 0),
                "lpu_id": str(lpu_id or ""),
                "gorzdrav_patient_id": gorzdrav_patient_id,
                "gorzdrav_specialist_id": str(specialist_id or ""),
                "preferred_doctors_ids": selected_doctors,
                "status": ScheduleStatus.PENDING,
            }

            if time_start and time_end:
                schedule_data["preferred_time_start"] = dt_time.fromisoformat(
                    time_start,
                )
                schedule_data["preferred_time_end"] = dt_time.fromisoformat(time_end)

            await schedules_service.add_model(Schedule(**schedule_data))

        # Показываем успешное создание
        patient_name = f"{patient.last_name} {patient.first_name}"
        if patient.middle_name:
            patient_name += f" {patient.middle_name}"

        await callback.message.edit_text(
            f"✅ <b>Расписание успешно создано!</b>\n\n"
            f"👤 <b>Пациент:</b> {patient_name}\n"
            f"🏥 <b>ЛПУ:</b> {lpu_name}\n"
            f"🩺 <b>Специализация:</b> {specialist_name}\n"
            f"👨‍⚕️ <b>Врачи:</b> {len(selected_doctors)} выбрано\n\n"
            f"⏳ <b>Статус:</b> Ожидание талона для записи\n\n"
            f"📋 Для просмотра всех расписаний: /schedules",
            reply_markup=get_schedule_deleted_keyboard(),
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при создании расписания: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка при создании расписания</b>\n\n"
            "Попробуйте позже или обратитесь в поддержку.",
        )
        await state.clear()


@router.callback_query(SchedulesMenuFactory.filter(F.action == "view"))
async def view_schedule_callback(  # noqa: C901, PLR0912, PLR0915
    callback: CallbackQuery,
    callback_data: SchedulesMenuFactory,
) -> None:
    """Показывает данные расписания."""
    await callback.answer()

    if (
        not callback.from_user
        or not callback.message
        or isinstance(callback.message, InaccessibleMessage)
    ):
        return

    user_id = callback.from_user.id
    schedule_id = callback_data.schedule_id

    if schedule_id is None:
        await callback.message.edit_text(
            "❌ <b>Некорректный ID расписания</b>\n\n"
            "Попробуйте перейти к списку расписаний заново.",
        )
        return

    try:
        async with get_or_create_session() as session:
            schedules_service = SchedulesService(session)
            schedule = await schedules_service.find_one_with_patient(schedule_id)

            if not schedule or schedule.patient.user_id != user_id:
                await callback.message.edit_text(
                    "❌ <b>Расписание не найдено</b>\n\n"
                    "Возможно, оно было удалено или у вас нет доступа к нему.",
                )
                return

            # Форматируем информацию о расписании
            patient_name = f"{schedule.patient.last_name} {schedule.patient.first_name}"
            if schedule.patient.middle_name:
                patient_name += f" {schedule.patient.middle_name}"

            status_text = {
                ScheduleStatus.PENDING.value: "⏳ Ожидание талона",
                ScheduleStatus.FOUND.value: "✅ Запись найдена",
                ScheduleStatus.CANCELLED.value: "❌ Отменено",
            }.get(schedule.status.value, "❓ Неизвестно")

            time_text = "Любое доступное"
            if schedule.preferred_time_start and schedule.preferred_time_end:
                time_text = (
                    f"{schedule.preferred_time_start.strftime('%H:%M')}"
                    f"-{schedule.preferred_time_end.strftime('%H:%M')}"
                )

            async with GorzdravAPIClient() as api_client:
                # Получаем информацию об ЛПУ
                lpu_name = f"ЛПУ #{schedule.lpu_id}"
                try:
                    lpu = await api_client.get_lpu_by_id(int(schedule.lpu_id))
                    if lpu:
                        lpu_name = lpu.lpu_full_name or lpu.lpu_short_name or lpu_name
                except Exception as e:
                    logger.warning(
                        f"Error getting LPU info for {schedule.lpu_id}: {e}",
                    )

                # Получаем информацию о специализации
                specialist_name = f"Специализация #{schedule.gorzdrav_specialist_id}"
                try:
                    specialists_response = await api_client.get_specialists(
                        int(schedule.lpu_id),
                    )
                    if specialists_response.success and specialists_response.result:
                        for spec in specialists_response.result:
                            if spec.id == schedule.gorzdrav_specialist_id:
                                specialist_name = spec.name or specialist_name
                                break
                except Exception as e:
                    logger.warning(
                        f"Error getting specialist info for "
                        f"{schedule.gorzdrav_specialist_id}: {e}",
                    )

                # Получаем имена врачей
                doctors_names: list[str] = []
                if schedule.preferred_doctors_ids:
                    try:
                        doctors_response = await api_client.get_doctors(
                            int(schedule.lpu_id),
                            schedule.gorzdrav_specialist_id,
                        )
                        if doctors_response.success and doctors_response.result:
                            for doctor_id in schedule.preferred_doctors_ids:
                                for doctor in doctors_response.result:
                                    if str(doctor.id) == doctor_id:
                                        doctors_names.append(doctor.name)
                                        break
                                else:
                                    doctors_names.append(f"Врач #{doctor_id}")
                    except Exception as e:
                        logger.warning(f"Не удалось получить информацию о врачах: {e}")
                        doctors_names = [
                            f"Врач #{doctor_id}"
                            for doctor_id in schedule.preferred_doctors_ids
                        ]

            doctors_text = ", ".join(doctors_names) if doctors_names else "Не выбраны"

            schedule_text = (
                "📅 <b>Информация о расписании</b>\n\n"
                f"👤 <b>Пациент:</b> {patient_name}\n"
                f"🏥 <b>ЛПУ:</b> {lpu_name}\n"
                f"🩺 <b>Специализация:</b> {specialist_name}\n"
                f"👨‍⚕️ <b>Врачи:</b> {doctors_text}\n"
                f"⏰ <b>Время:</b> {time_text}\n"
                f"📊 <b>Статус:</b> {status_text}\n"
                f"📅 <b>Создано:</b> "
                f"{schedule.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                "💡 <i>Используйте кнопки ниже для управления расписанием</i>"
            )

            keyboard = get_schedule_view_keyboard(schedule.id)

            await callback.message.edit_text(
                schedule_text,
                reply_markup=keyboard,
            )

    except Exception as e:
        logger.error(
            f"Ошибка при просмотре расписания {schedule_id}: {e}",
        )
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Не удалось загрузить информацию о расписании. "
            "Попробуйте позже или обратитесь в поддержку.",
        )


@router.callback_query(SchedulesMenuFactory.filter(F.action == "delete"))
async def delete_schedule_callback(
    callback: CallbackQuery,
    callback_data: SchedulesMenuFactory,
) -> None:
    """Показывает подтверждение удаления расписания."""
    await callback.answer()

    if (
        not callback.from_user
        or not callback.message
        or isinstance(callback.message, InaccessibleMessage)
    ):
        return

    user_id = callback.from_user.id
    schedule_id = callback_data.schedule_id

    if schedule_id is None:
        await callback.message.edit_text(
            "❌ <b>Некорректный ID расписания</b>\n\n"
            "Попробуйте перейти к списку расписаний заново.",
        )
        return

    try:
        async with get_or_create_session() as session:
            schedules_service = SchedulesService(session)
            schedule = await schedules_service.find_one_with_patient(schedule_id)

            if not schedule or schedule.patient.user_id != user_id:
                await callback.message.edit_text(
                    "❌ <b>Расписание не найдено</b>\n\n"
                    "Возможно, оно было удалено или у вас нет доступа к нему.",
                )
                return

            keyboard = get_schedule_delete_keyboard(schedule.id)

            await callback.message.edit_text(
                "⚠️ <b>Подтверждение удаления</b>\n\n"
                "Вы уверены, что хотите удалить расписание?\n\n"
                "⚠️ <i>Это действие нельзя будет отменить</i>",
                reply_markup=keyboard,
            )

    except Exception as e:
        logger.error(
            f"Ошибка при удалении расписания {schedule_id}: {e}",
        )
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Не удалось подготовить удаление расписания. "
            "Попробуйте позже или обратитесь в поддержку.",
        )


@router.callback_query(SchedulesMenuFactory.filter(F.action == "delete_confirm"))
async def delete_schedule_confirm_callback(
    callback: CallbackQuery,
    callback_data: SchedulesMenuFactory,
) -> None:
    """Подтверждает удаление расписания."""
    await callback.answer()

    if (
        not callback.from_user
        or not callback.message
        or isinstance(callback.message, InaccessibleMessage)
    ):
        return

    user_id = callback.from_user.id
    schedule_id = callback_data.schedule_id

    if schedule_id is None:
        await callback.message.edit_text(
            "❌ <b>Некорректный ID расписания</b>\n\n"
            "Попробуйте перейти к списку расписаний заново.",
        )
        return

    try:
        async with get_or_create_session() as session:
            schedules_service = SchedulesService(session)
            schedule = await schedules_service.find_one_with_patient(schedule_id)

            if not schedule or schedule.patient.user_id != user_id:
                await callback.message.edit_text(
                    "❌ <b>Расписание не найдено</b>\n\n"
                    "Возможно, оно уже было удалено или у вас нет доступа к нему.",
                )
                return

            # Сохраняем ФИО для сообщения об успехе
            patient_name = f"{schedule.patient.last_name} {schedule.patient.first_name}"
            if schedule.patient.middle_name:
                patient_name += f" {schedule.patient.middle_name}"

            # Удаляем расписание
            await schedules_service.delete(schedule_id)

            keyboard = get_schedule_deleted_keyboard()

            await callback.message.edit_text(
                f"✅ <b>Расписание успешно удалено</b>\n\n"
                f"👤 <b>Пациент:</b> {patient_name}\n\n"
                f"🗑️ <i>Все данные расписания были удалены из системы</i>",
                reply_markup=keyboard,
            )

            logger.info(f"Пользователь {user_id} удалил расписание {schedule_id}")

    except Exception as e:
        logger.error(
            f"Ошибка при подтверждении удаления расписания {schedule_id}: {e}",
        )
        await callback.message.edit_text(
            "❌ <b>Ошибка удаления</b>\n\n"
            "Не удалось удалить расписание. "
            "Попробуйте позже или обратитесь в поддержку.",
        )
