import asyncio
from pathlib import Path

import orjson
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram_fsm_storage import JSONStorage  # type: ignore

from bot.settings import settings
from bot.utils.session import SmartAiogramAiohttpSession

dp = Dispatcher(storage=JSONStorage(path="states.json"))
BASE_PATH = Path(__file__).parent.resolve()

loop = asyncio.get_event_loop()

storage = JSONStorage(path="data/states.json")
dispatcher = Dispatcher(storage=storage)

session = SmartAiogramAiohttpSession(json_loads=orjson.loads)
bot = Bot(
    settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML"),
    session=session,
)
