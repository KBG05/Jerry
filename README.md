# BlankPoint Application

A full-stack application with Go (Gin) backend and containerized architecture.

## 🏗️ Architecture

- **Backend**: Go with Gin framework, sqlc for type-safe SQL, PostgreSQL database
- **Frontend**: Static HTML/CSS/JS served by Nginx (easily replaceable with React/Vue/etc.)
- **Infrastructure**: Docker containers orchestrated with Docker Compose

## 📁 Project Structure

```
BlankPoint/
├── backend/                    # Go backend application
│   ├── cmd/
│   │   └── api/               # Application entry point
│   │       └── main.go
│   ├── internal/              # Private application code
│   │   ├── api/               # API handlers (Gin routes)
│   │   ├── db/                # sqlc generated code
│   │   ├── models/            # Business models
│   │   └── middleware/        # Middleware components
│   ├── sql/                   # Database files
│   │   ├── schema/            # Database schema
│   │   ├── queries/           # SQL queries for sqlc
│   │   └── migrations/        # Migration files
│   ├── go.mod                 # Go dependencies
│   ├── sqlc.yaml              # sqlc configuration
│   ├── Dockerfile             # Backend container
│   └── .env.example           # Environment variables template
├── frontend/                   # Frontend application
│   ├── public/                # Static files
│   │   ├── index.html
│   │   ├── css/
│   │   └── js/
│   ├── nginx.conf             # Nginx configuration
│   └── Dockerfile             # Frontend container
├── docker-compose.yml          # Production orchestration
├── docker-compose.dev.yml      # Development orchestration
├── Makefile                    # Build automation
├── .gitignore
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Go 1.22+ (for local development)
- Make (optional, for convenience commands)

### Using Docker (Recommended)

1. **Start the application in development mode:**
   ```bash
   make dev
   # or
   docker-compose -f docker-compose.dev.yml up
   ```

2. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8080
   - Health check: http://localhost:8080/health
   - Database: localhost:5432

3. **Stop the application:**
   ```bash
   make dev-down
   # or
   docker-compose -f docker-compose.dev.yml down
   ```

### Local Development

1. **Start the database:**
   ```bash
   make db-up
   ```

2. **Setup backend dependencies:**
   ```bash
   cd backend
   go mod download
   ```

3. **Generate sqlc code:**
   ```bash
   make sqlc
   # or
   cd backend && sqlc generate
   ```

4. **Run the backend:**
   ```bash
   make backend-run
   # or
   cd backend && go run cmd/api/main.go
   ```

5. **Serve the frontend:**
   Open `frontend/public/index.html` in a browser or use a local server.

## 🛠️ Development

### Available Make Commands

```bash
make help              # Show all available commands
make dev               # Run in development mode with hot reload
make docker-up         # Start all containers (production mode)
make docker-down       # Stop all containers
make sqlc              # Generate Go code from SQL queries
make backend-build     # Build backend binary
make backend-test      # Run tests
make clean             # Clean build artifacts
make setup             # Full project setup
```

### Working with sqlc

1. **Define your SQL schema** in `backend/sql/schema/`
2. **Write SQL queries** in `backend/sql/queries/`
3. **Generate Go code:**
   ```bash
   make sqlc
   ```

The generated code will be in `backend/internal/db/`

### Database Migrations

The project includes sample migrations in `backend/sql/migrations/`. To use them:

1. **Install golang-migrate:**
   ```bash
   go install -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate@latest
   ```

2. **Run migrations:**
   ```bash
   migrate -path ./backend/sql/migrations \
           -database "postgres://postgres:postgres@localhost:5432/blankpoint?sslmode=disable" \
           up
   ```

## 🔧 Configuration

### Environment Variables

Copy `backend/.env.example` to `backend/.env` and adjust as needed:

```env
DATABASE_URL=postgres://postgres:postgres@db:5432/blankpoint?sslmode=disable
PORT=8080
```

### sqlc Configuration

The `backend/sqlc.yaml` file is configured to:
- Use PostgreSQL with pgx/v5
- Generate code with Google UUID support
- Emit JSON tags for easy API responses
- Create interfaces for better testing

## 🐳 Docker

### Production Build

```bash
make docker-build
make docker-up
```

### Development with Hot Reload

```bash
make dev
```

This mounts your local code into the containers for live reloading.

## 📊 Database Schema

The default schema includes a `users` table with:
- UUID primary keys
- Email and username with unique constraints
- Password hash storage
- Timestamps for created/updated times

Example queries are provided for CRUD operations.

## 🌐 API Endpoints

- `GET /health` - Health check
- `GET /api/v1/ping` - Ping endpoint

Add your own routes in `backend/cmd/api/main.go` or create handlers in `backend/internal/api/`.

## 🎨 Frontend

The current frontend is a simple static site with Nginx. To use a modern framework:

1. Replace the `frontend/` directory with your framework's build output
2. Update `frontend/Dockerfile` to match your build process
3. Adjust `frontend/nginx.conf` if needed

Example for React:
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
```

## 🧪 Testing

```bash
make test
# or
cd backend && go test -v ./...
```

## 📝 Next Steps

1. **Add authentication**: Implement JWT or session-based auth
2. **Expand the API**: Add more endpoints and business logic
3. **Choose a frontend framework**: Replace static files with React, Vue, etc.
4. **Add middleware**: Logging, CORS, rate limiting
5. **Set up CI/CD**: GitHub Actions, GitLab CI, etc.
6. **Production deployment**: Configure for your hosting platform

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## 📄 License

[Your chosen license]

## 🆘 Troubleshooting

### Database connection failed
- Ensure PostgreSQL container is running: `docker-compose ps`
- Check DATABASE_URL environment variable
- Verify port 5432 is not in use

### Frontend can't reach backend
- Check that backend is running on port 8080
- Verify nginx.conf proxy settings
- Ensure containers are on the same network

### sqlc generation fails
- Install sqlc: `make install-sqlc`
- Check sqlc.yaml syntax
- Verify SQL files are valid PostgreSQL

---

Built with ❤️ using Go, Gin, sqlc, and Docker
