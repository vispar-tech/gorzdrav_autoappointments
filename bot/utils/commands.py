from aiogram import Bot
from aiogram.types import BotCommand

DEFAULT_COMMANDS: list[BotCommand] = [
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="patients", description="Пациенты пользователя"),
    BotCommand(command="schedules", description="Все расписания всех пациентов"),
    BotCommand(command="appointments", description="Все записи всех пациентов"),
    BotCommand(command="subscribe", description="Оформить подписку"),
    BotCommand(command="my_subscription", description="Ваша подписка"),
    BotCommand(command="help", description="Помощь и поддержка"),
]


async def setup_default_commands(bot: Bot) -> None:
    """Ensures the bot has up-to-date default commands."""
    current_commands = await bot.get_my_commands()
    if current_commands != DEFAULT_COMMANDS:
        await bot.set_my_commands(DEFAULT_COMMANDS)
