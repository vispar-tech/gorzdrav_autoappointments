import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import DeclarativeBase

from bot.db.meta import meta

logger = logging.getLogger(__name__)


class Base(AsyncAttrs, DeclarativeBase):
    """Base for all models."""

    __abstract__ = True
    metadata = meta

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the model to a dictionary with property fields.

        Returns:
            The dictionary.
        """
        property_fields = [
            prop.__name__
            for prop in inspect(self.__class__).all_orm_descriptors
            if isinstance(prop, hybrid_property)
        ]
        try:
            result = {**self.__dict__}
            for prop in property_fields:
                try:
                    result[prop] = getattr(self, prop)
                except AttributeError as err:
                    logger.error(f"Error on {prop}: {err}")
                    result[prop] = None
            return result
        except AttributeError as err:
            logger.error(f"Error on {self.__class__.__name__}: {err}")
            raise

    def __repr__(self) -> str:
        """
        Return a pretty representation of the model.

        Returns:
            The representation.
        """
        self_dict = self.to_dict()
        items = list(self_dict.items())[:2]
        params = ", ".join([f"{key}={value!r}" for key, value in items])
        if len(items) < len(self_dict):
            params += ", ..."
        return f"{self.__class__.__name__}({params})"
