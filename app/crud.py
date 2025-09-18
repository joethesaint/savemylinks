"""
CRUD operations for SaveMyLinks application.

This module implements Create, Read, Update, Delete operations for resources
using SQLAlchemy 2.0 async patterns.
"""

from typing import Optional, Sequence
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models import Resource
from app.schemas import ResourceCreate, ResourceUpdate


class ResourceCRUD:
    """CRUD operations for Resource model."""

    @staticmethod
    async def create(db: AsyncSession, resource_data: ResourceCreate) -> Resource:
        """
        Create a new resource.
        
        Args:
            db: Database session
            resource_data: Resource creation data
            
        Returns:
            Created resource instance
            
        Raises:
            IntegrityError: If URL already exists
        """
        db_resource = Resource(
            title=resource_data.title,
            url=str(resource_data.url),
            description=resource_data.description,
            category=resource_data.category
        )
        
        db.add(db_resource)
        try:
            await db.commit()
            await db.refresh(db_resource)
            return db_resource
        except IntegrityError:
            await db.rollback()
            raise

    @staticmethod
    async def get_by_id(db: AsyncSession, resource_id: int) -> Optional[Resource]:
        """
        Get a resource by ID.
        
        Args:
            db: Database session
            resource_id: Resource ID
            
        Returns:
            Resource instance or None if not found
        """
        result = await db.execute(
            select(Resource).where(Resource.id == resource_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_url(db: AsyncSession, url: str) -> Optional[Resource]:
        """
        Get a resource by URL.
        
        Args:
            db: Database session
            url: Resource URL
            
        Returns:
            Resource instance or None if not found
        """
        result = await db.execute(
            select(Resource).where(Resource.url == url)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> tuple[Sequence[Resource], int]:
        """
        Get all resources with pagination and filtering.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            category: Filter by category
            search: Search in title and description
            
        Returns:
            Tuple of (resources list, total count)
        """
        # Build base query
        query = select(Resource)
        count_query = select(func.count(Resource.id))
        
        # Apply filters
        if category:
            query = query.where(Resource.category == category)
            count_query = count_query.where(Resource.category == category)
            
        if search:
            search_filter = Resource.title.ilike(f"%{search}%") | Resource.description.ilike(f"%{search}%")
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        # Apply ordering and pagination
        query = query.order_by(desc(Resource.created_at)).offset(skip).limit(limit)
        
        # Execute queries
        result = await db.execute(query)
        resources = result.scalars().all()
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        return resources, total

    @staticmethod
    async def get_categories(db: AsyncSession) -> list[str]:
        """
        Get all unique categories.
        
        Args:
            db: Database session
            
        Returns:
            List of unique categories
        """
        result = await db.execute(
            select(Resource.category)
            .where(Resource.category.is_not(None))
            .distinct()
            .order_by(Resource.category)
        )
        return [category for category in result.scalars().all() if category]

    @staticmethod
    async def update(
        db: AsyncSession,
        resource_id: int,
        resource_data: ResourceUpdate
    ) -> Optional[Resource]:
        """
        Update a resource.
        
        Args:
            db: Database session
            resource_id: Resource ID
            resource_data: Resource update data
            
        Returns:
            Updated resource instance or None if not found
        """
        result = await db.execute(
            select(Resource).where(Resource.id == resource_id)
        )
        db_resource = result.scalar_one_or_none()
        
        if not db_resource:
            return None
        
        # Update only provided fields
        update_data = resource_data.model_dump(exclude_unset=True)
        if 'url' in update_data:
            update_data['url'] = str(update_data['url'])
            
        for field, value in update_data.items():
            setattr(db_resource, field, value)
        
        try:
            await db.commit()
            await db.refresh(db_resource)
            return db_resource
        except IntegrityError:
            await db.rollback()
            raise

    @staticmethod
    async def delete(db: AsyncSession, resource_id: int) -> bool:
        """
        Delete a resource.
        
        Args:
            db: Database session
            resource_id: Resource ID
            
        Returns:
            True if deleted, False if not found
        """
        result = await db.execute(
            select(Resource).where(Resource.id == resource_id)
        )
        db_resource = result.scalar_one_or_none()
        
        if not db_resource:
            return False
        
        await db.delete(db_resource)
        await db.commit()
        return True


# Create instance for easy import
resource_crud = ResourceCRUD()