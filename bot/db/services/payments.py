from decimal import Decimal
from typing import Any, Optional

from bot.db.models.payments import Payment
from bot.db.services.base import BaseService


class PaymentsService(BaseService[Payment]):
    """Service for working with payments."""

    model = Payment

    async def create_payment(
        self,
        user_id: int,
        yookassa_payment_id: str,
        amount: Decimal,
        currency: str = "RUB",
        status: str = "pending",
        description: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Payment:
        """Создать новый платеж."""
        payment = Payment(
            user_id=user_id,
            yookassa_payment_id=yookassa_payment_id,
            amount=amount,
            currency=currency,
            status=status,
            description=description,
            payment_metadata=metadata or {},
        )
        return await self.add_model(payment)
