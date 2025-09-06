from typing import TYPE_CHECKING

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from loguru import logger

from bot.api.client import GorzdravAPIClient
from bot.db.models.enums import ScheduleStatus
from bot.settings.settings import settings
from bot.utils.callbacks import PatientsMenuFactory, SchedulesMenuFactory, StartCallback

if TYPE_CHECKING:
    from bot.api.models import Attachment, Doctor, Specialist
    from bot.db.models.patients import Patient
    from bot.db.models.schedules import Schedule
    from bot.db.models.users import User


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Get the start keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="ℹ️ Помощь",
                    callback_data=StartCallback.START_HELP,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📄 Пользовательское соглашение",
                    callback_data=StartCallback.START_AGREEMENT,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔒 Политика конфиденциальности",
                    callback_data=StartCallback.START_PRIVACY,
                ),
            ],
        ],
    )


def get_commands_reply_keyboard() -> ReplyKeyboardMarkup:
    """Get the reply keyboard with main commands."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👥 Пациенты"),
                KeyboardButton(text="📅 Расписания"),
            ],
            [
                KeyboardButton(text="📋 Записи"),
                KeyboardButton(text="ℹ️ Помощь"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите команду или используйте меню",
    )


def get_add_patient_keyboard() -> InlineKeyboardMarkup:
    """Get an inline keyboard with an add patient button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить пациента",
                    callback_data=PatientsMenuFactory(
                        patient_id=None,
                        action="add",
                    ).pack(),
                ),
            ],
        ],
    )


def get_patients_keyboard(
    patients: list["Patient"],
    user: "User",
) -> InlineKeyboardMarkup:
    """Create an inline keyboard with a list of patients and an add patient button.

    Args:
        patients: List of patient objects to display
        user: User object to check subscription status

    Returns:
        InlineKeyboardMarkup with patient buttons and optional add button
    """
    keyboard: list[list[InlineKeyboardButton]] = []

    # Add patient button (limited by subscription)
    max_patients = (
        settings.MAX_SUBSCRIBED_PATIENTS
        if user.is_subscribed
        else settings.MAX_UNSUBSCRIBED_PATIENTS
    )

    # Create buttons for each patient
    for patient in patients[:max_patients]:
        patient_name = (
            f"{patient.last_name} {patient.first_name} {patient.middle_name}".strip()
        )
        if not patient_name:
            patient_name = f"Пациент #{patient.id}"

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=patient_name,
                    callback_data=PatientsMenuFactory(
                        patient_id=patient.id,
                        action="view",
                    ).pack(),
                ),
            ],
        )

    if len(patients) < max_patients:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="➕ Добавить пациента",
                    callback_data=PatientsMenuFactory(
                        patient_id=None,
                        action="add",
                    ).pack(),
                ),
            ],
        )

    # Add toggle button for same day booking preference
    flag_text = (
        "🚫 Запись в текущий день (вкл?)"
        if user.no_same_day_booking
        else "✅ Запись в текущий день (выкл?)"
    )

    keyboard.append(
        [
            InlineKeyboardButton(
                text=flag_text,
                callback_data=PatientsMenuFactory(
                    patient_id=None,
                    action="toggle_same_day",
                ).pack(),
            ),
        ],
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_patients_cancel_keyboard() -> InlineKeyboardMarkup:
    """Get an inline keyboard with a cancel button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=PatientsMenuFactory(
                        patient_id=None,
                        action="cancel",
                    ).pack(),
                ),
            ],
        ],
    )


def get_patients_cancel_back_keyboard() -> InlineKeyboardMarkup:
    """Get an inline keyboard with a cancel and back buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=PatientsMenuFactory(
                        patient_id=None,
                        action="cancel",
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=PatientsMenuFactory(
                        patient_id=None,
                        action="back",
                    ).pack(),
                ),
            ],
        ],
    )


def get_patients_cancel_back_skip_keyboard() -> InlineKeyboardMarkup:
    """Get an inline keyboard with a cancel, back and skip buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=PatientsMenuFactory(
                        patient_id=None,
                        action="back",
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="⏭️ Пропустить",
                    callback_data=PatientsMenuFactory(
                        patient_id=None,
                        action="skip",
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=PatientsMenuFactory(
                        patient_id=None,
                        action="cancel",
                    ).pack(),
                ),
            ],
        ],
    )


def get_patients_cancel_skip_keyboard() -> InlineKeyboardMarkup:
    """Get an inline keyboard with a cancel and skip buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=PatientsMenuFactory(
                        patient_id=None,
                        action="cancel",
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="⏭️ Пропустить",
                    callback_data=PatientsMenuFactory(
                        patient_id=None,
                        action="skip",
                    ).pack(),
                ),
            ],
        ],
    )


