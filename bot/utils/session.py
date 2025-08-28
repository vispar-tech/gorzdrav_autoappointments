import asyncio
from aiogram.client.bot import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import (
    RestartingTelegram,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.methods import TelegramMethod
from aiogram.methods.base import TelegramType

MAX_ATTEMPTS = 6
SLEEPY_TIME = 64


class SmartAiogramAiohttpSession(AiohttpSession):
    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,
    ) -> TelegramType:
        attempt = 0
        while True:
            attempt += 1
            try:
                res = await super().make_request(bot, method, timeout)
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except (RestartingTelegram, TelegramServerError):
                SLEEPY_TIME = MAX_ATTEMPTS if attempt > MAX_ATTEMPTS else 2**attempt
                await asyncio.sleep(SLEEPY_TIME)
            except Exception:
                raise
            else:
                return res
