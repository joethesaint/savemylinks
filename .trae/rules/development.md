Purpose: Specifies coding standards, conventions, and practices for all generated code.

# SaveMyLinks - Development Standards

## Python Code Style
- **Formatter:** Black. Generate code that is Black-compliant.
- **Linter:** Ruff. Avoid generating code that will trigger common linting errors (e.g., unused imports, long lines).
- **Imports:** Use absolute imports. Group standard library, third-party, and local imports.
- **Naming:** Use `snake_case` for variables and functions, `PascalCase` for classes, `UPPER_CASE` for constants.
- **Types:** Use Python type hints religiously for all function parameters and return values.

## FastAPI Specifics
- Use `HTTPException` with appropriate status codes for errors.
- Prefix all API routes with `/api/`.
- Use descriptive `response_model` and `status_code` parameters in route decorators.
- For database operations, use asynchronous sessions: `await db.execute()`, `result = await db.scalars()`.

## SQLAlchemy Specifics
- Use SQLAlchemy 2.0 style declarative base and query syntax.
- Define models with `Mapped` and `mapped_column`.
- Example:

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Resource(Base):
    __tablename__ = "resources"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    # ... other fields ...

```

## Testing
Use pytest and httpx.AsyncClient for testing.

All tests must be async.

Tests should be isolated; use a separate test database or rollback transactions after each test.

Follow the Arrange-Act-Assert pattern.

Generate tests that cover both success and failure cases (e.g., 200 OK, 404 Not Found, 422 Validation Error).

Also, ensure that tests are idempotent and do not depend on the order of execution.
We are to follow TDD approach as it helps with setting up the build