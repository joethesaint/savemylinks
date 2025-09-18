"""
Database configuration and session management for SaveMyLinks.

This module sets up SQLAlchemy 2.0 with async support for database operations.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os

# Database URL - SQLite for development, PostgreSQL for production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./savemylinks.db")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    future=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.
    
    Yields:
        AsyncSession: Database session for dependency injection.
    """
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    """
    Create all database tables declared on the ORM `Base`.
    
    This asynchronous function opens a connection to the configured async engine and creates any missing tables for all models registered on `Base.metadata`. It should be awaited (e.g., during startup or migrations). Changes are executed within a database transaction against the configured DATABASE_URL.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all database tables (for testing)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)