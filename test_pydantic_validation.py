import asyncio
from sqlalchemy import select
from app.database import get_db
from app.models import Resource
from app.schemas import Resource as ResourceSchema

async def test_pydantic_validation():
    async for db in get_db():
        try:
            # Get raw database objects
            result = await db.execute(select(Resource))
            resources = result.scalars().all()
            print(f'Found {len(resources)} resources in database')
            
            # Try to validate each resource with Pydantic
            validated_resources = []
            for resource in resources:
                try:
                    validated = ResourceSchema.model_validate(resource)
                    validated_resources.append(validated)
                    print(f'Successfully validated resource {resource.id}: {resource.title}')
                except Exception as e:
                    print(f'Validation error for resource {resource.id}: {e}')
                    print(f'  Resource data: {resource.__dict__}')
                    import traceback
                    traceback.print_exc()
                    
            print(f'Successfully validated {len(validated_resources)} out of {len(resources)} resources')
                
        except Exception as e:
            print(f'Database query error: {e}')
            import traceback
            traceback.print_exc()
        break

if __name__ == "__main__":
    asyncio.run(test_pydantic_validation())