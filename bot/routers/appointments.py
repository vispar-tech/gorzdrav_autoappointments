"""Router for handling appointments."""

import time
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from bot.api.client import GorzdravAPIClient, GorzdravAPIError
from bot.db.context import get_or_create_session
from bot.db.models.patients import Patient
from bot.db.services import PatientsService
from bot.utils.texts import get_appointments_text

if TYPE_CHECKING:
    from bot.api.models import Attachment, PatientAppointmentItem

router = Router(name="appointments")

RATE_LIMIT_SECONDS = 10


async def check_rate_limit(state: FSMContext) -> tuple[bool, int]:
    """
    Проверяет rate limit для пользователя используя FSMContext.

    Returns:
        tuple[bool, int]: (можно_выполнить, оставшееся_время_в_секундах)
    """
    current_time = time.time()
    data = await state.get_data()
    last_call_time = data.get("last_appointments_call", 0)

    if current_time - last_call_time >= RATE_LIMIT_SECONDS:
        await state.update_data(last_appointments_call=current_time)
        return True, 0

    remaining_time = RATE_LIMIT_SECONDS - int(current_time - last_call_time)
    return False, remaining_time


async def get_patient_appointments_from_attachment(
    api_client: GorzdravAPIClient,
    patient: "Patient",
    attachment: "Attachment",
) -> "list[tuple[Patient, Attachment, PatientAppointmentItem]]":
    """Get appointments for a patient from a specific attachment."""
    appointments: "list[tuple[Patient, Attachment, PatientAppointmentItem]]" = []

    try:
        # Ищем пациента в системе ГорЗдрав
        search_response = await api_client.search_patient(
            lpu_id=attachment.id,
            last_name=patient.last_name,
            first_name=patient.first_name,
            middle_name=patient.middle_name or "",
            birthdate_iso=patient.birth_date.isoformat(),
        )

        # Если пациент найден, получаем его записи
        if search_response.result:
            patient_id = search_response.result
            appointments_response = await api_client.get_patient_appointments(
                lpu_id=attachment.id,
                patient_id=patient_id,
            )

            for appointment in appointments_response.result:
                appointments.append(
                    (
                        patient,
                        attachment,
                        appointment,
                    ),
                )
        else:
            logger.info(
                f"Patient {patient.id} not found in LPU {attachment.id} system",
            )

    except GorzdravAPIError as e:
        logger.warning(
            f"Failed to get appointments for patient {patient.id} "
            f"at LPU {attachment.id}: {e.message}",
        )

    return appointments


async def get_all_patient_appointments(
    api_client: GorzdravAPIClient,
    patients: list[Patient],
) -> "list[tuple[Patient, Attachment, PatientAppointmentItem]]":
    """Get all appointments for all patients."""
    all_appointments: "list[tuple[Patient, Attachment, PatientAppointmentItem]]" = []

    for patient in patients:
        try:
            # Получаем прикрепления для пациента
            attachments_response = await api_client.get_attachments(
                polis_s=patient.polis_s,
                polis_n=patient.polis_n,
            )

            # Для каждого прикрепления получаем записи
            for attachment in attachments_response.result:
                appointments = await get_patient_appointments_from_attachment(
                    api_client,
                    patient,
                    attachment,
                )
                all_appointments.extend(appointments)

        except GorzdravAPIError as e:
            logger.warning(
                f"Failed to get attachments for patient {patient.id}: {e.message}",
            )
            continue

    return all_appointments


@router.message(Command("appointments"))
@router.message(F.text == "📋 Записи")
async def appointments_handler(message: Message, state: FSMContext) -> None:
    """Show all appointments for all patients of the user."""
    if not message.from_user:
        await message.answer(
            "<b>❌ Техническая ошибка: отсутствует пользователь сообщения</b>",
        )
        return

    user_id = message.from_user.id

    # Проверяем rate limit
    can_execute, remaining_time = await check_rate_limit(state)
    if not can_execute:
        await message.answer(
            f"⏳ <b>Слишком частые запросы</b>\n\n"
            f"Пожалуйста, подождите {remaining_time} секунд "
            f"перед следующим запросом записей.",
        )
        return

    # Отправляем сообщение о загрузке
    loading_message = await message.answer(
        "🔄 <b>Загружаем ваши записи...</b>\n⏳ Это может занять несколько секунд",
    )

    try:
        async with get_or_create_session() as session:
            patients_service = PatientsService(session)
            patients = await patients_service.get_patients_by_user_id(user_id)

            if not patients:
                await loading_message.edit_text(
                    "<b>📋 Записи</b>\n\n"
                    "❌ У вас нет добавленных пациентов.\n"
                    "Используйте команду /patients для добавления пациентов.",
                )
                return

            # Получаем записи для всех пациентов
            async with GorzdravAPIClient() as api_client:
                all_appointments = await get_all_patient_appointments(
                    api_client,
                    patients,
                )

            if not all_appointments:
                await loading_message.edit_text(
                    "<b>📋 Записи</b>\n\n"
                    "❌ У вас нет активных записей к врачам.\n"
                    "Используйте команду /schedules для настройки автопоиска записей.",
                )
                return

            # Форматируем и отправляем список записей
            appointments_text = get_appointments_text(all_appointments)
            await loading_message.edit_text(appointments_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in appointments handler: {e}")
        await loading_message.edit_text(
            "<b>❌ Произошла ошибка при получении записей</b>\n"
            "Попробуйте позже или обратитесь в поддержку.",
        )
