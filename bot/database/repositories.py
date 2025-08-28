from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from loguru import logger
from typing import Any, Optional, Sequence

from .models import User, Patient, Schedule
from .database import get_or_create_session
from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository:
    """Репозиторий для работы с пользователями"""

    @staticmethod
    async def create_user(user: User, resession: AsyncSession | None = None) -> User:
        """Создает нового пользователя"""
        async with get_or_create_session(resession) as session:
            try:
                session.add(user)
                await session.flush()
                await session.refresh(user)
                logger.info(f"Создан пользователь: {user.id}")
                return user
            except Exception as e:
                logger.error(f"Ошибка создания пользователя: {e}")
                raise

    @staticmethod
    async def get_user_by_id(
        user_id: int, resession: AsyncSession | None = None
    ) -> Optional[User]:
        """Получает пользователя по ID"""
        async with get_or_create_session(resession) as session:
            try:
                result = await session.execute(select(User).where(User.id == user_id))
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"Ошибка получения пользователя {user_id}: {e}")
                return None

    @staticmethod
    async def update_user(
        user_id: int, resession: AsyncSession | None = None, **kwargs: Any
    ) -> bool:
        """Обновляет пользователя"""
        async with get_or_create_session(resession) as session:
            try:
                result = await session.execute(
                    update(User).where(User.id == user_id).values(**kwargs)
                )
                return result.rowcount > 0
            except Exception as e:
                logger.error(f"Ошибка обновления пользователя {user_id}: {e}")
                return False

    @staticmethod
    async def get_or_create_user(
        user_id: int, resession: AsyncSession | None = None, **kwargs: Any
    ) -> User:
        """Получает пользователя или создает нового"""
        user = await UserRepository.get_user_by_id(user_id, resession)
        if user is None:
            user = User(id=user_id, **kwargs)
            user = await UserRepository.create_user(user, resession)
        return user


class PatientRepository:
    """Репозиторий для работы с пациентами"""

    @staticmethod
    async def create_patient(
        patient: Patient, resession: AsyncSession | None = None
    ) -> Patient:
        """Создает нового пациента"""
        async with get_or_create_session(resession) as session:
            try:
                session.add(patient)
                await session.flush()
                await session.refresh(patient)
                logger.info(f"Создан пациент: {patient.last_name} {patient.first_name}")
                return patient
            except Exception as e:
                logger.error(f"Ошибка создания пациента: {e}")
                raise

    @staticmethod
    async def get_patient_by_id(
        patient_id: int, resession: AsyncSession | None = None
    ) -> Optional[Patient]:
        """Получает пациента по ID"""
        async with get_or_create_session(resession) as session:
            try:
                result = await session.execute(
                    select(Patient)
                    .options(selectinload(Patient.user))
                    .where(Patient.id == patient_id)
                )
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"Ошибка получения пациента {patient_id}: {e}")
                return None

    @staticmethod
    async def get_patient_by_user(
        user_id: int, resession: AsyncSession | None = None
    ) -> Optional[Patient]:
        """Получает пациента пользователя (один-к-одному)"""
        async with get_or_create_session(resession) as session:
            try:
                result = await session.execute(
                    select(Patient)
                    .options(selectinload(Patient.user))
                    .where(Patient.user_id == user_id)
                )
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"Ошибка получения пациента пользователя {user_id}: {e}")
                return None

    @staticmethod
    async def get_patient_by_gorzdrav_id(
        gorzdrav_id: str, resession: AsyncSession | None = None
    ) -> Optional[Patient]:
        """Получает пациента по ID в системе Горздрав"""
        async with get_or_create_session(resession) as session:
            try:
                result = await session.execute(
                    select(Patient).where(Patient.gorzdrav_id == gorzdrav_id)
                )
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(
                    f"Ошибка получения пациента по gorzdrav_id {gorzdrav_id}: {e}"
                )
                return None

    @staticmethod
    async def update_patient(
        patient_id: int, resession: AsyncSession | None = None, **kwargs: Any
    ) -> bool:
        """Обновляет пациента"""
        async with get_or_create_session(resession) as session:
            try:
                result = await session.execute(
                    update(Patient).where(Patient.id == patient_id).values(**kwargs)
                )
                return result.rowcount > 0
            except Exception as e:
                logger.error(f"Ошибка обновления пациента {patient_id}: {e}")
                return False


