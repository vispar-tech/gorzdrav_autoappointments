from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
)
from loguru import logger

from bot.db.context import get_or_create_session
from bot.db.services import UsersService
from bot.settings import settings
from bot.utils.callbacks import StartCallback
from bot.utils.keyboards import get_commands_reply_keyboard, get_start_keyboard
from bot.utils.texts import (
    FULL_HELP_TEXT,
    HELP_TEXT,
    WELCOME_TEXT,
    get_privacy_policy_text,
    get_user_aggrement_text,
)

router = Router(name="start")


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext) -> None:
    """Welcome message and user registration in the system."""
    await state.clear()

    if not message.from_user:
        await message.answer(
            "<b>❌ Техническая ошибка: отсутствует пользователь сообщения</b>",
        )
        return

    user_id = message.from_user.id

    try:
        async with get_or_create_session() as session:
            service = UsersService(session)
            user_data = {
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
            }

            await service.get_or_create_user(user_id, **user_data)

            welcome_text = WELCOME_TEXT.format(
                first_name=message.from_user.first_name or "дорогой пользователь",
                max_unsubscribed_patients=settings.MAX_UNSUBSCRIBED_PATIENTS,
                max_subscribed_patients=settings.MAX_SUBSCRIBED_PATIENTS,
                max_unsubscribed_schedules=settings.MAX_UNSUBSCRIBED_SCHEDULES,
                max_subscribed_schedules=settings.MAX_SUBSCRIBED_SCHEDULES,
            )

            # send welcome message with inline keyboard
            await message.answer(
                welcome_text,
                reply_markup=get_start_keyboard(),
            )

            # send additional message with keyboard
            await message.answer(
                "Так же вы можете воспользоваться клавиатурой "
                "с основными опциями ниже 🔽",
                reply_markup=get_commands_reply_keyboard(),
            )

            logger.info(
                f"User {user_id} ({message.from_user.username}) started the bot",
            )

    except Exception as e:
        logger.error(
            f"Error processing the /start command for user {user_id}: {e}",
        )
        await message.answer(
            "<b>❌ Произошла ошибка при запуске бота.</b>\n\n"
            "<i>Попробуйте позже или обратитесь к администратору.</i>",
        )


@router.callback_query(F.data == StartCallback.START_HELP)
async def start_help_callback(callback: CallbackQuery) -> None:
    """Handler for the 'Help' button."""
    await callback.answer()

    if callback.message:
        await callback.message.answer(
            HELP_TEXT.format(
                max_unsubscribed_patients=settings.MAX_UNSUBSCRIBED_PATIENTS,
                max_subscribed_patients=settings.MAX_SUBSCRIBED_PATIENTS,
                max_unsubscribed_schedules=settings.MAX_UNSUBSCRIBED_SCHEDULES,
                max_subscribed_schedules=settings.MAX_SUBSCRIBED_SCHEDULES,
            ),
        )


@router.callback_query(F.data == StartCallback.START_AGREEMENT)
async def start_agreement_callback(callback: CallbackQuery) -> None:
    """Handler for the 'User Agreement' button."""
    await callback.answer()

    if callback.message:
        await callback.message.answer(get_user_aggrement_text())


@router.callback_query(F.data == StartCallback.START_PRIVACY)
async def start_privacy_callback(callback: CallbackQuery) -> None:
    """Handler for the 'Privacy Policy' button."""
    await callback.answer()

    if callback.message:
        await callback.message.answer(get_privacy_policy_text())


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    """Handler for the /help command."""
    await message.answer(
        FULL_HELP_TEXT.format(
            max_unsubscribed_patients=settings.MAX_UNSUBSCRIBED_PATIENTS,
            max_subscribed_patients=settings.MAX_SUBSCRIBED_PATIENTS,
            max_unsubscribed_schedules=settings.MAX_UNSUBSCRIBED_SCHEDULES,
            max_subscribed_schedules=settings.MAX_SUBSCRIBED_SCHEDULES,
        ),
    )


@router.message(F.text == "ℹ️ Помощь")
async def help_button_handler(message: Message) -> None:
    """Handler for the 'Помощь' button."""
    await message.answer(
        FULL_HELP_TEXT.format(
            max_unsubscribed_patients=settings.MAX_UNSUBSCRIBED_PATIENTS,
            max_subscribed_patients=settings.MAX_SUBSCRIBED_PATIENTS,
            max_unsubscribed_schedules=settings.MAX_UNSUBSCRIBED_SCHEDULES,
            max_subscribed_schedules=settings.MAX_SUBSCRIBED_SCHEDULES,
        ),
    )


@router.message(Command("subscribe"))
async def subscribe_handler(message: Message, state: FSMContext) -> None:
    """Handler for command /subscribe to show payment contacts."""
    await state.clear()

    if not message.from_user:
        await message.answer(
            "<b>❌ Техническая ошибка: отсутствует пользователь сообщения</b>",
        )
        return

    user_id = message.from_user.id

    try:
        async with get_or_create_session() as session:
            service = UsersService(session)
            user = await service.get_user_by_id(user_id)

            if not user:
                await message.answer(
                    "<b>❌ Пользователь не найден. "
                    "Используйте /start для регистрации.</b>",
                )
                return

            # Проверяем, есть ли уже активная подписка
            if user.is_subscribed:
                sub_duration_text = (
                    (
                        "Подписка действует до: "
                        f"{user.subscription_end.strftime('%d.%m.%Y %H:%M')}"
                    )
                    if user.subscription_end
                    else "Безлимитная подписка"
                )
                await message.answer(
                    "<b>✅ У вас уже есть активная подписка!</b>\n\n"
                    + sub_duration_text,
                )
                return

            # Показываем информацию о подписке и контакты для оплаты
            subscription_text = """
💳 <b>Оформление подписки</b>

💰 <b>Стоимость:</b> 500 ₽
⏰ <b>Срок действия:</b> 30 дней

✨ <b>Что дает подписка:</b>
• До 10 пациентов для записи
• До 10 активных расписаний
• Безлимитное исполнение расписаний
• Приоритетная исполнение расписаний
• Приоритетная поддержка

📞 <b>Для оплаты свяжитесь со мной:</b>
• Telegram: <a href="https://t.me/vispar_work">@vispar_work</a>

⏱️ <b>Время обработки:</b> до 24 часов
"""

            await message.answer(
                subscription_text,
                parse_mode="HTML",
                reply_markup=get_start_keyboard(),
            )

    except Exception as e:
        logger.error(f"Error showing subscription info for user {user_id}: {e}")
        await message.answer(
            "<b>❌ Произошла ошибка. Попробуйте позже.</b>",
            reply_markup=get_start_keyboard(),
        )


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
            service = UsersService(session)
            user = await service.get_user_by_id(user_id)

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
