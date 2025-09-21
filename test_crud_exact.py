import asyncio
from app.database import get_db
from app.crud import resource_crud
from app.schemas import ResourceList

async def test_crud_exact():
    async for db in get_db():
        try:
            # Mimic exactly what the route handler does
            page = 1
            per_page = 10
            skip = (page - 1) * per_page
            
            print(f"Getting resources with skip={skip}, limit={per_page}")
            
            # Get resources
            resources = await resource_crud.get_multi_with_filters(
                db, skip=skip, limit=per_page
            )
            print(f"Got {len(resources)} resources from CRUD")
            
            # Get count
            total = await resource_crud.count_with_filters(db)
            print(f"Total count: {total}")
            
            # Try to create ResourceList
            resource_list = ResourceList(
                resources=resources,
                total=total,
                page=page,
                per_page=per_page
            )
            print(f"Successfully created ResourceList with {len(resource_list.resources)} resources")
            
        except Exception as e:
            print(f'Error in CRUD operation: {e}')
            import traceback
            traceback.print_exc()
        break

if __name__ == "__main__":
    asyncio.run(test_crud_exact())