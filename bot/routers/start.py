from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from .register import register_handler

router = Router(name="start")


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    # Прокси на регистрацию, как требовалось: старт запускает регистрацию
    await register_handler(message, state)
