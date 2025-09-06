"""Роутер для обработки платежей через Telegram Payments."""

import json
from datetime import datetime, timedelta
from decimal import Decimal

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from loguru import logger

from bot.db.context import get_or_create_session
from bot.db.services import PaymentsService, UsersService
from bot.settings import settings
from bot.utils.keyboards import get_start_keyboard
from bot.utils.texts import SUBSCRIPTION_TEXT

router = Router(name="payments")

# Стоимость подписки (в копейках)
SUBSCRIPTION_PRICE_KOPECKS = settings.SUBSCRIPTION_PRICE
SUBSCRIPTION_DURATION_DAYS = 30

# Данные для чека (54-ФЗ)
PROVIDER_DATA = {
    "receipt": {
        "items": [
            {
                "description": "Подписка на месяц - МедБот СПб",
                "quantity": "1.00",
                "amount": {
                    "value": f"{SUBSCRIPTION_PRICE_KOPECKS / 100:.2f}",
                    "currency": settings.CURRENCY,
                },
                "vat_code": 1,  # Для самозанятых
            },
        ],
    },
}


@router.message(Command("subscribe"))
async def subscribe_handler(message: Message, state: FSMContext) -> None:
    """Handler for command /subscribe to create a subscription."""
    await state.clear()

    if not message.from_user:
        await message.answer(
            "<b>❌ Техническая ошибка: отсутствует пользователь сообщения</b>",
        )
        return

    if not message.bot:
        await message.answer(
            "<b>❌ Техническая ошибка: отсутствует бот сообщения</b>",
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

            provider_token = settings.PROVIDER_TOKEN
            # Создаем инвойс
            prices = [
                LabeledPrice(
                    label="Подписка на месяц - МедБот СПб",
                    amount=SUBSCRIPTION_PRICE_KOPECKS,
                ),
            ]

            await message.bot.send_invoice(
                chat_id=message.chat.id,
                title="Подписка на месяц - МедБот СПб",
                description=SUBSCRIPTION_TEXT.format(
                    price=SUBSCRIPTION_PRICE_KOPECKS / 100,
                    days=SUBSCRIPTION_DURATION_DAYS,
                ),
                payload="subscription_payment",
                provider_token=provider_token,
                currency=settings.CURRENCY,
                prices=prices,
                need_phone_number=True,
                send_phone_number_to_provider=True,
                provider_data=json.dumps(PROVIDER_DATA),
            )

    except Exception as e:
        logger.error(f"Error creating subscription for user {user_id}: {e}")
        await message.answer(
            "<b>❌ Произошла ошибка при создании подписки. Попробуйте позже.</b>",
            reply_markup=get_start_keyboard(),
        )


@router.pre_checkout_query()
async def process_pre_checkout_query(
    pre_checkout_query: PreCheckoutQuery,
    bot: Bot,
) -> None:
    """Handler for pre-checkout query."""

    try:
        # Всегда отвечаем утвердительно
        await bot.answer_pre_checkout_query(
            pre_checkout_query.id,
            ok=True,
        )
        logger.info(f"Pre-checkout query approved: {pre_checkout_query.id}")
    except Exception as e:
        logger.error(f"Ошибка при обработке pre-checkout query: {e}")


@router.message(F.successful_payment)
async def process_successful_payment(
    message: Message,
    state: FSMContext,
) -> None:
    """Handler for successful payment."""
    await state.clear()

    if not message.from_user or not message.successful_payment:
        await message.answer("❌ Ошибка при обработке платежа")
        return

    user_id = message.from_user.id
    payment = message.successful_payment

    try:
        async with get_or_create_session() as session:
            users_service = UsersService(session)
            payments_service = PaymentsService(session)

            user = await users_service.get_user_by_id(user_id)
            if not user:
                await message.answer("❌ Пользователь не найден")
                return

            # Сохраняем информацию о платеже
            await payments_service.create_payment(
                user_id=user_id,
                yookassa_payment_id=f"tg_{payment.telegram_payment_charge_id}",
                amount=Decimal(payment.total_amount / 100),
                currency=payment.currency,
                status="succeeded",
                description="Подписка на месяц - МедБот СПб",
                metadata={
                    "telegram_payment_charge_id": payment.telegram_payment_charge_id,
                    "provider_payment_charge_id": payment.provider_payment_charge_id,
                    "subscription_days": SUBSCRIPTION_DURATION_DAYS,
                },
            )

            # Активируем подписку
            user.is_subscribed = True
            user.subscription_end = datetime.now() + timedelta(
                days=SUBSCRIPTION_DURATION_DAYS,
            )
            await session.commit()

            # Уведомляем пользователя
            await message.answer(
                f"<b>✅ Платеж на сумму {payment.total_amount // 100} "
                f"{payment.currency} прошел успешно!</b>\n\n"
                f"Ваша подписка активирована на {SUBSCRIPTION_DURATION_DAYS} дней",
            )

            logger.info(f"Успешный платеж от пользователя {user_id}")

    except Exception as e:
        logger.error(f"Ошибка при обработке успешного платежа: {e}")
        await message.answer(
            "❌ Произошла ошибка при активации подписки. Обратитесь в поддержку.",
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
            users_service = UsersService(session)
            user = await users_service.get_user_by_id(user_id)

            if not user:
                await message.answer(
                    "<b>❌ Пользователь не найден. "
                    "Используйте /start для регистрации.</b>",
                )
                return

            if user.is_subscribed and user.subscription_end:
                # Проверяем, не истекла ли подписка
                if datetime.now() > user.subscription_end:
                    user.is_subscribed = False
                    await session.commit()
                    await message.answer(
                        "<b>❌ Ваша подписка истекла</b>\n\n"
                        "Для продления подписки используйте команду /subscribe",
                        reply_markup=get_start_keyboard(),
                    )
                else:
                    remaining_days = (user.subscription_end - datetime.now()).days
                    await message.answer(
                        (
                            "<b>✅ У вас есть активная подписка</b>\n\n"
                            f"Подписка действует до: "
                            f"{user.subscription_end.strftime('%d.%m.%Y %H:%M')}\n"
                            f"Осталось дней: {remaining_days}"
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
