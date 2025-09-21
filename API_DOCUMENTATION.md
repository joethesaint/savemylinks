# SaveMyLinks API Documentation

## Overview

SaveMyLinks is a comprehensive link management API that allows you to save, organize, and manage your favorite links with automatic metadata extraction. The API provides full CRUD operations, search functionality, categorization, and bulk operations.

## Base URL

```
http://localhost:8000
```

## Interactive Documentation

- **Swagger UI**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **ReDoc**: [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc)
- **OpenAPI JSON**: [http://localhost:8000/api/openapi.json](http://localhost:8000/api/openapi.json)

## Authentication

Currently, the API operates without authentication. In production environments, consider implementing proper authentication and authorization mechanisms.

## Rate Limiting

No rate limiting is currently implemented. For production use, consider adding rate limiting to prevent abuse.

## Error Handling

The API uses standard HTTP status codes and returns structured error responses:

```json
{
  "detail": "Error message description"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `404` - Not Found
- `409` - Conflict (e.g., duplicate URL)
- `422` - Validation Error
- `500` - Internal Server Error

## API Endpoints

### Resources

#### Create Resource
- **POST** `/api/resources/`
- **Description**: Create a new link resource with optional automatic metadata extraction
- **Request Body**: ResourceCreate schema
- **Response**: Resource schema
- **Status Codes**: 201, 409, 422, 500

#### Get Resources (Paginated)
- **GET** `/api/resources/`
- **Description**: Retrieve paginated list of resources with optional filtering
- **Query Parameters**:
  - `page` (int): Page number (default: 1)
  - `per_page` (int): Resources per page (1-100, default: 20)
  - `category` (string): Filter by category
  - `search` (string): Search in title and description
- **Response**: ResourceList schema
- **Status Codes**: 200, 500

#### Get Resource by ID
- **GET** `/api/resources/{resource_id}`
- **Description**: Retrieve a specific resource by its unique identifier
- **Path Parameters**: `resource_id` (int)
- **Response**: Resource schema
- **Status Codes**: 200, 404, 500

#### Update Resource
- **PUT** `/api/resources/{resource_id}`
- **Description**: Update an existing resource with optional metadata refresh
- **Path Parameters**: `resource_id` (int)
- **Query Parameters**: `refresh_metadata` (bool): Whether to refresh metadata if URL changed
- **Request Body**: ResourceUpdate schema
- **Response**: Resource schema
- **Status Codes**: 200, 404, 409, 422, 500

#### Delete Resource
- **DELETE** `/api/resources/{resource_id}`
- **Description**: Permanently delete a resource
- **Path Parameters**: `resource_id` (int)
- **Response**: MessageResponse schema
- **Status Codes**: 200, 404, 500

### Metadata Operations

#### Refresh Resource Metadata
- **POST** `/api/resources/{resource_id}/refresh-metadata`
- **Description**: Manually refresh link preview metadata for a resource
- **Path Parameters**: `resource_id` (int)
- **Response**: Resource schema
- **Status Codes**: 200, 404, 500

#### Get Resource Metadata
- **GET** `/api/resources/{resource_id}/metadata`
- **Description**: Retrieve link preview metadata for a specific resource
- **Path Parameters**: `resource_id` (int)
- **Response**: LinkPreviewMetadata schema or null
- **Status Codes**: 200, 404, 500

### Categories and Tags

#### Get All Categories
- **GET** `/api/resources/categories`
- **Description**: Retrieve all unique categories used across resources
- **Response**: Array of strings
- **Status Codes**: 200, 500

#### Get All Tags
- **GET** `/api/resources/tags`
- **Description**: Retrieve all unique tags used across resources
- **Response**: Array of strings
- **Status Codes**: 200, 500

### Export Operations

#### Export Resources
- **GET** `/api/resources/export`
- **Description**: Export resources in JSON or CSV format
- **Query Parameters**:
  - `format` (string): Export format ("json" or "csv", default: "json")
  - `category` (string): Filter by category
  - `search` (string): Search filter
- **Response**: File download (JSON or CSV)
- **Status Codes**: 200, 500

### Health Check

#### Health Status
- **GET** `/health`
- **Description**: Check API health status
- **Response**: Health status object
- **Status Codes**: 200

## Data Schemas

### Resource
```json
{
  "id": 1,
  "url": "https://example.com",
  "title": "Example Site",
  "description": "An example website",
  "category": "Technology",
  "tags": ["web", "example"],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "link_metadata": {
    "title": "Example Site",
    "description": "An example website",
    "image": "https://example.com/image.jpg",
    "status": "success"
  }
}
```

### ResourceCreate
```json
{
  "url": "https://example.com",
  "title": "Example Site",
  "description": "An example website",
  "category": "Technology",
  "tags": ["web", "example"]
}
```

### ResourceUpdate
```json
{
  "url": "https://example.com",
  "title": "Updated Title",
  "description": "Updated description",
  "category": "Updated Category",
  "tags": ["updated", "tags"]
}
```

### ResourceList
```json
{
  "items": [/* Array of Resource objects */],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}
```

### LinkPreviewMetadata
```json
{
  "title": "Page Title",
  "description": "Page description",
  "image": "https://example.com/image.jpg",
  "status": "success"
}
```

### MessageResponse
```json
{
  "message": "Operation completed successfully"
}
```

### ErrorResponse
```json
{
  "detail": "Error message description"
}
```

## Features

### Automatic Metadata Extraction
When creating resources, the API can automatically extract metadata (title, description, image) from the provided URL. This feature can be controlled using the `extract_metadata` query parameter.

### Search and Filtering
Resources can be filtered by:
- **Category**: Exact match filtering
- **Search**: Full-text search in title and description fields
- **Pagination**: Efficient pagination with configurable page sizes

### Background Processing
Metadata extraction and refresh operations are processed in the background to ensure fast API response times.

### Bulk Operations
- Export all resources in JSON or CSV format
- Bulk delete operations (via separate endpoints)

### Data Validation
All input data is validated using Pydantic schemas to ensure data integrity and provide clear error messages.

## Usage Examples

### Create a Resource
```bash
curl -X POST "http://localhost:8000/api/resources/" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com",
    "title": "GitHub",
    "category": "Development",
    "tags": ["git", "code", "repository"]
  }'
```

### Get Resources with Filtering
```bash
curl "http://localhost:8000/api/resources/?category=Development&search=git&page=1&per_page=10"
```

### Update a Resource
```bash
curl -X PUT "http://localhost:8000/api/resources/1" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "GitHub - Updated",
    "description": "The world's leading software development platform"
  }'
```

### Export Resources
```bash
curl "http://localhost:8000/api/resources/export?format=csv" -o resources.csv
```

## Development

### Running the API
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
The API includes comprehensive test coverage. Run tests with:
```bash
pytest
```

### Database Migrations
Database schema changes are managed through migration scripts in the `migrations/` directory.

## Support

For issues, questions, or contributions, please refer to the project repository or contact the development team.