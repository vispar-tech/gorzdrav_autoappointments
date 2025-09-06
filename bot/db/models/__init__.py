"""bot models."""

import pkgutil
from pathlib import Path

import bot.db.models.enums  # noqa: F401


def load_all_models() -> None:
    """Load all models from this folder."""
    package_dir = Path(__file__).resolve().parent
    modules = pkgutil.walk_packages(
        path=[str(package_dir)],
        prefix="bot.db.models.",
    )
    for module in modules:
        __import__(module.name)