def get_patient_view_keyboard(patient_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для просмотра пациента."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить",
                    callback_data=PatientsMenuFactory(
                        action="delete",
                        patient_id=patient_id,
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад к списку",
                    callback_data=PatientsMenuFactory(
                        action="list",
                        patient_id=None,
                    ).pack(),
                ),
            ],
        ],
    )


def get_patient_delete_keyboard(patient_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для подтверждения удаления пациента."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить удаление",
                    callback_data=PatientsMenuFactory(
                        action="delete_confirm",
                        patient_id=patient_id,
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=PatientsMenuFactory(
                        action="view",
                        patient_id=patient_id,
                    ).pack(),
                ),
            ],
        ],
    )


def get_patient_deleted_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру после успешного удаления пациента."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 К списку пациентов",
                    callback_data=PatientsMenuFactory(
                        action="list",
                        patient_id=None,
                    ).pack(),
                ),
            ],
        ],
    )


async def get_schedules_keyboard(  # noqa: C901, PLR0912
    schedules: list["Schedule"],
    user: "User",
) -> InlineKeyboardMarkup:
    """Create a keyboard with a list of schedules."""
    keyboard: list[list[InlineKeyboardButton]] = []

    # Add patient button (limited by subscription)
    max_schedules = (
        settings.MAX_SUBSCRIBED_SCHEDULES
        if user.is_subscribed
        else settings.MAX_UNSUBSCRIBED_SCHEDULES
    )

    # Предварительно загружаем все специализации для уникальных ЛПУ
    specializations_cache: dict[str, dict[str, str | None]] = {}
    unique_lpu_ids = list({schedule.lpu_id for schedule in schedules})

    if unique_lpu_ids:
        try:
            async with GorzdravAPIClient() as client:
                for lpu_id in unique_lpu_ids:
                    try:
                        specialists_response = await client.get_specialists(int(lpu_id))
                        if specialists_response.success and specialists_response.result:
                            specializations_cache[lpu_id] = {
                                specialist.id: specialist.name
                                for specialist in specialists_response.result
                            }
                    except Exception:
                        specializations_cache[lpu_id] = {}
        except Exception:
            logger.error("Error loading specializations for schedules")

    # Кнопки для каждого расписания
    for schedule in schedules[:max_schedules]:
        if schedule.status != ScheduleStatus.PENDING:
            continue
        # Форматируем имя пациента
        patient_name = f"{schedule.patient.last_name} {schedule.patient.first_name}"
        if schedule.patient.middle_name:
            patient_name += f" {schedule.patient.middle_name}"

        # Определяем эмодзи статуса
        status_emoji = {
            ScheduleStatus.PENDING: "⏳",
            ScheduleStatus.FOUND: "✅",
            ScheduleStatus.CANCELLED: "❌",
        }.get(schedule.status, "❓")

        # Получаем название специализации из кэша
        specialization_name = "Не указана"
        if (
            schedule.lpu_id in specializations_cache
            and schedule.gorzdrav_specialist_id
            in specializations_cache[schedule.lpu_id]
        ):
            try:
                specialization_name = (
                    specializations_cache[schedule.lpu_id][
                        schedule.gorzdrav_specialist_id
                    ]
                    or "Не указана"
                )
            except KeyError:
                specialization_name = "Не указана"

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{status_emoji} {schedule.patient.first_name} "
                        f"({specialization_name})"
                    ),
                    callback_data=SchedulesMenuFactory(
                        schedule_id=schedule.id,
                        action="view",
                    ).pack(),
                ),
            ],
        )

    # Кнопка добавления расписания (ограничена подпиской)
    can_create = False
    if user.is_subscribed:
        pending_schedules = [s for s in schedules if s.status == ScheduleStatus.PENDING]
        can_create = len(pending_schedules) < max_schedules
    else:
        total_schedules = len(schedules)
        can_create = total_schedules < max_schedules

    if can_create:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="➕ Создать расписание",
                    callback_data=SchedulesMenuFactory(
                        action="create",
                    ).pack(),
                ),
            ],
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_schedules_empty_keyboard(user: "User") -> InlineKeyboardMarkup:
    """Create a keyboard for an empty list of schedules."""
    keyboard: list[list[InlineKeyboardButton]] = []

    # Кнопка добавления расписания (ограничена подпиской)
    if user.is_subscribed:
        # Платные: максимум 10 активных расписаний
        max_schedules = settings.MAX_SUBSCRIBED_SCHEDULES
    else:
        # Бесплатные: максимум 2 найденные записи
        max_schedules = settings.MAX_UNSUBSCRIBED_SCHEDULES

    if max_schedules > 0:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="➕ Создать расписание",
                    callback_data=SchedulesMenuFactory(
                        action="create",
                    ).pack(),
                ),
            ],
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_schedule_view_keyboard(schedule_id: int) -> InlineKeyboardMarkup:
    """Create a keyboard for viewing a schedule."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить",
                    callback_data=SchedulesMenuFactory(
                        schedule_id=schedule_id,
                        action="delete",
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 К списку расписаний",
                    callback_data=SchedulesMenuFactory(
                        action="list",
                    ).pack(),
                ),
            ],
        ],
    )


def get_schedule_delete_keyboard(schedule_id: int) -> InlineKeyboardMarkup:
    """Create a keyboard for confirming the deletion of a schedule."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить удаление",
                    callback_data=SchedulesMenuFactory(
                        schedule_id=schedule_id,
                        action="delete_confirm",
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=SchedulesMenuFactory(
                        schedule_id=schedule_id,
                        action="view",
                    ).pack(),
                ),
            ],
        ],
    )


