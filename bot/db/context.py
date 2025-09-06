from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .engine import session_factory


@asynccontextmanager
async def get_or_create_session(
    existing_session: AsyncSession | None = None,
) -> AsyncGenerator[AsyncSession, Any]:
    """
    Commit the session or rollback when exceptions occur.

    Yields:
        The session.
    """

    if existing_session is None:
        async with session_factory() as session:
            await session.begin()
            try:
                yield session
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error while saving session, {e}")
                raise
            else:
                await session.commit()
            finally:
                await session.close()
    else:
        yield existing_session
