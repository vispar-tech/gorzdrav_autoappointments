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
    """Smart AIogram Aiohttp Session."""

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,
    ) -> TelegramType:
        """Make request."""
        attempt = 0
        while True:
            attempt += 1
            try:
                res = await super().make_request(bot, method, timeout)
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except (RestartingTelegram, TelegramServerError):
                sleepy_time = MAX_ATTEMPTS if attempt > MAX_ATTEMPTS else 2**attempt
                await asyncio.sleep(sleepy_time)
            except Exception:
                raise
            else:
                return res
