import sys
from pathlib import Path

from loguru import logger


def setup_logging() -> None:
    """Setup logging."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logger.remove()

    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",  # noqa: E501
        level="INFO",
    )

    logger.add(
        log_dir / "bot_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",  # noqa: E501
        level="DEBUG",
        rotation="1 day",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    logger.add(
        log_dir / "errors_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",  # noqa: E501
        level="ERROR",
        rotation="1 day",
        retention="90 days",
        compression="zip",
        encoding="utf-8",
    )
