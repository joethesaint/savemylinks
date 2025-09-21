import asyncio
from app.database import get_db
from app.crud import resource_crud

async def test_crud():
    async for db in get_db():
        try:
            resources = await resource_crud.get_multi_with_filters(db, skip=0, limit=10)
            print(f'Found {len(resources)} resources')
            for r in resources:
                print(f'Resource: {r.id} - {r.title} - {r.url}')
        except Exception as e:
            print(f'Error: {e}')
            import traceback
            traceback.print_exc()
        break

if __name__ == "__main__":
    asyncio.run(test_crud())