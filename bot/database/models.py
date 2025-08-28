from datetime import datetime, time
from typing import List

from sqlalchemy import DateTime, ForeignKey, String, Time, JSON
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .database import (
    big_int,
    content_an,
    created_at_an,
    updated_at_an,
)


class User(Base):
    """Модель пользователя Telegram"""

    __tablename__ = "users"

    id: Mapped[big_int] = mapped_column(primary_key=True)  # Telegram ID
    username: Mapped[str | None] = mapped_column(String(100))
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[created_at_an]
    updated_at: Mapped[updated_at_an]

    # Связь с пациентом (один-к-одному)
    patient: Mapped["Patient | None"] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )

    @hybrid_property
    def is_registered(self) -> bool:
        return self.patient is not None

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', is_registered={self.is_registered})>"


class Patient(Base):
    """Модель пациента"""

    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[big_int] = mapped_column(
        ForeignKey("users.id"), nullable=False, unique=True
    )

    # Данные пациента
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # ID в системе Горздрав
    gorzdrav_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    # Предпочитаемая поликлиника (ID из API ГЗ)
    prefer_lpu_id: Mapped[str] = mapped_column(String(50), nullable=False)

    created_at: Mapped[created_at_an]
    updated_at: Mapped[updated_at_an]

    # Связи
    user: Mapped["User"] = relationship(back_populates="patient", lazy="selectin")
    schedules: Mapped[List["Schedule"]] = relationship(back_populates="patient")

    def __repr__(self):
        return f"<Patient(id={self.id}, name='{self.last_name} {self.first_name}')>"


class Schedule(Base):
    """Модель записи на прием"""

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)

    # Желаемое время записи
    preferred_time_start: Mapped[time | None] = mapped_column(Time)  # Например 11:00
    preferred_time_end: Mapped[time | None] = mapped_column(Time)  # Например 18:00

    # Направление (specialist_id из API ГЗ)
    specialist_id: Mapped[str] = mapped_column(String(50), nullable=False)

    # Предпочитаемые доктора (массив ID из API ГЗ)
    preferred_doctors: Mapped[List[str] | None] = mapped_column(JSON, default=list)

    # Статус записи
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, searching, found, confirmed, cancelled

    # Дополнительная информация
    notes: Mapped[content_an]
    created_at: Mapped[created_at_an]
    updated_at: Mapped[updated_at_an]

    # Связи
    patient: Mapped["Patient"] = relationship(back_populates="schedules")

    def __repr__(self):
        return f"<Schedule(id={self.id}, patient_id={self.patient_id}, specialist_id='{self.specialist_id}', status='{self.status}')>"
