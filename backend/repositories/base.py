"""
Base repository pattern for data access.

Provides common CRUD operations with multi-tenancy support.
"""

from typing import TypeVar, Generic, Type, Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.models.base import TimestampMixin


T = TypeVar('T')


class BaseRepository(Generic[T]):
    """
    Generic base repository providing common CRUD operations.

    All repositories should inherit from this class to ensure consistent
    data access patterns and multi-tenancy isolation.
    """

    def __init__(self, model: Type[T], db: Session):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db

    def get_by_id(self, id: UUID, organization_id: Optional[UUID] = None) -> Optional[T]:
        """
        Get entity by ID.

        Args:
            id: Entity ID
            organization_id: Organization ID for multi-tenancy filtering

        Returns:
            Entity if found, None otherwise
        """
        query = select(self.model).where(self.model.id == id)

        # Apply organization filter if model has organization_id
        if organization_id and hasattr(self.model, 'organization_id'):
            query = query.where(self.model.organization_id == organization_id)

        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def get_all(
        self,
        organization_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[T]:
        """
        Get all entities with pagination.

        Args:
            organization_id: Organization ID for multi-tenancy filtering
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of entities
        """
        query = select(self.model)

        # Apply organization filter if model has organization_id
        if organization_id and hasattr(self.model, 'organization_id'):
            query = query.where(self.model.organization_id == organization_id)

        # Apply ordering by created_at if model has it
        if hasattr(self.model, 'created_at'):
            query = query.order_by(self.model.created_at.desc())

        query = query.limit(limit).offset(offset)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def create(self, entity: T) -> T:
        """
        Create a new entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity with ID and timestamps
        """
        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)
        return entity

    def update(self, entity: T) -> T:
        """
        Update an existing entity.

        Args:
            entity: Entity to update

        Returns:
            Updated entity
        """
        self.db.flush()
        self.db.refresh(entity)
        return entity

    def delete(self, id: UUID, organization_id: Optional[UUID] = None) -> bool:
        """
        Delete an entity by ID.

        Args:
            id: Entity ID
            organization_id: Organization ID for multi-tenancy filtering

        Returns:
            True if entity was deleted, False if not found
        """
        entity = self.get_by_id(id, organization_id)
        if entity:
            self.db.delete(entity)
            self.db.flush()
            return True
        return False

    def count(self, organization_id: Optional[UUID] = None) -> int:
        """
        Count total entities.

        Args:
            organization_id: Organization ID for multi-tenancy filtering

        Returns:
            Total count of entities
        """
        from sqlalchemy import func

        query = select(func.count()).select_from(self.model)

        # Apply organization filter if model has organization_id
        if organization_id and hasattr(self.model, 'organization_id'):
            query = query.where(self.model.organization_id == organization_id)

        result = self.db.execute(query)
        return result.scalar_one()

    def exists(self, id: UUID, organization_id: Optional[UUID] = None) -> bool:
        """
        Check if entity exists.

        Args:
            id: Entity ID
            organization_id: Organization ID for multi-tenancy filtering

        Returns:
            True if entity exists, False otherwise
        """
        return self.get_by_id(id, organization_id) is not None
