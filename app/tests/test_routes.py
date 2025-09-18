"""
Tests for API routes.

This module tests the FastAPI routes using httpx.AsyncClient with async support.
Following the development rule: Use pytest for all testing with proper async support.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import Resource


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


@pytest_asyncio.fixture
async def client(async_session: AsyncSession):
    """Create an async HTTP client for testing."""
    async def override_get_db():
        yield async_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


class TestResourceRoutes:
    """Test cases for Resource API routes."""

    @pytest.mark.asyncio
    async def test_create_resource_success(self, client: AsyncClient):
        """Test successful resource creation."""
        resource_data = {
            "title": "Test Resource",
            "url": "https://example.com",
            "description": "A test resource",
            "category": "Testing"
        }
        
        response = await client.post("/api/resources/", json=resource_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == resource_data["title"]
        assert data["url"] == "https://example.com/"  # URL gets normalized with trailing slash
        assert data["description"] == resource_data["description"]
        assert data["category"] == resource_data["category"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_create_resource_duplicate_url(self, client: AsyncClient):
        """Test creating resource with duplicate URL fails."""
        resource_data = {
            "title": "Test Resource",
            "url": "https://example.com",
            "description": "A test resource",
            "category": "Testing"
        }
        
        # Create first resource
        response1 = await client.post("/api/resources/", json=resource_data)
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = await client.post("/api/resources/", json=resource_data)
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_resource_invalid_url(self, client: AsyncClient):
        """Test creating resource with invalid URL fails."""
        resource_data = {
            "title": "Test Resource",
            "url": "not-a-valid-url",
            "description": "A test resource",
            "category": "Testing"
        }
        
        response = await client.post("/api/resources/", json=resource_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_resource_by_id_success(self, client: AsyncClient):
        """Test getting resource by ID."""
        # Create a resource first
        resource_data = {
            "title": "Test Resource",
            "url": "https://example.com",
            "description": "A test resource",
            "category": "Testing"
        }
        
        create_response = await client.post("/api/resources/", json=resource_data)
        created_resource = create_response.json()
        
        # Get the resource
        response = await client.get(f"/api/resources/{created_resource['id']}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_resource["id"]
        assert data["title"] == resource_data["title"]

    @pytest.mark.asyncio
    async def test_get_resource_by_id_not_found(self, client: AsyncClient):
        """Test getting non-existent resource returns 404."""
        response = await client.get("/api/resources/999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_all_resources_empty(self, client: AsyncClient):
        """Test getting all resources when none exist."""
        response = await client.get("/api/resources/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["resources"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_all_resources_with_data(self, client: AsyncClient):
        """Test getting all resources with data."""
        # Create test resources
        resources_data = [
            {
                "title": "Resource 1",
                "url": "https://example1.com",
                "description": "First resource",
                "category": "Testing"
            },
            {
                "title": "Resource 2",
                "url": "https://example2.com",
                "description": "Second resource",
                "category": "Development"
            }
        ]
        
        for resource_data in resources_data:
            await client.post("/api/resources/", json=resource_data)
        
        response = await client.get("/api/resources/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["resources"]) == 2
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_get_all_resources_with_pagination(self, client: AsyncClient):
        """Test getting resources with pagination."""
        # Create multiple resources
        for i in range(5):
            resource_data = {
                "title": f"Resource {i}",
                "url": f"https://example{i}.com",
                "description": f"Resource number {i}",
                "category": "Testing"
            }
            await client.post("/api/resources/", json=resource_data)
        
        # Test pagination
        response = await client.get("/api/resources/?page=2&per_page=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["resources"]) == 2
        assert data["total"] == 5

    @pytest.mark.asyncio
    async def test_get_all_resources_with_category_filter(self, client: AsyncClient):
        """Test getting resources filtered by category."""
        # Create resources with different categories
        resources_data = [
            {
                "title": "Test Resource",
                "url": "https://test.com",
                "description": "Test resource",
                "category": "Testing"
            },
            {
                "title": "Dev Resource",
                "url": "https://dev.com",
                "description": "Development resource",
                "category": "Development"
            }
        ]
        
        for resource_data in resources_data:
            await client.post("/api/resources/", json=resource_data)
        
        response = await client.get("/api/resources/?category=Testing")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["resources"]) == 1
        assert data["resources"][0]["category"] == "Testing"

    @pytest.mark.asyncio
    async def test_get_all_resources_with_search(self, client: AsyncClient):
        """Test getting resources with search query."""
        # Create resources
        resources_data = [
            {
                "title": "Python Tutorial",
                "url": "https://python.com",
                "description": "Learn Python programming",
                "category": "Programming"
            },
            {
                "title": "JavaScript Guide",
                "url": "https://js.com",
                "description": "JavaScript development guide",
                "category": "Programming"
            }
        ]
        
        for resource_data in resources_data:
            await client.post("/api/resources/", json=resource_data)
        
        response = await client.get("/api/resources/?search=Python")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["resources"]) == 1
        assert "Python" in data["resources"][0]["title"]

    @pytest.mark.asyncio
    async def test_get_categories(self, client: AsyncClient):
        """Test getting all categories."""
        # Create resources with different categories
        resources_data = [
            {
                "title": "Resource 1",
                "url": "https://example1.com",
                "description": "First resource",
                "category": "Testing"
            },
            {
                "title": "Resource 2",
                "url": "https://example2.com",
                "description": "Second resource",
                "category": "Development"
            }
        ]
        
        for resource_data in resources_data:
            await client.post("/api/resources/", json=resource_data)
        
        response = await client.get("/api/resources/categories")
        
        assert response.status_code == 200
        categories = response.json()
        assert "Testing" in categories
        assert "Development" in categories

    @pytest.mark.asyncio
    async def test_update_resource_success(self, client: AsyncClient):
        """Test successful resource update."""
        # Create a resource first
        resource_data = {
            "title": "Original Title",
            "url": "https://example.com",
            "description": "Original description",
            "category": "Testing"
        }
        
        create_response = await client.post("/api/resources/", json=resource_data)
        created_resource = create_response.json()
        
        # Update the resource
        update_data = {
            "title": "Updated Title",
            "description": "Updated description"
        }
        
        response = await client.put(f"/api/resources/{created_resource['id']}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "Updated description"
        assert data["url"] == "https://example.com/"  # URL gets normalized with trailing slash

    @pytest.mark.asyncio
    async def test_update_resource_duplicate_url(self, client: AsyncClient):
        """Test updating resource with duplicate URL fails."""
        # Create two resources
        resource1_data = {
            "title": "Resource 1",
            "url": "https://example1.com",
            "description": "First resource",
            "category": "Testing"
        }
        resource2_data = {
            "title": "Resource 2",
            "url": "https://example2.com",
            "description": "Second resource",
            "category": "Testing"
        }
        
        response1 = await client.post("/api/resources/", json=resource1_data)
        response2 = await client.post("/api/resources/", json=resource2_data)
        
        resource1_id = response1.json()["id"]
        
        # Try to update resource1 with resource2's URL
        update_data = {"url": "https://example2.com"}
        response = await client.put(f"/api/resources/{resource1_id}", json=update_data)
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_resource_not_found(self, client: AsyncClient):
        """Test updating non-existent resource returns 404."""
        update_data = {
            "title": "Updated Title"
        }
        
        response = await client.put("/api/resources/999", json=update_data)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_resource_success(self, client: AsyncClient):
        """Test successful resource deletion."""
        # Create a resource first
        resource_data = {
            "title": "To Delete",
            "url": "https://example.com",
            "description": "Resource to delete",
            "category": "Testing"
        }
        
        create_response = await client.post("/api/resources/", json=resource_data)
        created_resource = create_response.json()
        
        # Delete the resource
        response = await client.delete(f"/api/resources/{created_resource['id']}")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Resource deleted successfully"
        
        # Verify it's deleted
        get_response = await client.get(f"/api/resources/{created_resource['id']}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_resource_not_found(self, client: AsyncClient):
        """Test deleting non-existent resource returns 404."""
        response = await client.delete("/api/resources/999")
        assert response.status_code == 404


class TestWebRoutes:
    """Test cases for web routes."""

    @pytest.mark.asyncio
    async def test_home_page(self, client: AsyncClient):
        """Test home page loads successfully."""
        response = await client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_add_page(self, client: AsyncClient):
        """Test add resource page loads successfully."""
        response = await client.get("/add")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"