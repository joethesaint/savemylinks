"""
Database migration to add tags column to resources table.

This migration adds the tags column to support the tagging system
for better resource organization and filtering.
"""

import asyncio
import logging
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Use SQLite database URL directly
DATABASE_URL = "sqlite+aiosqlite:///./savemylinks.db"


async def add_tags_column():
    """Add tags column to resources table."""
    
    # Create async engine
    engine = create_async_engine(DATABASE_URL)
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    try:
        async with async_session() as session:
            # Check if tags column already exists
            result = await session.execute(
                text("PRAGMA table_info(resources)")
            )
            columns = result.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'tags' not in column_names:
                # Add tags column
                await session.execute(
                    text("ALTER TABLE resources ADD COLUMN tags JSON DEFAULT '[]'")
                )
                await session.commit()
                logger.info("Successfully added tags column to resources table")
                print("Successfully added tags column to resources table")
            else:
                logger.info("Tags column already exists in resources table")
                print("Tags column already exists in resources table")
                
    except Exception as e:
        logger.error(f"Failed to add tags column: {str(e)}")
        print(f"Failed to add tags column: {str(e)}")
        raise
    finally:
        await engine.dispose()


async def main():
    """Run the migration."""
    await add_tags_column()


if __name__ == "__main__":
    asyncio.run(main())