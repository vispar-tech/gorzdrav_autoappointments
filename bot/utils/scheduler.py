from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Optional
from datetime import time
from loguru import logger

from bot.api.client import GorzdravAPIClient, GorzdravAPIException
from bot.api.models import AppointmentCreateRequest, Appointment
from bot.database.repositories import PatientRepository
from bot.database.repositories import ScheduleRepository
from bot.database.models import Schedule, Patient
from bot.loader import bot


@dataclass
class SchedulerConfig:
    interval_seconds: int = 10


class AppointmentScheduler:
    def __init__(self, config: SchedulerConfig | None = None):
        self._config = config or SchedulerConfig()
        self._task: Optional[asyncio.Task[None]] = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stopped.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("AppointmentScheduler started")

    async def stop(self) -> None:
        self._stopped.set()
        if self._task:
            await self._task
        logger.info("AppointmentScheduler stopped")

    async def _run_loop(self) -> None:
        try:
            while not self._stopped.is_set():
                await self._tick()
                try:
                    await asyncio.wait_for(
                        self._stopped.wait(), timeout=self._config.interval_seconds
                    )
                except asyncio.TimeoutError:
                    pass
        except Exception as e:
            logger.exception(f"Scheduler crashed: {e}")

    async def _tick(self) -> None:
        # Проходим по пациентам с расписаниями и ищем слоты
        schedules = await ScheduleRepository().get_schedules_by_status("pending")
        if not schedules:
            return

        async with GorzdravAPIClient() as client:
            for schedule in schedules:
                try:
                    await self._process_schedule(schedule, client)
                except Exception as e:
                    logger.error(f"Ошибка обработки расписания {schedule.id}: {e}")

    async def _process_schedule(
        self, schedule: Schedule, client: GorzdravAPIClient
    ) -> None:
        """Обрабатывает одно расписание: ищет слоты, создает запись, уведомляет, удаляет"""
        patient = await PatientRepository().get_patient_by_id(schedule.patient_id)
        if not patient or not patient.prefer_lpu_id:
            logger.warning(
                f"Пациент {schedule.patient_id} не найден или нет prefer_lpu_id"
            )
            return

        # Проверяем наличие gorzdrav_id
        if not patient.gorzdrav_id:
            logger.warning(f"У пациента {patient.id} отсутствует gorzdrav_id")
            return

        # Получаем слоты по выбранным докторам
        doctors = await client.get_doctors(
            int(patient.prefer_lpu_id), schedule.specialist_id
        )
        doctor_ids = (
            schedule.preferred_doctors
            if schedule.preferred_doctors
            else [d.id for d in doctors.result]
        )

        # Создаем словарь для быстрого поиска имен докторов
        doctor_names = {d.id: d.name for d in doctors.result}

        # Ищем подходящие апойтменты у каждого врача
        start_t = schedule.preferred_time_start or time(0, 0)
        end_t = schedule.preferred_time_end or time(23, 59)

        for doctor_id in doctor_ids:
            doctor_name = doctor_names.get(doctor_id, f"ID:{doctor_id}")

            try:
                appointments = await client.get_appointments(
                    int(patient.prefer_lpu_id), doctor_id
                )
            except GorzdravAPIException as e:
                if e.error_code == 39:
                    logger.info(
                        f"Нет номерков для доктора {doctor_name}: {e.error_code}"
                    )
                else:
                    logger.warning(
                        f"Не удается получить записи для доктора {doctor_name}: {e.error_code}"
                    )
                continue
            except Exception as e:
                logger.warning(
                    f"Не удается получить записи для доктора {doctor_name}: {e}"
                )
                continue

            # Проверяем подходящие слоты
            for appointment in appointments.result:
                appointment_time = appointment.visitStart.time()
                if start_t <= appointment_time <= end_t:
                    # Найден подходящий слот - создаем запись
                    try:
                        await self._create_appointment_and_notify(
                            client, schedule, patient, appointment, doctor_name
                        )
                        return  # Выходим после успешной записи
                    except Exception as e:
                        logger.error(
                            f"Ошибка создания записи для расписания {schedule.id}: {e}"
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
        """Создает запись, отправляет уведомление и удаляет расписание"""
        try:
            # Создаем запись на прием
            create_request = AppointmentCreateRequest(
                lpuId=int(patient.prefer_lpu_id),
                patientId=patient.gorzdrav_id,
                appointmentId=appointment.id,
                patientLastName=patient.last_name,
                patientFirstName=patient.first_name,
                patientMiddleName=patient.middle_name,
                patientBirthdate=patient.birth_date.isoformat(),
                visitDate=appointment.visitStart.isoformat(),
                room=appointment.room,
                address=appointment.address,
                esiaId=None,
                referralId=None,
                ipmpiCardId=None,
                recipientEmail=patient.user.email,
            )

            create_response = await client.create_appointment(create_request)
            logger.info(f"Запись создана для пациента {patient.id}: {create_response}")

            # Удаляем расписание
            await ScheduleRepository.delete_schedule(schedule.id)
            logger.info(f"Расписание {schedule.id} удалено после успешной записи")

            # Отправляем уведомление пользователю
            await self._send_notification(patient, appointment, doctor_name)

        except Exception as e:
            logger.error(f"Ошибка в процессе создания записи: {e}")
            raise

    async def _send_notification(
        self,
        patient: Patient,
        appointment: Appointment,
        doctor_name: str,
    ) -> None:
        """Отправляет уведомление пользователю о созданной записи"""
        try:
            user_id = patient.user_id
            appointment_date = appointment.visitStart.strftime("%d.%m.%Y %H:%M")
            appointment_end = appointment.visitEnd.strftime("%H:%M")

            message = (
                f"🎉 <b>Запись на прием создана!</b>\n\n"
                f"👤 <b>Пациент:</b> {patient.last_name} {patient.first_name} {patient.middle_name}\n"
                f"👨‍⚕️ <b>Врач:</b> {doctor_name}\n"
                f"📅 <b>Дата и время:</b> {appointment_date}-{appointment_end}\n"
                f"✅ Ваше расписание автоматически удалено"
            )

            await bot.send_message(user_id, message)
            logger.info(f"Уведомление отправлено пользователю {user_id}")

        except Exception as e:
            logger.error(
                f"Ошибка отправки уведомления пользователю {patient.user_id}: {e}"
            )
