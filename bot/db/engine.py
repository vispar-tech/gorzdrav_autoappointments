from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.settings import settings

engine = create_async_engine(str(settings.db_url), echo=settings.DB_ECHO)


session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def close_engine() -> None:
    """Close database engine."""
    await engine.dispose()
    logger.info("Close database engine")
