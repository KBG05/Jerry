# BlankPoint Backend

FastAPI backend with async SQLAlchemy, PostgreSQL, UV package management, request logging, and rate limiting.

## 🚀 Features

- **FastAPI**: Modern, fast web framework for building APIs
- **Async SQLAlchemy**: Asynchronous database operations with PostgreSQL
- **UV Package Manager**: Fast Python package installer and resolver
- **Request Logging**: Comprehensive logging with structured JSON/text formats
- **Rate Limiting**: SlowAPI-based rate limiting to prevent abuse
- **CORS Support**: Configurable CORS middleware
- **Alembic Migrations**: Database schema version control
- **Docker Support**: Multi-stage Dockerfile with Docker Compose
- **Health Checks**: Built-in health check endpoints
- **API Documentation**: Auto-generated OpenAPI (Swagger) docs

## 📋 Prerequisites

- Python 3.12+
- UV package manager
- Docker and Docker Compose (for containerized deployment)
- PostgreSQL 16 (if running locally without Docker)

## 🛠️ Installation

### Using UV (Recommended)

1. **Install UV** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**:
   ```bash
   cd backend
   uv pip install -e .
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

5. **Start the development server**:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

### Using Docker Compose (Production)

1. **Copy environment file**:
   ```bash
   cp .env.example .env
   # Edit .env as needed
   ```

2. **Start all services**:
   ```bash
   docker-compose up -d
   ```

3. **Run migrations** (inside container):
   ```bash
   docker-compose exec fastapi alembic upgrade head
   ```

### Using Docker Compose (Development)

For development with hot-reload:

```bash
docker-compose -f docker-compose.dev.yml up
```

## 🔧 Configuration

All configuration is done via environment variables. See `.env.example` for available options:

### Database
- `DATABASE_URL`: PostgreSQL connection URL with asyncpg driver
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: Database credentials

### API Settings
- `API_HOST`: Host to bind (default: 0.0.0.0)
- `API_PORT`: Port to listen on (default: 8000)
- `API_TITLE`, `API_VERSION`: API metadata

### CORS
- `CORS_ORIGINS`: Comma-separated allowed origins or `*` for all

### Rate Limiting
- `RATE_LIMIT_PER_MINUTE`: Format: "count/period" (e.g., "100/minute")

### Logging
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `LOG_FORMAT`: `json` or `text`

### Uvicorn
- `WORKERS_COUNT`: Number of worker processes
- `RELOAD`: Enable auto-reload for development

## 📚 API Documentation

Once running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🗄️ Database Migrations

### Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations:
```bash
alembic upgrade head
```

### Rollback migration:
```bash
alembic downgrade -1
```

### View migration history:
```bash
alembic history
```

## 🧪 Example API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Create User
```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe"
  }'
```

### Get Users (with pagination)
```bash
curl http://localhost:8000/api/v1/users?page=1&page_size=10
```

### Get User by ID
```bash
curl http://localhost:8000/api/v1/users/1
```

### Update User
```bash
curl -X PATCH http://localhost:8000/api/v1/users/1 \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Jane Doe"}'
```

### Delete User
```bash
curl -X DELETE http://localhost:8000/api/v1/users/1
```

## 📁 Project Structure

```
backend/
├── alembic/                    # Database migrations
│   ├── versions/               # Migration files
│   └── env.py                  # Alembic configuration
├── app/
│   ├── api/                    # API routes
│   │   └── v1/                 # API version 1
│   │       └── users.py        # User endpoints
│   ├── core/                   # Core configurations
│   │   ├── config.py           # Settings management
│   │   └── logging_config.py  # Logging setup
│   ├── db/                     # Database setup
│   │   ├── base.py             # SQLAlchemy Base
│   │   └── database.py         # Async engine & sessions
│   ├── middleware/             # Custom middleware
│   │   ├── logging.py          # Request logging
│   │   └── rate_limit.py       # Rate limiting
│   ├── models/                 # SQLAlchemy models
│   │   └── user.py             # User model
│   ├── schemas/                # Pydantic schemas
│   │   └── user.py             # User schemas
│   └── main.py                 # FastAPI application
├── alembic.ini                 # Alembic configuration
├── pyproject.toml              # Project dependencies (UV)
├── Dockerfile                  # Multi-stage Docker build
├── .env.example                # Environment variables template
└── README.md                   # This file
```

## 🔐 Security Features

- **Rate Limiting**: Prevents abuse with configurable limits per endpoint
- **Request Logging**: All requests are logged with unique IDs for tracing
- **Non-root Docker User**: Container runs as non-privileged user
- **Health Checks**: Docker health checks for service monitoring
- **CORS Protection**: Configurable CORS policies

## 🚀 Performance Features

- **Async Database Operations**: Full async/await support with asyncpg
- **Connection Pooling**: SQLAlchemy async connection pool
- **Request Middleware**: Efficient request processing pipeline
- **UV Package Manager**: Fast dependency resolution and installation

## 🐛 Development

### Running Tests
```bash
pytest
```

### Code Formatting (Ruff)
```bash
ruff check .
ruff format .
```

### Type Checking
```bash
mypy app/
```

## 📝 License

This project is part of the BlankPoint application.

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Add tests if applicable
4. Submit a pull request

## 📞 Support

For issues and questions, please refer to the main BlankPoint repository.
