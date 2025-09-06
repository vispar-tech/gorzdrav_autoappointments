from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
)
from loguru import logger

from bot.db.context import get_or_create_session
from bot.db.services import UsersService
from bot.utils.keyboards import get_start_keyboard

router = Router(name="subscription")


@router.message(Command("my_subscription"))
async def my_subscription_handler(message: Message, state: FSMContext) -> None:
    """Handler for command /my_subscription to view subscription information."""
    await state.clear()

    if not message.from_user:
        await message.answer(
            "<b>❌ Техническая ошибка: отсутствует пользователь сообщения</b>",
        )
        return

    user_id = message.from_user.id

    try:
        async with get_or_create_session() as session:
            users_service = UsersService(session)
            user = await users_service.get_user_by_id(user_id)

            if not user:
                await message.answer(
                    "<b>❌ Пользователь не найден. "
                    "Используйте /start для регистрации.</b>",
                )
                return

            if user.is_subscribed:
                if user.subscription_end is None:
                    # Безлимитная подписка
                    await message.answer(
                        "<b>✅ У вас есть активная подписка</b>\n\n"
                        "Тип подписки: Безлимитная",
                        reply_markup=get_start_keyboard(),
                    )
                elif datetime.now() > user.subscription_end:
                    # Подписка истекла
                    user.is_subscribed = False
                    await session.commit()
                    await message.answer(
                        "<b>❌ Ваша подписка истекла</b>\n\n"
                        "Для продления подписки используйте команду /subscribe",
                        reply_markup=get_start_keyboard(),
                    )
                else:
                    # Активная подписка с датой окончания
                    remaining_days = (user.subscription_end - datetime.now()).days
                    await message.answer(
                        (
                            "<b>✅ У вас есть активная подписка</b>\n\n"
                            f"Подписка действует до: "
                            f"{user.subscription_end.strftime('%d.%m.%Y %H:%M')}\n"
                            f"<b>Осталось дней: {remaining_days}</b>"
                        ),
                        reply_markup=get_start_keyboard(),
                    )
            else:
                await message.answer(
                    "<b>❌ У вас нет активной подписки</b>\n\n"
                    "Для оформления подписки используйте команду /subscribe",
                    reply_markup=get_start_keyboard(),
                )

    except Exception as e:
        logger.error(
            f"Error getting subscription information for user {user_id}: {e}",
        )
        await message.answer(
            "<b>❌ Произошла ошибка при получении информации о подписке.</b>",
            reply_markup=get_start_keyboard(),
        )
