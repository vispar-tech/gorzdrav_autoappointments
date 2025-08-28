from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Any, AsyncGenerator

from loguru import logger
from sqlalchemy import BigInteger, DateTime, Text, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import (
    mapped_column,
)

# Создаем движок для SQLite
engine = create_async_engine(
    url="sqlite+aiosqlite:///gorzdrav_bot.db",
)

# Создаем фабрику сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Аннотации для типов
uniq_str_an = Annotated[str, mapped_column(unique=True)]
content_an = Annotated[str | None, mapped_column(Text)]
big_int = Annotated[int, mapped_column(BigInteger)]
created_at_an = Annotated[datetime, mapped_column(DateTime, default=func.now())]
updated_at_an = Annotated[
    datetime, mapped_column(DateTime, default=func.now(), onupdate=func.now())
]


@asynccontextmanager
async def get_or_create_session(
    existing_session: AsyncSession | None = None,
) -> AsyncGenerator[AsyncSession, Any]:
    """
    Commit the session or rollback when exceptions occur

    Yields:
        The session.
    """

    if existing_session is None:
        async with async_session_maker() as session:
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


async def create_tables():
    """Создает все таблицы в базе данных"""
    from .models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Все таблицы созданы")


async def close_engine():
    """Закрывает движок базы данных"""
    await engine.dispose()
    logger.info("Движок базы данных закрыт")
