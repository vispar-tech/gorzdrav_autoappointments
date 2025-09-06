"""Модель для хранения платежей пользователей."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base
from bot.db.types import big_int, created_at_an, updated_at_an

if TYPE_CHECKING:
    from bot.db.models.users import User


class Payment(Base):
    """Модель платежа пользователя."""

    __tablename__ = "payments"

    id: Mapped[big_int] = mapped_column(primary_key=True)
    user_id: Mapped[big_int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    yookassa_payment_id: Mapped[str] = mapped_column(String(100), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    status: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(500))
    payment_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
    )  # JSON строка

    # Временные метки
    created_at: Mapped[created_at_an]
    updated_at: Mapped[updated_at_an]
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Связь с пользователем
    user: Mapped["User"] = relationship(
        back_populates="payments",
        lazy="selectin",
    )
