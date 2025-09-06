from __future__ import annotations

from enum import StrEnum, auto

from aiogram.filters.callback_data import CallbackData


class StartCallback(StrEnum):
    """Callbacks for the start router."""

    START_HELP = auto()
    START_AGREEMENT = auto()
    START_PRIVACY = auto()


class PatientsMenuFactory(CallbackData, prefix="patients-menu"):
    """Factory for patients menu callbacks."""

    patient_id: int | None = None
    action: str
    district_id: int | None = None
    lpu_id: int | None = None


class SchedulesMenuFactory(CallbackData, prefix="schedules-menu"):
    """Factory for schedules menu callbacks."""

    schedule_id: int | None = None
    patient_id: int | None = None
    lpu_id: int | None = None
    specialist_id: str | None = None
    doctor_id: str | None = None
    action: str
