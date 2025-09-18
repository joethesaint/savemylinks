"""
Tests for database module.

This module tests the database connection and session management.
Following the development rule: Use pytest for all testing with proper async support.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db, engine, AsyncSessionLocal


class TestDatabase:
    """Test cases for database functionality."""

    @pytest.mark.asyncio
    async def test_session_transaction(self):
        """Test session transaction handling."""
        async with AsyncSessionLocal() as session:
            # Start a transaction
            async with session.begin():
                # Test that we can execute queries within transaction
                result = await session.execute("SELECT 1")
                assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_get_db_dependency(self):
        """Test the get_db dependency function."""
        async for session in get_db():
            assert isinstance(session, AsyncSession)
            assert session.is_active
            break  # Only test the first yielded session

    def test_base_metadata(self):
        """Test that Base has metadata."""
        assert hasattr(Base, 'metadata')
        assert Base.metadata is not None

    @pytest.mark.asyncio
    async def test_engine_connection(self):
        """Test that engine can establish connection."""
        from sqlalchemy import text
        async with engine.begin() as conn:
            # Test basic connection
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_session_transaction(self):
        """Test session transaction handling."""
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            # Start a transaction
            async with session.begin():
                # Test that we can execute queries within transaction
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_session_rollback(self):
        """Test session rollback functionality."""
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            try:
                async with session.begin():
                    # This should work
                    await session.execute(text("SELECT 1"))
                    # Force an error to test rollback
                    raise Exception("Test rollback")
            except Exception as e:
                assert str(e) == "Test rollback"
                # Session should still be usable after rollback
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_multiple_sessions(self):
        """Test that multiple sessions can be created."""
        sessions = []
        
        # Create multiple sessions
        for _ in range(3):
            async with AsyncSessionLocal() as session:
                sessions.append(session)
                assert isinstance(session, AsyncSession)
        
        # All sessions should be different instances
        assert len(set(id(s) for s in sessions)) == 3

    def test_engine_configuration(self):
        """Test engine configuration."""
        assert engine is not None
        assert hasattr(engine, 'url')
        # Engine should be configured for async operations
        assert 'aiosqlite' in str(engine.url) or 'asyncpg' in str(engine.url)


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @pytest.mark.asyncio
    async def test_create_tables(self):
        """Test creating database tables."""
        from sqlalchemy import text
        # Create a test engine with in-memory database
        test_engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )
        
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
            # Check that tables were created
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result.fetchall()]
            assert 'resources' in tables

        await test_engine.dispose()

    @pytest.mark.asyncio
    async def test_session_with_model_operations(self):
        """Test session operations with actual models."""
        from app.models import Resource
        
        # Create a test engine with in-memory database
        test_engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )
        
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session
        async_session_maker = sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session_maker() as session:
            # Create a resource
            resource = Resource(
                title="Test Resource",
                url="https://test.com",
                description="Test description",
                category="Test"
            )
            
            session.add(resource)
            await session.commit()
            await session.refresh(resource)
            
            # Verify resource was created
            assert resource.id is not None
            assert resource.title == "Test Resource"

        await test_engine.dispose()