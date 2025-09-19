# SaveMyLinks - Database Migration Rules

## Purpose
This document outlines the best practices for managing database schema changes to prevent data loss and ensure a consistent development and production environment.

## Core Principle: Use a Migration Tool
Directly modifying the database schema manually or by dropping and recreating tables is strongly discouraged as it leads to data loss and makes collaboration difficult.

We recommend using **Alembic**, the standard database migration tool for SQLAlchemy.

## Alembic Setup Guide

### 1. Installation
```bash
pip install alembic
```

### 2. Initialization
In the root of the project, run:
```bash
alembic init alembic
```
This will create an `alembic` directory and an `alembic.ini` file.

### 3. Configuration
In `alembic.ini`, find the `sqlalchemy.url` line and point it to your database URL. You can get this from your environment variables or `config.py`.

Example:
```ini
sqlalchemy.url = sqlite:///./savemylinks.db
```

In `alembic/env.py`, you need to make sure Alembic can see your SQLAlchemy models. Around line 20, import your models' `Base`:

```python
from app.models import Base
target_metadata = Base.metadata
```

## Alembic Usage Guide

### 1. Creating a Migration
Whenever you change your models in `app/models.py` (e.g., add a new column), you need to generate a migration script:

```bash
alembic revision --autogenerate -m "Add metadata column to resources"
```
This will create a new file in `alembic/versions/` containing the Python code to apply the schema change.

### 2. Applying a Migration
To apply the changes to your database, run:
```bash
alembic upgrade head
```
This will run all pending migration scripts.

### 3. Downgrading a Migration
To revert a migration, you can run:
```bash
alembic downgrade -1
```
This will revert the last applied migration.

## Workflow
1.  Change your models in `app/models.py`.
2.  Run `alembic revision --autogenerate -m "Your descriptive message"`.
3.  Review the generated migration script in `alembic/versions/`.
4.  Run `alembic upgrade head` to apply the changes to your database.
5.  Commit the migration script along with your model changes.