def get_schedule_deleted_keyboard() -> InlineKeyboardMarkup:
    """Create a keyboard after successfully deleting a schedule."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 К списку расписаний",
                    callback_data=SchedulesMenuFactory(
                        action="list",
                    ).pack(),
                ),
            ],
        ],
    )


def get_patient_select_keyboard(patients: list["Patient"]) -> InlineKeyboardMarkup:
    """Create a keyboard for selecting a patient."""
    keyboard: list[list[InlineKeyboardButton]] = []

    for patient in patients:
        patient_name = f"{patient.last_name} {patient.first_name}"
        if patient.middle_name:
            patient_name += f" {patient.middle_name}"

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=patient_name,
                    callback_data=SchedulesMenuFactory(
                        patient_id=patient.id,
                        action="select_patient",
                    ).pack(),
                ),
            ],
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=SchedulesMenuFactory(
                    action="list",
                ).pack(),
            ),
        ],
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_lpu_select_keyboard(attachments: list["Attachment"]) -> InlineKeyboardMarkup:
    """Create a keyboard for selecting an LPU."""
    keyboard: list[list[InlineKeyboardButton]] = []

    for attachment in attachments:
        lpu_name = attachment.lpu_full_name or attachment.lpu_short_name or "-"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=lpu_name,
                    callback_data=SchedulesMenuFactory(
                        lpu_id=attachment.id,
                        action="select_lpu",
                    ).pack(),
                ),
            ],
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=SchedulesMenuFactory(
                    action="create",
                ).pack(),
            ),
        ],
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_specialist_select_keyboard(
    specialists: list["Specialist"],
    patient_id: int,
) -> InlineKeyboardMarkup:
    """Create a keyboard for selecting a specialization."""
    keyboard: list[list[InlineKeyboardButton]] = []

    for specialist in specialists:
        specialist_name = specialist.name or f"Специалист #{specialist.id}"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=specialist_name,
                    callback_data=SchedulesMenuFactory(
                        specialist_id=specialist.id,
                        action="select_specialist",
                    ).pack(),
                ),
            ],
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=SchedulesMenuFactory(
                    patient_id=patient_id,
                    action="select_patient",
                ).pack(),
            ),
        ],
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_doctors_select_keyboard(
    doctors: list["Doctor"],
    lpu_id: int,
    selected_doctors: list[str],
) -> InlineKeyboardMarkup:
    """Create a keyboard for selecting doctors."""
    keyboard: list[list[InlineKeyboardButton]] = []

    for doctor in doctors:
        doctor_name = doctor.name or f"Врач #{doctor.id}"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{'✅' if doctor.id in selected_doctors else '☑️'} "
                        f"{doctor_name}"
                    ),
                    callback_data=SchedulesMenuFactory(
                        doctor_id=doctor.id,
                        action="toggle_doctor",
                    ).pack(),
                ),
            ],
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="✅ Продолжить",
                callback_data=SchedulesMenuFactory(
                    action="confirm_doctors",
                ).pack(),
            ),
        ],
    )
    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=SchedulesMenuFactory(
                    lpu_id=lpu_id,
                    action="select_lpu",
                ).pack(),
            ),
        ],
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_schedule_cancel_keyboard() -> InlineKeyboardMarkup:
    """Create a keyboard with a cancel button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=SchedulesMenuFactory(
                        action="list",
                    ).pack(),
                ),
            ],
        ],
    )


def get_schedule_create_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Create a keyboard for confirming the creation of a schedule."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Создать",
                    callback_data=SchedulesMenuFactory(
                        action="create_confirm",
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=SchedulesMenuFactory(
                        action="list",
                    ).pack(),
                ),
            ],
        ],
    )
