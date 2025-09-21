import asyncio
from sqlalchemy import select
from app.database import get_db
from app.models import Resource

async def test_db_query():
    async for db in get_db():
        try:
            # Test raw database query
            result = await db.execute(select(Resource))
            resources = result.scalars().all()
            print(f'Found {len(resources)} resources in database')
            
            for resource in resources:
                print(f'Raw resource: {resource.id} - {resource.title} - {resource.url}')
                print(f'  Tags: {resource.tags}')
                print(f'  Link metadata: {resource.link_metadata}')
                print(f'  Created at: {resource.created_at}')
                print(f'  Updated at: {resource.updated_at}')
                print('---')
                
        except Exception as e:
            print(f'Database query error: {e}')
            import traceback
            traceback.print_exc()
        break

if __name__ == "__main__":
    asyncio.run(test_db_query())