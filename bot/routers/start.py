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
