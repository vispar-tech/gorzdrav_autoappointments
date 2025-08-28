from typing import TYPE_CHECKING

import orjson
from loguru import logger

# Импортируем настройки логирования
from bot.settings.logging import setup_logging

from bot import routers
from bot.loader import bot, dispatcher, loop
from bot.utils.scheduler import AppointmentScheduler, SchedulerConfig
from bot.utils.session import SmartAiogramAiohttpSession
from bot.utils.commands import setup_default_commands
from bot.database.database import close_engine, create_tables

if TYPE_CHECKING:
    from aiogram.client.session.aiohttp import AiohttpSession


async def aiogram_on_startup_polling() -> None:
    # Создаём таблицы
    await create_tables()
    await bot.delete_webhook(drop_pending_updates=True)
    dispatcher["temp_bot_cloud_session"] = SmartAiogramAiohttpSession(
        json_loads=orjson.loads,
    )
    await setup_default_commands(bot)
    dispatcher.include_routers(
        routers.register_router, routers.start_router, routers.schedule_router
    )

    # Запускаем планировщик
    scheduler = AppointmentScheduler(SchedulerConfig(interval_seconds=10))
    dispatcher["appointment_scheduler"] = scheduler
    await scheduler.start()

    logger.info("Бот запущен")


async def aiogram_on_shutdown_polling() -> None:
    # Останавливаем планировщик
    scheduler: AppointmentScheduler | None = dispatcher.workflow_data.get(
        "appointment_scheduler"
    )  # type: ignore
    if scheduler:
        await scheduler.stop()

    await close_engine()
    await bot.session.close()
    if "temp_bot_cloud_session" in dispatcher.workflow_data:
        temp_bot_cloud_session: "AiohttpSession" = dispatcher["temp_bot_cloud_session"]
        await temp_bot_cloud_session.close()

    logger.info("Stopped polling")


def main() -> None:
    setup_logging()
    dispatcher.startup.register(aiogram_on_startup_polling)
    dispatcher.shutdown.register(aiogram_on_shutdown_polling)
    loop.run_until_complete(dispatcher.start_polling(bot))  # type: ignore


if __name__ == "__main__":
    main()
