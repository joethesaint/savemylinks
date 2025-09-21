"""
Tests for UI functionality and JavaScript features.

This module tests the enhanced UI features including
search, filtering, theme toggle, and bulk operations UI.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db


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


class TestUIFunctionality:
    """Test cases for UI functionality."""

    @pytest.mark.asyncio
    async def test_home_page_loads(self, client: AsyncClient):
        """Test that the home page loads successfully."""
        response = await client.get("/")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for essential UI elements
        assert "SaveMyLinks" in content
        assert "search-input" in content
        assert "category-filter" in content
        assert "resources-list" in content
        assert "pagination-container" in content

    @pytest.mark.asyncio
    async def test_ui_components_present(self, client: AsyncClient):
        """Test that all enhanced UI components are present."""
        response = await client.get("/")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for enhanced search components
        assert "clear-search" in content
        assert "advanced-search-panel" in content
        assert "sort-select" in content
        assert "view-mode-grid" in content
        assert "view-mode-list" in content
        
        # Check for bulk operations
        assert "bulk-actions-toggle" in content
        assert "bulk-actions-bar" in content
        assert "bulk-delete-btn" in content
        assert "bulk-export-btn" in content
        
        # Check for theme toggle
        assert "themeToggle" in content

    @pytest.mark.asyncio
    async def test_javascript_files_included(self, client: AsyncClient):
        """Test that JavaScript files are properly included."""
        response = await client.get("/")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for script inclusions
        assert "script.js" in content
        assert "modern-clippy" in content

    @pytest.mark.asyncio
    async def test_css_styles_included(self, client: AsyncClient):
        """Test that CSS styles are properly included."""
        response = await client.get("/")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for CSS inclusions
        assert "style.css" in content
        assert "bulma" in content.lower()

    @pytest.mark.asyncio
    async def test_static_files_accessible(self, client: AsyncClient):
        """Test that static files are accessible."""
        # Test CSS file
        response = await client.get("/static/style.css")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")
        
        # Test JavaScript file
        response = await client.get("/static/script.js")
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "").lower()

    @pytest.mark.asyncio
    async def test_search_functionality_ui(self, client: AsyncClient):
        """Test search functionality through UI endpoints."""
        # Create test resource first
        resource_data = {
            "title": "Test Search Resource",
            "url": "https://testsearch.com",
            "description": "A resource for testing search",
            "category": "Testing"
        }
        create_response = await client.post("/api/resources/", json=resource_data)
        assert create_response.status_code == 201
        
        # Test search through API (which UI uses)
        search_response = await client.get("/api/resources/?search=Test Search")
        assert search_response.status_code == 200
        
        data = search_response.json()
        assert data["total"] >= 1
        assert any("Test Search" in resource["title"] for resource in data["resources"])

    @pytest.mark.asyncio
    async def test_category_filtering_ui(self, client: AsyncClient):
        """Test category filtering through UI endpoints."""
        # Create test resources with different categories
        resources_data = [
            {"title": "Dev Resource", "url": "https://dev.com", "category": "Development"},
            {"title": "Design Resource", "url": "https://design.com", "category": "Design"}
        ]
        
        for resource_data in resources_data:
            response = await client.post("/api/resources/", json=resource_data)
            assert response.status_code == 201
        
        # Test category filtering
        filter_response = await client.get("/api/resources/?category=Development")
        assert filter_response.status_code == 200
        
        data = filter_response.json()
        assert all(resource["category"] == "Development" for resource in data["resources"])

    @pytest.mark.asyncio
    async def test_pagination_ui(self, client: AsyncClient):
        """Test pagination functionality."""
        # Create multiple test resources
        for i in range(5):
            resource_data = {
                "title": f"Pagination Test {i}",
                "url": f"https://pagination{i}.com",
                "category": "Testing"
            }
            response = await client.post("/api/resources/", json=resource_data)
            assert response.status_code == 201
        
        # Test pagination
        page1_response = await client.get("/api/resources/?page=1&per_page=3")
        assert page1_response.status_code == 200
        
        page1_data = page1_response.json()
        assert page1_data["page"] == 1
        assert page1_data["per_page"] == 3
        assert len(page1_data["resources"]) <= 3

    @pytest.mark.asyncio
    async def test_categories_endpoint(self, client: AsyncClient):
        """Test categories endpoint for UI dropdown."""
        # Create resources with different categories
        categories = ["Web Development", "Design", "Marketing"]
        for i, category in enumerate(categories):
            resource_data = {
                "title": f"Resource {i}",
                "url": f"https://example{i}.com",
                "category": category
            }
            response = await client.post("/api/resources/", json=resource_data)
            assert response.status_code == 201
        
        # Test categories endpoint
        categories_response = await client.get("/api/resources/categories")
        assert categories_response.status_code == 200
        
        returned_categories = categories_response.json()
        assert isinstance(returned_categories, list)
        
        # Check that our test categories are included
        for category in categories:
            assert category in returned_categories

    @pytest.mark.asyncio
    async def test_responsive_design_elements(self, client: AsyncClient):
        """Test that responsive design elements are present."""
        response = await client.get("/")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for responsive classes (Bulma framework)
        assert "is-mobile" in content or "column" in content
        assert "container" in content
        
        # Check for viewport meta tag
        assert "viewport" in content
        assert "width=device-width" in content

    @pytest.mark.asyncio
    async def test_accessibility_features(self, client: AsyncClient):
        """Test accessibility features in the UI."""
        response = await client.get("/")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for accessibility attributes
        assert "aria-label" in content
        assert "role=" in content
        assert "alt=" in content or "aria-describedby" in content
        
        # Check for semantic HTML
        assert "<main" in content
        assert "<nav" in content
        assert "<section" in content or "<article" in content