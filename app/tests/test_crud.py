"""Tests for CRUD operations.

This module tests the database CRUD operations for resources.
Following the development rule: Use pytest for all testing with proper async support.
"""

import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Resource
from app.crud import resource_crud
from app.schemas import ResourceCreate, ResourceUpdate


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def async_session():
    """Create an async database session for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def sample_resource_data():
    """Sample resource data for testing."""
    return ResourceCreate(
        title="Test Resource",
        url="https://example.com",
        description="A test resource",
        category="Testing"
    )


@pytest.fixture
def another_resource_data():
    """Another sample resource data for testing."""
    return ResourceCreate(
        title="Another Resource",
        url="https://another-example.com",
        description="Another resource for development",
        category="Development"
    )


class TestResourceCRUD:
    """Test cases for Resource CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_resource(self, async_session: AsyncSession, sample_resource_data: ResourceCreate):
        """Test creating a new resource."""
        # Create resource
        resource = await resource_crud.create(async_session, sample_resource_data)
        
        # Assertions
        assert resource.id is not None
        assert resource.title == sample_resource_data.title
        assert resource.url == str(sample_resource_data.url)
        assert resource.description == sample_resource_data.description
        assert resource.category == sample_resource_data.category
        assert resource.created_at is not None
        assert resource.updated_at is not None

    @pytest.mark.asyncio
    async def test_create_duplicate_url_fails(self, async_session: AsyncSession, sample_resource_data: ResourceCreate):
        """Test that creating a resource with duplicate URL fails."""
        # Create first resource
        await resource_crud.create(async_session, sample_resource_data)
        
        # Try to create duplicate
        with pytest.raises(Exception):  # Should raise IntegrityError
            await resource_crud.create(async_session, sample_resource_data)

    @pytest.mark.asyncio
    async def test_get_resource_by_id(self, async_session: AsyncSession, sample_resource_data: ResourceCreate):
        """Test getting a resource by ID."""
        # Create resource
        created_resource = await resource_crud.create(async_session, sample_resource_data)
        
        # Get resource by ID
        retrieved_resource = await resource_crud.get_by_id(async_session, created_resource.id)
        
        # Assertions
        assert retrieved_resource is not None
        assert retrieved_resource.id == created_resource.id
        assert retrieved_resource.title == sample_resource_data.title

    @pytest.mark.asyncio
    async def test_get_nonexistent_resource_returns_none(self, async_session: AsyncSession):
        """Test that getting a nonexistent resource returns None."""
        resource = await resource_crud.get_by_id(async_session, 999)
        assert resource is None

    @pytest.mark.asyncio
    async def test_get_resource_by_url(self, async_session: AsyncSession, sample_resource_data: ResourceCreate):
        """Test getting a resource by URL."""
        # Create resource
        created_resource = await resource_crud.create(async_session, sample_resource_data)
        
        # Get resource by URL
        retrieved_resource = await resource_crud.get_by_url(async_session, str(sample_resource_data.url))
        
        # Assertions
        assert retrieved_resource is not None
        assert retrieved_resource.id == created_resource.id
        assert retrieved_resource.url == str(sample_resource_data.url)

    @pytest.mark.asyncio
    async def test_get_all_resources_empty(self, async_session: AsyncSession):
        """Test getting all resources when database is empty."""
        resources, total = await resource_crud.get_all(async_session)
        assert len(resources) == 0
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_all_resources_with_data(self, async_session: AsyncSession, sample_resource_data: ResourceCreate, another_resource_data: ResourceCreate):
        """Test getting all resources with data."""
        # Create resources
        await resource_crud.create(async_session, sample_resource_data)
        await resource_crud.create(async_session, another_resource_data)
        
        # Get all resources
        resources, total = await resource_crud.get_all(async_session)
        
        # Assertions
        assert len(resources) == 2
        assert total == 2
        titles = [r.title for r in resources]
        assert sample_resource_data.title in titles
        assert another_resource_data.title in titles

    @pytest.mark.asyncio
    async def test_get_all_resources_with_pagination(self, async_session: AsyncSession, sample_resource_data: ResourceCreate, another_resource_data: ResourceCreate):
        """Test getting resources with pagination."""
        # Create resources
        await resource_crud.create(async_session, sample_resource_data)
        await resource_crud.create(async_session, another_resource_data)
        
        # Get first page
        resources_page1, total = await resource_crud.get_all(async_session, skip=0, limit=1)
        assert len(resources_page1) == 1
        assert total == 2
        
        # Get second page
        resources_page2, total = await resource_crud.get_all(async_session, skip=1, limit=1)
        assert len(resources_page2) == 1
        assert total == 2
        
        # Ensure different resources
        assert resources_page1[0].id != resources_page2[0].id

    @pytest.mark.asyncio
    async def test_get_all_resources_with_category_filter(self, async_session: AsyncSession, sample_resource_data: ResourceCreate, another_resource_data: ResourceCreate):
        """Test getting resources filtered by category."""
        # Create resources
        await resource_crud.create(async_session, sample_resource_data)
        await resource_crud.create(async_session, another_resource_data)
        
        # Filter by category
        testing_resources, total = await resource_crud.get_all(async_session, category="Testing")
        dev_resources, total = await resource_crud.get_all(async_session, category="Development")
        
        # Assertions
        assert len(testing_resources) == 1
        assert len(dev_resources) == 1
        assert testing_resources[0].category == "Testing"
        assert dev_resources[0].category == "Development"

    @pytest.mark.asyncio
    async def test_get_all_resources_with_search(self, async_session: AsyncSession, sample_resource_data: ResourceCreate, another_resource_data: ResourceCreate):
        """Test getting resources with search query."""
        # Create resources
        await resource_crud.create(async_session, sample_resource_data)
        await resource_crud.create(async_session, another_resource_data)
        
        # Search for resources - the search uses ILIKE which is case-insensitive and partial matching
        # Since "Test Resource" contains "Resource" and "Another Resource" also contains "Resource",
        # we need to use more specific search terms
        test_results, test_total = await resource_crud.get_all(async_session, search="Test")
        another_results, another_total = await resource_crud.get_all(async_session, search="Another")
        all_results, all_total = await resource_crud.get_all(async_session)
        
        # Assertions
        assert len(test_results) == 1
        assert test_total == 1
        assert len(another_results) == 1
        assert another_total == 1
        assert len(all_results) == 2
        assert all_total == 2
        assert "Test" in test_results[0].title
        assert "Another" in another_results[0].title

    @pytest.mark.asyncio
    async def test_get_categories(self, async_session: AsyncSession, sample_resource_data: ResourceCreate, another_resource_data: ResourceCreate):
        """Test getting all unique categories."""
        # Create resources
        await resource_crud.create(async_session, sample_resource_data)
        await resource_crud.create(async_session, another_resource_data)
        
        # Get categories
        categories = await resource_crud.get_categories(async_session)
        
        # Assertions
        assert len(categories) == 2
        assert "Testing" in categories
        assert "Development" in categories

    @pytest.mark.asyncio
    async def test_update_resource(self, async_session: AsyncSession, sample_resource_data: ResourceCreate):
        """Test updating a resource."""
        # Create resource
        created_resource = await resource_crud.create(async_session, sample_resource_data)

        # Add a small delay to ensure timestamp difference
        import time
        time.sleep(0.01)

        # Update data
        update_data = ResourceUpdate(
            title="Updated Title",
            description="Updated description"
        )

        # Update resource
        updated_resource = await resource_crud.update(async_session, created_resource.id, update_data)

        # Assertions
        assert updated_resource is not None
        assert updated_resource.title == "Updated Title"
        assert updated_resource.description == "Updated description"
        assert updated_resource.url == str(sample_resource_data.url)  # Should remain unchanged
        assert updated_resource.updated_at >= updated_resource.created_at

    @pytest.mark.asyncio
    async def test_update_nonexistent_resource_returns_none(self, async_session: AsyncSession):
        """Test that updating a nonexistent resource returns None."""
        update_data = ResourceUpdate(title="Updated Title")
        updated_resource = await resource_crud.update(async_session, 999, update_data)
        assert updated_resource is None

    @pytest.mark.asyncio
    async def test_delete_resource(self, async_session: AsyncSession, sample_resource_data: ResourceCreate):
        """Test deleting a resource."""
        # Create resource
        created_resource = await resource_crud.create(async_session, sample_resource_data)
        
        # Delete resource
        deleted = await resource_crud.delete(async_session, created_resource.id)
        
        # Assertions
        assert deleted is True
        
        # Verify resource is deleted
        retrieved_resource = await resource_crud.get_by_id(async_session, created_resource.id)
        assert retrieved_resource is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_resource_returns_false(self, async_session: AsyncSession):
        """Test that deleting a nonexistent resource returns False."""
        deleted = await resource_crud.delete(async_session, 999)
        assert deleted is False