from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base
from bot.db.types import (
    big_int,
    created_at_an,
    updated_at_an,
)

if TYPE_CHECKING:
    from bot.db.models.schedules import Schedule
    from bot.db.models.users import User


class Patient(Base):
    """Patient model for storing information in the healthcare system."""

    __tablename__ = "patients"

    # Identifiers
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[big_int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Patient personal data
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    birth_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Health insurance information
    polis_s: Mapped[str | None] = mapped_column(String(20), nullable=True)
    polis_n: Mapped[str] = mapped_column(String(20), nullable=False)

    # Contact information
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False)

    # System timestamps
    created_at: Mapped[created_at_an]
    updated_at: Mapped[updated_at_an]

    # Relationships
    user: Mapped["User"] = relationship(back_populates="patients", lazy="selectin")
    schedules: Mapped[List["Schedule"]] = relationship(back_populates="patient")
