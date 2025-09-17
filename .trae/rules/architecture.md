Purpose: Defines the high-level structure, patterns, and technology decisions for the project.

# SaveMyLinks - Architecture Rules

## Tech Stack
- **Backend:** FastAPI
- **Database:** SQLite (development), PostgreSQL (production-ready)
- **ORM:** SQLAlchemy 2.0 with async support
- **Templating:** Jinja2
- **CSS Framework:** Bulma
- **Hosting:** Railway (preferred) or Render

## Project Structure
Adhere to a modular structure. Generate code that fits this layout:
app/
├── init.py
├── main.py # FastAPI app initialization and middleware
├── database.py # SQLAlchemy setup and session factory
├── models.py # SQLAlchemy ORM models (e.g., Resource)
├── schemas.py # Pydantic models for request/response validation
├── crud.py # Database operations (Create, Read, Update, Delete)
├── routes/ # API endpoint routers
│ └── resources.py # Routes for /api/resources/
├── templates/ # Jinja2 HTML templates
│ ├── base.html # Base template with Bulma CSS
│ ├── index.html # List all resources
│ └── add.html # Form to add a new resource
└── tests/ # Pytest test suite
├── init.py
├── conftest.py # Pytest fixtures (e.g., test client, DB session)
└── test_routes.py # Tests for API routes


## Architectural Patterns
- Use dependency injection for database sessions (`Depends` in FastAPI).
- Separate concerns: routes handle HTTP logic, crud modules handle database logic.
- All API routes must be asynchronous (`async def`).
- Use Pydantic schemas for all data validation on input (request bodies) and output (response models). Do not use ORM models directly in endpoints.