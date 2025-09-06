from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from loguru import logger

from bot.db.context import get_or_create_session
from bot.db.models.enums import ScheduleStatus
from bot.db.models.users import User
from bot.db.services import UsersService
from bot.loader import bot

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class SubscriptionCheckerConfig:
    """Configuration for checking subscriptions."""

    interval_seconds: int = 3600  # Check every hour


class SubscriptionCheckerService:
    """Service for checking subscription status."""

    def __init__(self, config: SubscriptionCheckerConfig | None = None) -> None:
        self._config = config or SubscriptionCheckerConfig()
        self._task: Optional[asyncio.Task[None]] = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        """Start subscription checker service."""
        if self._task and not self._task.done():
            return
        self._stopped.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("SubscriptionCheckerService started")

    async def stop(self) -> None:
        """Stop subscription checker service."""
        self._stopped.set()
        if self._task:
            await self._task
        logger.info("SubscriptionCheckerService stopped")

    async def _run_loop(self) -> None:
        try:
            while not self._stopped.is_set():
                await self._check_subscriptions()
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(
                        self._stopped.wait(),
                        timeout=self._config.interval_seconds,
                    )
        except Exception as e:
            logger.exception(f"Сервис проверки подписок упал: {e}")

    async def _check_subscriptions(self) -> None:
        """Check all subscriptions for users."""
        try:
            async with get_or_create_session() as session:
                users_service = UsersService(session)

                # get all users with active subscriptions
                subscribed_users = await users_service.find_all_where(
                    User.is_subscribed,
                )

                if not subscribed_users:
                    return

                current_time = datetime.now()

                for user in subscribed_users:
                    await self._process_user_subscription(
                        user,
                        current_time,
                        session,
                    )

        except Exception as e:
            logger.error(f"Ошибка при проверке подписок: {e}")

    async def _process_user_subscription(
        self,
        user: User,
        current_time: datetime,
        session: AsyncSession,
    ) -> None:
        """Process subscription for one user."""
        if not user.subscription_end:
            return

        # Проверяем, не истекла ли подписка
        if self.is_user_subscription_expired(user, current_time):
            await self._handle_expired_subscription(user, session)
            return

    async def _handle_expired_subscription(
        self,
        user: User,
        session: AsyncSession,
    ) -> None:
        """Handle expired subscription."""
        try:
            # Деактивируем подписку
            user.is_subscribed = False
            for patient in user.patients:
                for schedule in patient.schedules:
                    if schedule.status == ScheduleStatus.PENDING:
                        schedule.status = ScheduleStatus.CANCELLED

            # Отправляем уведомление
            await bot.send_message(
                chat_id=user.id,
                text=(
                    "<b>❌ Ваша подписка истекла</b>\n\n"
                    "Все ваши активные расписания были автоматически отменены.\n\n"
                    "Для продления подписки и возобновления работы с расписаниями "
                    "используйте команду /subscribe\n\n"
                ),
            )
            await session.commit()

            logger.info(
                f"Deactivated expired subscription for user {user.id}",
            )

        except Exception as e:
            logger.error(
                f"Error processing expired subscription for user {user.id}: {e}",
            )

    def is_user_subscription_expired(
        self,
        user: User,
        current_time: datetime,
    ) -> bool:
        """Проверить статус подписки конкретного пользователя."""
        try:
            if not user.subscription_end:
                return False
            return current_time > user.subscription_end
        except Exception as e:
            logger.error(
                f"Error checking subscription status for user {user.id}: {e}",
            )
            return False
