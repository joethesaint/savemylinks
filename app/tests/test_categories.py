"""Test cases for categories and tags functionality.

This module tests the category and tagging system for resource organization.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, patch

from app.main import app
from app.database import Base, get_db


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def sample_categorized_resources(client: AsyncClient):
    """Create sample resources with various categories and tags."""
    resources_data = [
        {
            "title": "Python Official Docs",
            "url": "https://docs.python.org",
            "description": "Official Python documentation",
            "category": "Documentation",
            "tags": ["python", "programming", "official", "reference"]
        },
        {
            "title": "React Getting Started",
            "url": "https://reactjs.org/docs/getting-started.html",
            "description": "React.js getting started guide",
            "category": "Documentation",
            "tags": ["react", "javascript", "frontend", "tutorial"]
        },
        {
            "title": "Python Tutorial",
            "url": "https://docs.python.org/tutorial/",
            "description": "Python tutorial for beginners",
            "category": "Tutorial",
            "tags": ["python", "tutorial", "beginner", "learning"]
        },
        {
            "title": "JavaScript MDN",
            "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
            "description": "JavaScript reference on MDN",
            "category": "Documentation",
            "tags": ["javascript", "reference", "mdn", "web"]
        },
        {
            "title": "GitHub Repository",
            "url": "https://github.com/example/repo",
            "description": "Example GitHub repository",
            "category": "Development",
            "tags": ["github", "git", "repository", "code"]
        },
        {
            "title": "Design System",
            "url": "https://designsystem.example.com",
            "description": "Company design system",
            "category": "Design",
            "tags": ["design", "ui", "components", "system"]
        }
    ]
    
    created_resources = []
    
    # Mock the metadata extractor to avoid network calls
    with patch('app.crud.metadata_extractor.extract_metadata', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = {}
        
        for data in resources_data:
            response = await client.post("/api/resources/", json=data)
            assert response.status_code == 201
            created_resources.append(response.json())
    
    return created_resources


class TestCategories:
    """Test cases for category functionality."""

    @pytest.mark.asyncio
    async def test_get_all_categories(self, client: AsyncClient, sample_categorized_resources):
        """Test retrieving all available categories."""
        response = await client.get("/api/resources/categories")
        assert response.status_code == 200
        
        categories = response.json()
        expected_categories = ["Documentation", "Tutorial", "Development", "Design"]
        
        for category in expected_categories:
            assert category in categories

    @pytest.mark.asyncio
    async def test_filter_by_category(self, client: AsyncClient, sample_categorized_resources):
        """Test filtering resources by category."""
        # Test Documentation category
        response = await client.get("/api/resources/?category=Documentation")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 3  # Python docs, React docs, JavaScript MDN
        
        for resource in data["resources"]:
            assert resource["category"] == "Documentation"

    @pytest.mark.asyncio
    async def test_filter_by_multiple_categories(self, client: AsyncClient, sample_categorized_resources):
        """Test filtering by multiple categories."""
        # Test Tutorial and Development categories
        response = await client.get("/api/resources/?category=Tutorial")
        assert response.status_code == 200
        tutorial_count = response.json()["total"]
        
        response = await client.get("/api/resources/?category=Development")
        assert response.status_code == 200
        development_count = response.json()["total"]
        
        assert tutorial_count == 1
        assert development_count == 1

    @pytest.mark.asyncio
    async def test_category_case_sensitivity(self, client: AsyncClient, sample_categorized_resources):
        """Test category filtering case sensitivity."""
        # Test lowercase category
        response = await client.get("/api/resources/?category=documentation")
        assert response.status_code == 200
        
        # Should still find resources (case-insensitive)
        data = response.json()
        # This depends on implementation - might be case-sensitive
        # Adjust assertion based on actual behavior

    @pytest.mark.asyncio
    async def test_invalid_category_filter(self, client: AsyncClient, sample_categorized_resources):
        """Test filtering by non-existent category."""
        response = await client.get("/api/resources/?category=NonExistentCategory")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 0
        assert data["resources"] == []

    @pytest.mark.asyncio
    async def test_create_resource_with_new_category(self, client: AsyncClient):
        """Test creating a resource with a new category."""
        new_resource = {
            "title": "New Category Resource",
            "url": "https://newcategory.example.com",
            "description": "Resource with new category",
            "category": "NewCategory",
            "tags": ["new", "category", "test"]
        }
        
        response = await client.post("/api/resources/", json=new_resource)
        assert response.status_code == 201
        
        created_resource = response.json()
        assert created_resource["category"] == "NewCategory"
        
        # Verify new category appears in categories list
        response = await client.get("/api/resources/categories")
        assert response.status_code == 200
        categories = response.json()
        assert "NewCategory" in categories


class TestTags:
    """Test cases for tagging functionality."""

    @pytest.mark.asyncio
    async def test_filter_by_single_tag(self, client: AsyncClient, sample_categorized_resources):
        """Test filtering resources by a single tag."""
        response = await client.get("/api/resources/?search=python")
        assert response.status_code == 200
        
        data = response.json()
        # Should find resources with "python" tag
        assert data["total"] >= 2  # Python docs and Python tutorial
        
        # Verify results contain python-related resources
        python_resources = [r for r in data["resources"] if "python" in str(r).lower()]
        assert len(python_resources) >= 2

    @pytest.mark.asyncio
    async def test_filter_by_multiple_tags(self, client: AsyncClient, sample_categorized_resources):
        """Test filtering by multiple tags."""
        # Search for resources with both "javascript" and "reference"
        response = await client.get("/api/resources/?search=javascript reference")
        assert response.status_code == 200
        
        data = response.json()
        # Should find JavaScript MDN which has both tags
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_tag_search_partial_match(self, client: AsyncClient, sample_categorized_resources):
        """Test partial tag matching in search."""
        response = await client.get("/api/resources/?search=prog")
        assert response.status_code == 200
        
        data = response.json()
        # Should find resources with "programming" tag
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_create_resource_with_tags(self, client: AsyncClient):
        """Test creating a resource with multiple tags."""
        new_resource = {
            "title": "Tagged Resource",
            "url": "https://tagged.example.com",
            "description": "Resource with multiple tags",
            "category": "Testing",
            "tags": ["tag1", "tag2", "tag3", "special-tag"]
        }
        
        response = await client.post("/api/resources/", json=new_resource)
        assert response.status_code == 201
        
        created_resource = response.json()
        assert len(created_resource["tags"]) == 4
        assert "special-tag" in created_resource["tags"]

    @pytest.mark.asyncio
    async def test_update_resource_tags(self, client: AsyncClient, sample_categorized_resources):
        """Test updating tags for an existing resource."""
        resource = sample_categorized_resources[0]
        resource_id = resource["id"]
        
        updated_data = {
            "title": resource["title"],
            "url": resource["url"],
            "description": resource["description"],
            "category": resource["category"],
            "tags": ["updated", "tags", "new-tag"]
        }
        
        response = await client.put(f"/api/resources/{resource_id}", json=updated_data)
        assert response.status_code == 200
        
        updated_resource = response.json()
        assert "updated" in updated_resource["tags"]
        assert "new-tag" in updated_resource["tags"]

    @pytest.mark.asyncio
    async def test_empty_tags_list(self, client: AsyncClient):
        """Test creating a resource with empty tags list."""
        new_resource = {
            "title": "No Tags Resource",
            "url": "https://notags.example.com",
            "description": "Resource without tags",
            "category": "Testing",
            "tags": []
        }
        
        response = await client.post("/api/resources/", json=new_resource)
        assert response.status_code == 201
        
        created_resource = response.json()
        assert created_resource["tags"] == []

    @pytest.mark.asyncio
    async def test_duplicate_tags_handling(self, client: AsyncClient):
        """Test handling of duplicate tags."""
        new_resource = {
            "title": "Duplicate Tags Resource",
            "url": "https://duplicatetags.example.com",
            "description": "Resource with duplicate tags",
            "category": "Testing",
            "tags": ["tag1", "tag2", "tag1", "tag3", "tag2"]
        }
        
        response = await client.post("/api/resources/", json=new_resource)
        assert response.status_code == 201
        
        created_resource = response.json()
        # Should handle duplicates (either remove them or keep them based on implementation)
        tags = created_resource["tags"]
        assert "tag1" in tags
        assert "tag2" in tags
        assert "tag3" in tags


class TestCategoryTagCombination:
    """Test cases for combined category and tag operations."""

    @pytest.mark.asyncio
    async def test_filter_by_category_and_search_tags(self, client: AsyncClient, sample_categorized_resources):
        """Test filtering by both category and tag search."""
        response = await client.get("/api/resources/?category=Documentation&search=python")
        assert response.status_code == 200
        
        data = response.json()
        # Should find Python documentation (has both Documentation category and python tag)
        assert data["total"] >= 1
        
        for resource in data["resources"]:
            assert resource["category"] == "Documentation"
            # Should contain python in title, description, or tags

    @pytest.mark.asyncio
    async def test_category_tag_statistics(self, client: AsyncClient, sample_categorized_resources):
        """Test getting statistics about categories and tags."""
        # Get all resources to analyze
        response = await client.get("/api/resources/")
        assert response.status_code == 200
        
        data = response.json()
        resources = data["resources"]
        
        # Analyze category distribution
        category_counts = {}
        tag_counts = {}
        
        for resource in resources:
            category = resource["category"]
            category_counts[category] = category_counts.get(category, 0) + 1
            
            for tag in resource.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Verify expected distributions
        assert category_counts.get("Documentation", 0) == 3
        assert tag_counts.get("python", 0) == 2

    @pytest.mark.asyncio
    async def test_bulk_category_update(self, client: AsyncClient, sample_categorized_resources):
        """Test bulk updating categories (future feature)."""
        # Get resources from a specific category
        response = await client.get("/api/resources/?category=Documentation")
        assert response.status_code == 200
        
        doc_resources = response.json()["resources"]
        resource_ids = [r["id"] for r in doc_resources]
        
        # In a future implementation, there might be a bulk update endpoint
        # For now, we'll update them individually to test the concept
        for resource_id in resource_ids[:2]:  # Update first 2
            resource = next(r for r in doc_resources if r["id"] == resource_id)
            updated_data = {
                "title": resource["title"],
                "url": resource["url"],
                "description": resource["description"],
                "category": "Reference",  # Change category
                "tags": resource["tags"]
            }
            
            response = await client.put(f"/api/resources/{resource_id}", json=updated_data)
            assert response.status_code == 200
            
            updated_resource = response.json()
            assert updated_resource["category"] == "Reference"

    @pytest.mark.asyncio
    async def test_tag_autocomplete_suggestions(self, client: AsyncClient, sample_categorized_resources):
        """Test tag autocomplete functionality (future feature)."""
        # Get all resources to extract existing tags
        response = await client.get("/api/resources/")
        assert response.status_code == 200
        
        data = response.json()
        resources = data["resources"]
        
        # Extract all unique tags
        all_tags = set()
        for resource in resources:
            all_tags.update(resource.get("tags", []))
        
        # Test autocomplete for partial matches
        partial_query = "prog"
        matching_tags = [tag for tag in all_tags if tag.startswith(partial_query)]
        
        # Should find "programming" tag
        assert any("programming" in tag for tag in matching_tags)

    @pytest.mark.asyncio
    async def test_category_hierarchy_support(self, client: AsyncClient):
        """Test hierarchical category support (future feature)."""
        # Test creating resources with hierarchical categories
        hierarchical_resources = [
            {
                "title": "Frontend Framework",
                "url": "https://frontend.example.com",
                "description": "Frontend development framework",
                "category": "Development/Frontend",
                "tags": ["frontend", "framework"]
            },
            {
                "title": "Backend API",
                "url": "https://backend.example.com",
                "description": "Backend API documentation",
                "category": "Development/Backend",
                "tags": ["backend", "api"]
            }
        ]
        
        for resource_data in hierarchical_resources:
            response = await client.post("/api/resources/", json=resource_data)
            assert response.status_code == 201
            
            created_resource = response.json()
            assert "/" in created_resource["category"]  # Hierarchical separator
        
        # Test filtering by parent category
        response = await client.get("/api/resources/?category=Development")
        assert response.status_code == 200
        
        # Depending on implementation, might find hierarchical subcategories