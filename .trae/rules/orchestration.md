# SaveMyLinks - Feature Orchestration

## Purpose
Guides the AI on how to break down feature implementation and how to use documentation.

## Implementation Workflow
When asked to implement a feature, follow this sequence:

1. **Database Layer**: First, update the SQLAlchemy model in models.py if needed.

2. **Pydantic Schemas**: Second, create or update the necessary Pydantic schemas in schemas.py (e.g., ResourceCreate, ResourceUpdate, Resource).

3. **CRUD Operations**: Third, implement the corresponding functions in crud.py.

4. **API Routes**: Fourth, add the endpoints to the appropriate router in routes/.

5. **Frontend (Jinja2)**: Fifth, update or create the necessary Jinja2 templates.

6. **Testing**: Finally, generate the corresponding tests in tests/.

## Prompting Context
I will often provide context by pasting code or schema definitions. Use this context to generate precise, relevant code.

When generating code, always assume the existence of the standard project structure (e.g., from app.database import get_db).

If you are unsure about a implementation detail, generate a concise, well-commented implementation and ask for confirmation or clarification.

## Documentation Generation
For complex functions or classes, generate Google-style or NumPy-style docstrings.

For HTTP endpoints, generate docstrings that describe the endpoint's purpose, parameters, and possible responses. FastAPI will use this for automatic API docs.

### Example endpoint docstring:
```python
@router.post("/", response_model=schemas.Resource, status_code=201)
async def create_resource(
    resource: schemas.ResourceCreate, db: AsyncSession = Depends(get_db)
):
    """
    Create a new resource entry in the database.

    Args:
        resource (schemas.ResourceCreate): The resource data to create.
        db (AsyncSession): The database session dependency.

    Returns:
        models.Resource: The newly created resource.

    Raises:
        HTTPException: 400 if the URL is invalid or a resource with the same URL exists.
    """
    # ... code ...
```