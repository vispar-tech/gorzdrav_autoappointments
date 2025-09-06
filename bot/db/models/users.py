from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base
from bot.db.types import (
    big_int,
    created_at_an,
    updated_at_an,
)

if TYPE_CHECKING:
    from bot.db.models.patients import Patient
    from bot.db.models.payments import Payment


class User(Base):
    """Telegram user model."""

    __tablename__ = "users"

    id: Mapped[big_int] = mapped_column(primary_key=True)
    username: Mapped[str | None] = mapped_column(String(100))
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))

    is_subscribed: Mapped[bool] = mapped_column(default=False)
    subscription_end: Mapped[datetime | None] = mapped_column(DateTime)
    no_same_day_booking: Mapped[bool] = mapped_column(default=False)
    external_priority: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[created_at_an]
    updated_at: Mapped[updated_at_an]

    # Relationship with patients (one-to-many)
    patients: Mapped[List["Patient"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )

    # Relationship with payments (one-to-many)
    payments: Mapped[List["Payment"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
