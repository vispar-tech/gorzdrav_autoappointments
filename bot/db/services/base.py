from typing import (
    Any,
    Generic,
    Iterable,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    cast,
)

from sqlalchemy import (
    ColumnExpressionArgument,
    delete,
    exc,
    func,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.base import ExecutableOption

from bot.db.base import Base

T = TypeVar("T", bound=Base)
TRefresh = TypeVar("TRefresh", bound=Base)


class BaseService(Generic[T]):
    """
    Base service class providing CRUD operations and advanced query utilities.

    This class offers methods for creating, reading, updating, and deleting records,
    as well as advanced filtering, pagination, bulk operations, and query customization.

    Attributes:
        model: SQLAlchemy model class.
    """

    model: Type[T]
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the service with an async database session.

        Args:
            session: The SQLAlchemy AsyncSession to use for database operations.

        Raises:
            NotImplementedError: If the service does not define a model.
        """
        self.session = session
        if not hasattr(self, "model"):
            raise NotImplementedError("Service must define a model")

    async def save(self, obj: T | None = None) -> None:
        """
        Save a model instance to the database and commit the transaction.

        Args:
            obj: The model instance to save. If None,
            only flushes and commits the session.

        Returns:
            None
        """
        if obj:
            self.session.add(obj)
        await self.session.flush()
        return await self.session.commit()

    async def refresh(
        self,
        instance: TRefresh,
        attribute_names: Optional[Iterable[str]] = None,
    ) -> TRefresh:
        """
        Refresh the attributes of a model instance from the database.

        Args:
            instance: The model instance to refresh.
            attribute_names: Optional iterable of attribute names to refresh.

        Returns:
            The refreshed model instance.
        """
        await self.session.flush()
        await self.session.refresh(instance, attribute_names)
        return instance

    async def exists(self, *whereclauses: ColumnExpressionArgument[bool]) -> bool:
        """
        Check if any record exists matching the given conditions.

        Args:
            *whereclauses: SQLAlchemy filter expressions.

        Returns:
            True if any matching record exists, False otherwise.
        """
        query = select(func.exists().where(*whereclauses))
        result = await self.session.execute(query)
        return cast("bool", result.scalar_one())

    async def add_model(self, new_instance: T) -> T:
        """
        Add a new model instance to the session.

        Args:
            new_instance: The model instance to add.

        Returns:
            The added model instance.
        """
        self.session.add(new_instance)
        return new_instance

    async def find_one_or_none(
        self,
        options: Optional[List[ExecutableOption]] = None,
        **filter_by: Any,
    ) -> Optional[T]:
        """
        Retrieve a single record matching the given filter criteria.

        Args:
            options: Optional list of SQLAlchemy loader options.
            **filter_by: Field-value filters.

        Returns:
            The model instance if found, otherwise None.
        """
        query = select(self.model).filter_by(**filter_by)
        if options:
            query = query.options(*options)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def find_all(
        self,
        options: Optional[List[ExecutableOption]] = None,
        order_by: Optional[List[ColumnExpressionArgument[T]]] = None,
        **filter_by: Any,
    ) -> Sequence[T]:
        """
        Retrieve all records matching the given filter criteria.

        Args:
            options: Optional list of SQLAlchemy loader options.
            order_by: Optional list of sorting criteria.
            distinct: Whether to apply DISTINCT to the query.
            **filter_by: Field-value filters.

        Returns:
            A sequence of matching model instances.
        """
        query = select(self.model).filter_by(**filter_by)
        if options:
            query = query.options(*options)
        if order_by:
            query = query.order_by(*order_by)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def find_all_where(
        self,
        *whereclauses: ColumnExpressionArgument[bool],
        options: Optional[List[ExecutableOption]] = None,
        order_by: Optional[List[ColumnExpressionArgument[T]]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Sequence[T]:
        """
        Retrieve records using complex where conditions.

        Args:
            *whereclauses: SQLAlchemy filter expressions.
            options: Optional list of SQLAlchemy loader options.
            order_by: Optional list of sorting criteria.
            limit: Maximum number of results to return.
            offset: Number of results to skip.
            with_deleted: Whether to include deleted records in the results.
            query_fn: Optional function to further modify the query.

        Returns:
            A sequence of matching model instances.
        """
        query = select(self.model).where(*whereclauses)
        if options:
            query = query.options(*options)
        if order_by:
            query = query.order_by(*order_by)
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update(
        self,
        item_id: int,
        options: Optional[List[ExecutableOption]] = None,
        **update_data: Any,
    ) -> Optional[T]:
        """
        Update a record by its primary key.

        Args:
            item_id: The primary key value.
            options: Optional list of SQLAlchemy loader options.
            **update_data: Field-value pairs to update.

        Returns:
            The updated model instance, or None if not found.

        Raises:
            sqlalchemy.exc.NoResultFound: If no record matches the ID.
        """
        try:
            stmt = (
                update(self.model)
                .where(getattr(self.model, "id") == item_id)  # noqa: B009
                .values(**update_data)
                .returning(self.model)
            )
            if options:
                stmt = stmt.options(*options)

            result = await self.session.execute(
                stmt,
            )
            return result.scalar_one()
        except exc.NoResultFound:
            return None

    async def update_by_model(
        self,
        instance: T,
        **update_data: Any,
    ) -> T:
        """
        Update a model instance directly.

        Args:
            instance: The model instance to update.
            **update_data: Field-value pairs to update.

        Returns:
            The updated model instance.
        """
        for key, value in update_data.items():
            setattr(instance, key, value)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, item_id: int) -> None:
        """
        Delete a record by its primary key.

        Args:
            item_id: The primary key value to delete.

        Returns:
            None
        """
        await self.session.execute(
            delete(self.model).where(
                getattr(self.model, "id") == item_id,  # noqa: B009
            ),
        )

    async def delete_where(
        self,
        *whereclauses: ColumnExpressionArgument[bool],
    ) -> None:
        """
        Delete records matching the given conditions.

        Args:
            *whereclauses: SQLAlchemy filter expressions.

        Returns:
            None
        """
        await self.session.execute(delete(self.model).where(*whereclauses))
