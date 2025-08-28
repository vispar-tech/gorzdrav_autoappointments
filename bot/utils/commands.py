from aiogram import Bot
from aiogram.types import BotCommand


DEFAULT_COMMANDS: list[BotCommand] = [
    BotCommand(command="start", description="Начать"),
    BotCommand(command="schedule", description="Расписания"),
    BotCommand(command="register", description="Зарегистрировать пациента"),
    BotCommand(command="profile", description="Профиль пациента"),
    BotCommand(command="patient", description="Пациент"),
    BotCommand(command="appointments", description="Мои записи"),
]


async def setup_default_commands(bot: Bot) -> None:
    """Требует, чтобы у бота были актуальные стандартные команды."""
    current_commands = await bot.get_my_commands()
    if current_commands != DEFAULT_COMMANDS:
        await bot.set_my_commands(DEFAULT_COMMANDS)
