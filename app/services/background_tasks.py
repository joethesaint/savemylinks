"""
Background tasks for the SaveMyLinks application.

This module provides background task functionality for operations that
should not block API responses, such as metadata extraction.
"""

import asyncio
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.crud import resource_crud
from app.services.metadata_extractor import metadata_extractor, test_metadata_extractor

logger = logging.getLogger(__name__)


async def extract_metadata_background(resource_id: int) -> None:
    """
    Background task to extract metadata for a resource.
    
    This task runs asynchronously after resource creation to avoid
    blocking the API response while metadata is being fetched.
    
    Args:
        resource_id: ID of the resource to extract metadata for
    """
    try:
        # Get a new database session for the background task
        async with AsyncSessionLocal() as db:
            # Fetch the resource
            resource = await resource_crud.get_by_id(db, resource_id=resource_id)
            if not resource:
                logger.warning(f"Resource {resource_id} not found for metadata extraction")
                return
            
            # Skip if metadata already exists
            if resource.link_metadata:
                logger.info(f"Metadata already exists for resource {resource_id}")
                return
            
            # Extract metadata
            logger.info(f"Starting background metadata extraction for resource {resource_id}")
            metadata = await metadata_extractor.extract_metadata(resource.url)
            
            # Update the resource with metadata
            resource.link_metadata = metadata
            
            logger.info(f"Successfully extracted metadata for resource {resource_id}")
            
    except Exception as e:
        logger.error(f"Error extracting metadata for resource {resource_id}: {str(e)}")
        raise


async def refresh_metadata_background(resource_id: int) -> None:
    """
    Background task to refresh metadata for an existing resource.
    
    Args:
        resource_id: ID of the resource to refresh metadata for
    """
    try:
        # Get a new database session for the background task
        async with AsyncSessionLocal() as db:
            # Fetch the resource
            resource = await resource_crud.get_by_id(db, resource_id=resource_id)
            if not resource:
                logger.warning(f"Resource {resource_id} not found for metadata refresh")
                return
            
            # Refresh metadata
            logger.info(f"Starting background metadata refresh for resource {resource_id}")
            await resource_crud.refresh_metadata(db, db_obj=resource)
            
            logger.info(f"Successfully refreshed metadata for resource {resource_id}: {resource.url}")
            
    except Exception as e:
        logger.error(f"Background metadata refresh failed for resource {resource_id}: {str(e)}")


async def batch_refresh_metadata(limit: Optional[int] = None) -> None:
    """
    Background task to refresh metadata for multiple resources.
    
    This can be used for maintenance tasks or to update metadata
    for resources that were created before the metadata feature.
    
    Args:
        limit: Maximum number of resources to process (None for all)
    """
    try:
        async with AsyncSessionLocal() as db:
            # Get resources that need metadata refresh
            resources = await resource_crud.get_all(
                db, 
                skip=0, 
                limit=limit or 1000
            )
            
            logger.info(f"Starting batch metadata refresh for {len(resources)} resources")
            
            # Process each resource
            for resource in resources:
                try:
                    await resource_crud.refresh_metadata(db, db_obj=resource)
                    logger.info(f"Refreshed metadata for resource {resource.id}")
                    
                    # Add a small delay to avoid overwhelming external servers
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Failed to refresh metadata for resource {resource.id}: {str(e)}")
                    continue
            
            logger.info(f"Completed batch metadata refresh")
            
    except Exception as e:
        logger.error(f"Batch metadata refresh failed: {str(e)}")