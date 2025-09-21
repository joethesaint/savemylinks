"""CRUD operations for the SaveMyLinks application.

This module provides database operations using SQLAlchemy 2.0 async patterns
for managing resources with link preview metadata support.
"""

import logging
from typing import List, Optional, Dict, Any, Sequence
from sqlalchemy import select, func, distinct, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models import Resource
from app.schemas import ResourceCreate, ResourceUpdate
from app.services.metadata_extractor import metadata_extractor

logger = logging.getLogger(__name__)


class ResourceCRUD:
    """CRUD operations for Resource model."""

    async def create(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: ResourceCreate,
        extract_metadata: bool = True
    ) -> Resource:
        """
        Create a new resource with optional metadata extraction.
        
        Args:
            db: Database session
            obj_in: Resource creation data
            extract_metadata: Whether to extract metadata from URL
            
        Returns:
            Created resource instance
            
        Raises:
            IntegrityError: If URL already exists
        """
        # Convert Pydantic model to dict
        obj_data = obj_in.model_dump()
        
        # Convert HttpUrl to string for database storage
        if 'url' in obj_data:
            obj_data['url'] = str(obj_data['url'])
        
        # Extract metadata if requested
        if extract_metadata and obj_data.get('url'):
            try:
                metadata = await metadata_extractor.extract_metadata(str(obj_data['url']))
                obj_data['link_metadata'] = metadata
                
                # Use extracted title if no title provided
                if not obj_data.get('title') and metadata.get('title'):
                    obj_data['title'] = metadata['title']
                
                # Use extracted description if no description provided
                if not obj_data.get('description') and metadata.get('description'):
                    obj_data['description'] = metadata['description']
                    
                logger.info(f"Extracted metadata for URL: {obj_data['url']}")
            except Exception as e:
                logger.warning(f"Failed to extract metadata for {obj_data['url']}: {str(e)}")
                # Continue without metadata
        
        # Create database object
        db_obj = Resource(**obj_data)
        db.add(db_obj)
        
        try:
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
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
            # Enhanced search to include tags
            search_filter = (
                Resource.title.ilike(f"%{search}%") | 
                Resource.description.ilike(f"%{search}%") |
                func.json_extract(Resource.tags, '$').like(f'%{search}%')
            )
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

    async def get_multi_with_filters(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> Sequence[Resource]:
        """
        Get multiple resources with filtering and pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            category: Filter by category
            search: Search in title and description
            
        Returns:
            List of resources
        """
        # Build base query
        query = select(Resource)
        
        # Apply filters
        if category:
            query = query.where(Resource.category == category)
            
        if search:
            # Enhanced search to include tags
            search_filter = (
                Resource.title.ilike(f"%{search}%") | 
                Resource.description.ilike(f"%{search}%") |
                func.json_extract(Resource.tags, '$').like(f'%{search}%')
            )
            query = query.where(search_filter)
        
        # Apply ordering and pagination
        query = query.order_by(desc(Resource.created_at)).offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        return result.scalars().all()

    async def count_with_filters(
        self,
        db: AsyncSession,
        *,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> int:
        """
        Count resources with filtering.
        
        Args:
            db: Database session
            category: Filter by category
            search: Search in title and description
            
        Returns:
            Total count of filtered resources
        """
        # Build count query
        count_query = select(func.count(Resource.id))
        
        # Apply filters
        if category:
            count_query = count_query.where(Resource.category == category)
            
        if search:
            # Enhanced search to include tags
            search_filter = (
                Resource.title.ilike(f"%{search}%") | 
                Resource.description.ilike(f"%{search}%") |
                func.json_extract(Resource.tags, '$').like(f'%{search}%')
            )
            count_query = count_query.where(search_filter)
        
        # Execute query
        result = await db.execute(count_query)
        return result.scalar()

    async def get_tags(self, db: AsyncSession) -> List[str]:
        """
        Get all unique tags from all resources.
        
        Args:
            db: Database session
            
        Returns:
            List of unique tags
        """
        result = await db.execute(
            select(Resource.tags).where(Resource.tags.is_not(None))
        )
        
        all_tags = set()
        for tags_list in result.scalars():
            if tags_list:
                all_tags.update(tags_list)
        
        return sorted(list(all_tags))

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

    async def update(
        self, 
        db: AsyncSession, 
        *, 
        db_obj: Resource, 
        obj_in: ResourceUpdate,
        refresh_metadata: bool = False
    ) -> Resource:
        """
        Update an existing resource with optional metadata refresh.
        
        Args:
            db: Database session
            db_obj: Existing resource instance
            obj_in: Update data
            refresh_metadata: Whether to refresh metadata if URL changed
            
        Returns:
            Updated resource instance
        """
        # Get update data, excluding unset fields
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # Check if URL changed and refresh metadata if requested
        url_changed = 'url' in update_data and str(update_data['url']) != db_obj.url
        
        if refresh_metadata and url_changed:
            try:
                metadata = await metadata_extractor.extract_metadata(str(update_data['url']))
                update_data['link_metadata'] = metadata
                logger.info(f"Refreshed metadata for updated URL: {update_data['url']}")
            except Exception as e:
                logger.warning(f"Failed to refresh metadata for {update_data['url']}: {str(e)}")
        
        # Apply updates to the database object
        for field, value in update_data.items():
            # Convert HttpUrl to string for database storage
            if field == 'url' and hasattr(value, '__str__'):
                value = str(value)
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

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


    async def refresh_metadata(self, db: AsyncSession, *, db_obj: Resource) -> Resource:
        """
        Refresh metadata for an existing resource.
        
        Args:
            db: Database session
            db_obj: Resource instance to refresh metadata for
            
        Returns:
            Updated resource instance with refreshed metadata
        """
        try:
            metadata = await metadata_extractor.extract_metadata(db_obj.url)
            db_obj.link_metadata = metadata
            
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            
            logger.info(f"Refreshed metadata for resource {db_obj.id}: {db_obj.url}")
            return db_obj
        except Exception as e:
            logger.error(f"Failed to refresh metadata for resource {db_obj.id}: {str(e)}")
            await db.rollback()
            raise


# Create instance for easy import
resource_crud = ResourceCRUD()