class ScheduleRepository:
    """Репозиторий для работы с записями на прием"""

    @staticmethod
    async def create_schedule(
        schedule: Schedule, resession: AsyncSession | None = None
    ) -> Schedule:
        """Создает новую запись на прием"""
        async with get_or_create_session(resession) as session:
            try:
                session.add(schedule)
                await session.flush()
                await session.refresh(schedule)
                logger.info(f"Создана запись на прием: {schedule.id}")
                return schedule
            except Exception as e:
                logger.error(f"Ошибка создания записи на прием: {e}")
                raise

    @staticmethod
    async def get_schedule_by_id(
        schedule_id: int, resession: AsyncSession | None = None
    ) -> Optional[Schedule]:
        """Получает запись на прием по ID"""
        async with get_or_create_session(resession) as session:
            try:
                result = await session.execute(
                    select(Schedule)
                    .options(selectinload(Schedule.patient))
                    .where(Schedule.id == schedule_id)
                )
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"Ошибка получения записи на прием {schedule_id}: {e}")
                return None

    @staticmethod
    async def get_patient_schedules(
        patient_id: int, resession: AsyncSession | None = None
    ) -> Sequence[Schedule]:
        """Получает все записи на прием пациента"""
        async with get_or_create_session(resession) as session:
            try:
                result = await session.execute(
                    select(Schedule)
                    .options(selectinload(Schedule.patient))
                    .where(Schedule.patient_id == patient_id)
                    .order_by(Schedule.created_at.desc())
                )
                return result.scalars().all()
            except Exception as e:
                logger.error(f"Ошибка получения записей пациента {patient_id}: {e}")
                return []

    @staticmethod
    async def get_schedules_by_status(
        status: str, resession: AsyncSession | None = None
    ) -> Sequence[Schedule]:
        """Получает записи на прием по статусу"""
        async with get_or_create_session(resession) as session:
            try:
                result = await session.execute(
                    select(Schedule)
                    .options(selectinload(Schedule.patient))
                    .where(Schedule.status == status)
                )
                return result.scalars().all()
            except Exception as e:
                logger.error(f"Ошибка получения записей по статусу {status}: {e}")
                return []

    @staticmethod
    async def get_schedules_by_specialist(
        specialist_id: str, resession: AsyncSession | None = None
    ) -> Sequence[Schedule]:
        """Получает записи на прием по специализации"""
        async with get_or_create_session(resession) as session:
            try:
                result = await session.execute(
                    select(Schedule)
                    .options(selectinload(Schedule.patient))
                    .where(Schedule.specialist_id == specialist_id)
                )
                return result.scalars().all()
            except Exception as e:
                logger.error(
                    f"Ошибка получения записей по специализации {specialist_id}: {e}"
                )
                return []

    @staticmethod
    async def update_schedule(
        schedule_id: int, resession: AsyncSession | None = None, **kwargs: Any
    ) -> bool:
        """Обновляет запись на прием"""
        async with get_or_create_session(resession) as session:
            try:
                result = await session.execute(
                    update(Schedule).where(Schedule.id == schedule_id).values(**kwargs)
                )
                return result.rowcount > 0
            except Exception as e:
                logger.error(f"Ошибка обновления записи на прием {schedule_id}: {e}")
                return False

    @staticmethod
    async def delete_schedule(
        schedule_id: int, resession: AsyncSession | None = None
    ) -> bool:
        """Удаляет запись на прием"""
        async with get_or_create_session(resession) as session:
            try:
                result = await session.execute(
                    delete(Schedule).where(Schedule.id == schedule_id)
                )
                return result.rowcount > 0
            except Exception as e:
                logger.error(f"Ошибка удаления записи на прием {schedule_id}: {e}")
                return False
