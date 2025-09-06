from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import TYPE_CHECKING, Optional, Sequence

from loguru import logger

from bot.api.client import GorzdravAPIClient, GorzdravAPIError
from bot.api.models import Appointment, AppointmentCreateRequest
from bot.db.context import get_or_create_session
from bot.db.models.enums import ScheduleStatus
from bot.db.services import SchedulesService
from bot.loader import bot

if TYPE_CHECKING:
    from bot.db.models.patients import Patient
    from bot.db.models.schedules import Schedule


@dataclass
class SchedulerConfig:
    """Config for the appointment scheduler."""

    interval_seconds: int = 10


class AppointmentScheduler:
    """Appointment scheduler."""

    def __init__(self, config: SchedulerConfig | None = None) -> None:
        self._config = config or SchedulerConfig()
        self._task: Optional[asyncio.Task[None]] = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        """Start the appointment scheduler."""
        if self._task and not self._task.done():
            return
        self._stopped.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("AppointmentScheduler started")

    async def stop(self) -> None:
        """Stop the appointment scheduler."""
        self._stopped.set()
        if self._task:
            await self._task
        logger.info("AppointmentScheduler stopped")

    async def _run_loop(self) -> None:
        try:
            while not self._stopped.is_set():
                await self._tick()
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(
                        self._stopped.wait(),
                        timeout=self._config.interval_seconds,
                    )
        except Exception as e:
            logger.exception(f"Scheduler crashed: {e}")

    async def sort_by_priority(self, schedules: Sequence[Schedule]) -> list[Schedule]:
        """Sort schedules by priority.

        Priority order:
        1. Users with external_priority
        2. Users with subscription (sorted by created_at)
        3. Other users (sorted by created_at)
        """

        def get_priority_key(schedule: Schedule) -> tuple[int, datetime]:
            user = schedule.patient.user

            # 1. external_priority - высший приоритет (0)
            if user.external_priority:
                return (0, user.created_at)

            # 2. Подписка - средний приоритет (1)
            if user.is_subscribed:
                return (1, user.created_at)

            # 3. Обычные пользователи - низший приоритет (2)
            return (2, user.created_at)

        return sorted(schedules, key=get_priority_key)

    async def _tick(self) -> None:
        # Iterates over patients with schedules and finds slots
        async with get_or_create_session() as session:
            schedules = await SchedulesService(session).find_all_by_status(
                ScheduleStatus.PENDING,
            )

        if not schedules:
            return

        schedules = await self.sort_by_priority(schedules)

        async with GorzdravAPIClient() as client:
            for schedule in schedules:
                try:
                    await self._process_schedule(schedule, client)
                except Exception as e:
                    logger.error(f"Error processing schedule {schedule.id}: {e}")

    async def _process_schedule(
        self,
        schedule: Schedule,
        client: GorzdravAPIClient,
    ) -> None:
        """Processes one schedule.

        Args:
            schedule: Schedule to process
            client: GorzdravAPIClient instance
        """

        # Gets slots by selected doctors
        doctors = await client.get_doctors(
            int(schedule.lpu_id),
            schedule.gorzdrav_specialist_id,
        )
        doctor_ids = (
            schedule.preferred_doctors_ids
            if schedule.preferred_doctors_ids
            else [d.id for d in doctors.result]
        )

        # Creates a dictionary for quick search of doctor names
        doctor_names = {d.id: d.name for d in doctors.result}

        # Searches for suitable appointments for each doctor
        start_t = schedule.preferred_time_start or time(0, 0)
        end_t = schedule.preferred_time_end or time(23, 59)

        for doctor_id in doctor_ids:
            doctor_name = doctor_names.get(doctor_id, f"ID:{doctor_id}")

            try:
                appointments = await client.get_appointments(
                    int(schedule.lpu_id),
                    doctor_id,
                )
            except GorzdravAPIError as e:
                if e.error_code == 39:
                    logger.info(
                        f"No appointments for doctor {doctor_name}: {e.error_code}",
                    )
                else:
                    logger.warning(
                        f"Cannot get appointments for doctor "
                        f"{doctor_name}: {e.error_code}",
                    )
                continue
            except Exception as e:
                logger.exception(
                    f"Cannot get appointments for doctor {doctor_name}: {e}",
                )
                continue

            # Checks suitable slots
            for appointment in appointments.result:
                appointment_time = appointment.visit_start.time()
                appointment_date = appointment.visit_start.date()

                # Проверяем временной диапазон
                if not (start_t <= appointment_time <= end_t):
                    logger.info(
                        f"Skip appointment out of time range - "
                        f"patient: {schedule.patient.id}, doctor: {doctor_name}, "
                        f"date: {appointment_date}, time: {appointment_time}",
                    )
                    continue

                # Проверяем флаг запрета записи на сегодня
                user = schedule.patient.user
                if user.no_same_day_booking and appointment_date == date.today():
                    logger.info(
                        f"Skip same day booking for appointment - "
                        f"patient: {schedule.patient.id}, doctor: {doctor_name}, "
                        f"date: {appointment_date}, time: {appointment_time}",
                    )
                    continue

                # Found a suitable slot - creates an appointment
                try:
                    await self._create_appointment_and_notify(
                        client,
                        schedule,
                        schedule.patient,
                        appointment,
                        doctor_name,
                    )
                    return  # Exits after successful appointment
                except Exception as e:
                    logger.exception(
                        f"Error creating appointment for schedule {schedule.id}: {e}",
                    )
                    continue

    async def _create_appointment_and_notify(
        self,
        client: GorzdravAPIClient,
        schedule: Schedule,
        patient: Patient,
        appointment: Appointment,
        doctor_name: str,
    ) -> None:
        """Creates an appointment, sends a notification and update the schedule."""
        try:
            # Creates an appointment
            create_request = AppointmentCreateRequest(
                lpu_id=int(schedule.lpu_id),
                patient_id=schedule.gorzdrav_patient_id,
                appointment_id=appointment.id,
                patient_last_name=patient.last_name,
                patient_first_name=patient.first_name,
                patient_middle_name=patient.middle_name,
                patient_birthdate=patient.birth_date.isoformat(),
                visit_date=appointment.visit_start.isoformat(),
                room=appointment.room,
                address=appointment.address,
                referral_id=None,
                ipmpi_card_id=None,
                recipient_email=patient.email,
            )

            create_response = await client.create_appointment(create_request)
            logger.info(
                f"Appointment created for patient {patient.id}: {create_response}",
            )

            # Deletes the schedule
            async with get_or_create_session() as session:
                await SchedulesService(session).update(
                    schedule.id,
                    status=ScheduleStatus.FOUND,
                )
            logger.info(f"Schedule {schedule.id} updated after successful appointment")

            # Sends a notification to the user
            await self._send_notification(patient, appointment, doctor_name)

        except Exception as e:
            logger.exception(f"Error creating appointment: {e}")
            raise

    async def _send_notification(
        self,
        patient: Patient,
        appointment: Appointment,
        doctor_name: str,
    ) -> None:
        """Sends a notification to the user about the created appointment."""
        try:
            user_id = patient.user_id
            appointment_date = appointment.visit_start.strftime("%d.%m.%Y %H:%M")
            appointment_end = appointment.visit_end.strftime("%H:%M")

            message = (
                f"🎉 <b>Запись на приём успешно создана!</b>\n\n"
                f"👤 <b>Информация о пациенте:</b>\n"
                f"   📝 ФИО: {patient.last_name} "
                f"{patient.first_name} {patient.middle_name}\n\n"
                f"👨‍⚕️ <b>Лечащий врач:</b>\n"
                f"   🩺 {doctor_name}\n\n"
                f"📅 <b>Детали приёма:</b>\n"
                f"   🕐 Дата: {appointment_date}\n"
                f"   ⏰ Окончание: {appointment_end}\n"
                f"   🏥 Кабинет: {appointment.room or 'Не указан'}\n"
                f"   📍 Адрес: {appointment.address or 'Не указан'}\n\n"
                f"✅ <b>Статус расписания обновлён</b>\n"
                f"   Ваше расписание автоматически переведено в статус "
                f"<b>«Завершено»</b>\n\n"
                f"💡 <i>Рекомендуем прибыть за 15 минут до назначенного времени</i>\n"
            )

            await bot.send_message(user_id, message)
            logger.info(f"Notification sent to user {user_id}")

        except Exception as e:
            logger.error(
                f"Error sending notification to user {patient.user_id}: {e}",
            )
