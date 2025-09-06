from datetime import time
from typing import TYPE_CHECKING, List

from sqlalchemy import JSON, Enum, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base
from bot.db.models.enums import ScheduleStatus
from bot.db.types import (
    created_at_an,
    updated_at_an,
)

if TYPE_CHECKING:
    from bot.db.models.patients import Patient


class Schedule(Base):
    """Appointment model."""

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)

    # Gorzdrav API ID
    lpu_id: Mapped[str] = mapped_column(String(50), nullable=False)
    gorzdrav_patient_id: Mapped[str] = mapped_column(String(100), nullable=False)
    gorzdrav_specialist_id: Mapped[str] = mapped_column(String(50), nullable=False)
    preferred_doctors_ids: Mapped[List[str] | None] = mapped_column(JSON, default=list)

    # Preferred appointment time
    preferred_time_start: Mapped[time | None] = mapped_column(Time)  # For example 11:00
    preferred_time_end: Mapped[time | None] = mapped_column(Time)  # For example 18:00

    # Appointment status
    status: Mapped[ScheduleStatus] = mapped_column(
        Enum(ScheduleStatus),
        default=ScheduleStatus.PENDING,
    )

    # Additional information
    reject_reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[created_at_an]
    updated_at: Mapped[updated_at_an]

    # Relations
    patient: Mapped["Patient"] = relationship(back_populates="schedules")
