from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from bot.db.models.enums import ScheduleStatus
from bot.db.models.patients import Patient
from bot.db.models.schedules import Schedule
from bot.db.services.base import BaseService


class SchedulesService(BaseService[Schedule]):
    """Service for working with schedules."""

    model = Schedule

    async def find_all_by_user_id(self, user_id: int) -> Sequence[Schedule]:
        """
        Retrieve all schedules for a specific user.

        Args:
            user_id: The user ID to filter by.

        Returns:
            A sequence of schedules for the user.
        """
        query = (
            select(Schedule)
            .join(Schedule.patient)
            .where(Schedule.patient.has(user_id=user_id))
            .options(joinedload(Schedule.patient))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def find_all_by_status(self, status: ScheduleStatus) -> Sequence[Schedule]:
        """
        Retrieve all schedules by status.

        Args:
            status: The status to filter by.

        Returns:
            A sequence of schedules by status.
        """
        query = (
            select(Schedule)
            .where(Schedule.status == status)
            .options(joinedload(Schedule.patient).joinedload(Patient.user))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def find_one_with_patient(self, schedule_id: int) -> Schedule | None:
        """
        Retrieve all schedules for a specific patient.

        Args:
            patient_id: The patient ID to filter by.
        """
        query = (
            select(Schedule)
            .where(Schedule.id == schedule_id)
            .options(joinedload(Schedule.patient))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
