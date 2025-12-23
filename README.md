# Multi-Tenant License Management Service

A multi-tenant, centralized license management service for group.one brands (WP Rocket, RankMath, Imagify, etc.).

## Features

- **Multi-tenant architecture** - Support for multiple brands with isolated API credentials
- **License key management** - Generate and manage license keys per customer
- **Product licensing** - Associate multiple product licenses with a single license key
- **Seat management** - Track and enforce activation limits per license
- **License lifecycle** - Support for valid, suspended, cancelled, and expired states
- **Cross-brand lookup** - Query customer licenses across all brands

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (optional, SQLite works for development)
- Docker & Docker Compose (optional)

### Option 1: Docker (Recommended)

```bash
# Start the service with PostgreSQL
docker-compose up -d

# The API will be available at http://localhost:8000
Admin dashboard: http://localhost:8000/admin/

# Create the superuser inside the container to access admin dashboard (follow the promts to set username, email and password)
docker-compose exec web python manage.py createsuperuser
```

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create a superuser (optional, for admin access)
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

## API Documentation

Once running, access the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/api/docs/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## API Overview

### Brand API (`/api/v1/brand/`)

For brand systems to manage licenses. Requires API key authentication.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/license-keys/` | GET | List all license keys |
| `/license-keys/` | POST | Create a new license key |
| `/license-keys/{key}/` | GET | Get license key details |
| `/license-keys/{key}/licenses/` | POST | Add a license to a key |
| `/licenses/{id}/renew/` | POST | Renew a license |
| `/licenses/{id}/suspend/` | POST | Suspend a license |
| `/licenses/{id}/resume/` | POST | Resume a suspended license |
| `/licenses/{id}/cancel/` | POST | Cancel a license |
| `/customers/?email=` | GET | List licenses by customer email |
| `/products/` | GET | List brand products |

**Authentication**: Include headers `X-API-Key` and `X-API-Secret`

### Product API (`/api/v1/product/`)

For end-user products to activate and validate licenses. No authentication required.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/activate/` | POST | Activate a license for an instance |
| `/validate/` | POST | Validate a license key |
| `/deactivate/` | POST | Deactivate a license |
| `/status/` | GET | Get full license status |

## Sample API Calls

### Create a License Key (Brand API)

```bash
curl -X POST http://localhost:8000/api/v1/brand/license-keys/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -H "X-API-Secret: your-api-secret" \
  -d '{
    "customer_email": "user@example.com",
    "customer_name": "John Doe"
  }'
```

### Add a License to a Key (Brand API)

```bash
curl -X POST http://localhost:8000/api/v1/brand/license-keys/{key}/licenses/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -H "X-API-Secret: your-api-secret" \
  -d '{
    "product_id": "uuid-of-product",
    "seat_limit": 3
  }'
```

### Activate a License (Product API)

```bash
curl -X POST http://localhost:8000/api/v1/product/activate/ \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "the-license-key",
    "product_slug": "pro-plan",
    "instance_id": "https://mysite.com",
    "instance_name": "My Website"
  }'
```

### Validate a License (Product API)

```bash
curl -X POST http://localhost:8000/api/v1/product/validate/ \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "the-license-key",
    "product_slug": "pro-plan"
  }'
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps --cov-report=html

# Run specific test file
pytest tests/test_brand_api.py -v
```

## Code Quality

```bash
# Format code
black .

# Check linting
flake8

# Sort imports
isort .
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_ENV` | Environment (development/production) | development |
| `DJANGO_SECRET_KEY` | Django secret key | dev-key |
| `DATABASE_URL` | Database connection URL | SQLite |
| `POSTGRES_DB` | PostgreSQL database name | license_service |
| `POSTGRES_USER` | PostgreSQL user | postgres |
| `POSTGRES_PASSWORD` | PostgreSQL password | postgres |
| `POSTGRES_HOST` | PostgreSQL host | localhost |
| `POSTGRES_PORT` | PostgreSQL port | 5432 |

## Project Structure

```
license-server/
├── config/                 # Django project configuration
│   ├── settings/          # Environment-specific settings
│   │   ├── base.py       # Base settings
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── brands/            # Brand and Product models
│   ├── licenses/          # License, LicenseKey, Activation models
│   └── api/               # REST API
│       ├── v1/
│       │   ├── brand/    # Brand API endpoints
│       │   └── product/  # Product API endpoints
│       ├── authentication.py
│       ├── exceptions.py
│       └── middleware.py
├── tests/                  # Test suite
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── Explanation.md          # Architecture documentation
```

## License

MIT