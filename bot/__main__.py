from typing import TYPE_CHECKING

import orjson
from loguru import logger

from bot import routers
from bot.db.engine import close_engine
from bot.loader import bot, dispatcher, loop
from bot.settings.logging import setup_logging
from bot.utils.commands import setup_default_commands
from bot.utils.scheduler import AppointmentScheduler, SchedulerConfig
from bot.utils.session import SmartAiogramAiohttpSession
from bot.utils.subscriptions import (
    SubscriptionCheckerConfig,
    SubscriptionCheckerService,
)

if TYPE_CHECKING:
    from aiogram.client.session.aiohttp import AiohttpSession


async def aiogram_on_startup_polling() -> None:
    """AIogram on startup polling."""
    await bot.delete_webhook(drop_pending_updates=True)
    dispatcher["temp_bot_cloud_session"] = SmartAiogramAiohttpSession(
        json_loads=orjson.loads,
    )
    await setup_default_commands(bot)
    dispatcher.include_routers(
        routers.start_router,
        routers.schedules_router,
        routers.patients_router,
        routers.appointments_router,
        # routers.payments_router,  # Временно отключен
        routers.subscription_router,
    )

    # Start scheduler
    scheduler = AppointmentScheduler(SchedulerConfig(interval_seconds=30))
    dispatcher["appointment_scheduler"] = scheduler
    await scheduler.start()

    # Start subscription checker
    subscription_checker = SubscriptionCheckerService(
        SubscriptionCheckerConfig(interval_seconds=10),
    )
    dispatcher["subscription_checker"] = subscription_checker
    await subscription_checker.start()

    logger.info("Bot started")


async def aiogram_on_shutdown_polling() -> None:
    """AIogram on shutdown polling."""
    # Stop scheduler
    scheduler: AppointmentScheduler | None = dispatcher.workflow_data.get(
        "appointment_scheduler",
    )  # type: ignore
    if scheduler:
        await scheduler.stop()

    # Stop subscription checker
    subscription_checker: SubscriptionCheckerService | None = (
        dispatcher.workflow_data.get(
            "subscription_checker",
        )
    )  # type: ignore
    if subscription_checker:
        await subscription_checker.stop()

    await close_engine()
    await bot.session.close()
    if "temp_bot_cloud_session" in dispatcher.workflow_data:
        temp_bot_cloud_session: "AiohttpSession" = dispatcher["temp_bot_cloud_session"]
        await temp_bot_cloud_session.close()

    logger.info("Stopped polling")


def main() -> None:
    """Main function."""
    setup_logging()
    dispatcher.startup.register(aiogram_on_startup_polling)
    dispatcher.shutdown.register(aiogram_on_shutdown_polling)
    loop.run_until_complete(dispatcher.start_polling(bot))  # type: ignore


if __name__ == "__main__":
    main()
