from typing import Any

from bot.db.models.users import User
from bot.db.services.base import BaseService


class UsersService(BaseService[User]):
    """Service for working with users."""

    model = User

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        return await self.find_one_or_none(id=user_id)

    async def get_or_create_user(self, user_id: int, **kwargs: Any) -> User:
        """Get or create user."""
        user = await self.find_one_or_none(id=user_id)
        if user is None:
            user = User(id=user_id, **kwargs)
            return await self.add_model(user)
        return user
