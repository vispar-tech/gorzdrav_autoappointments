#!/usr/bin/env python3
"""Script for manual subscription activation."""

import argparse
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

from loguru import logger

from bot.db.context import get_or_create_session
from bot.db.services import PaymentsService, UsersService


async def activate_subscription(user_id: int, days: int = 30) -> None:
    """Activate subscription for a user."""

    try:
        async with get_or_create_session() as session:
            users_service = UsersService(session)
            payments_service = PaymentsService(session)

            # Get the user
            user = await users_service.get_user_by_id(user_id)
            if not user:
                logger.error(f"User with ID {user_id} not found")
                return

            # Check if there's already an active subscription
            if user.is_subscribed:
                if user.subscription_end:
                    logger.warning(
                        f"User {user_id} already has an active"
                        f" subscription until {user.subscription_end}",
                    )
                else:
                    logger.warning(
                        f"User {user_id} already has an unlimited subscription",
                    )
                return

            # Create payment record
            await payments_service.create_payment(
                user_id=user_id,
                yookassa_payment_id=f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                amount=Decimal("500.00"),  # 500 rubles
                currency="RUB",
                status="succeeded",
                description="Ручная активация подписки",
                metadata={
                    "manual_activation": True,
                    "activated_by": "admin",
                    "subscription_days": days,
                },
            )

            # Activate subscription
            user.is_subscribed = True
            user.subscription_end = datetime.now() + timedelta(days=days)

            await session.commit()

            logger.success(
                f"Subscription for {days} days successfully "
                f"activated for user {user_id}",
            )

    except Exception as e:
        logger.error(f"Error activating subscription for user {user_id}: {e}")


async def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="User subscription activation")
    parser.add_argument(
        "--telegram_id",
        type=int,
        required=True,
        help="User's Telegram ID",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of subscription days (default: 30)",
    )

    args = parser.parse_args()

    await activate_subscription(args.telegram_id, args.days)


if __name__ == "__main__":
    asyncio.run(main())
