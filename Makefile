.PHONY: dev-db dev-db-stop migrate backend frontend test lint format install

# Start PostgreSQL in Docker
dev-db:
	docker compose up db -d

# Stop PostgreSQL
dev-db-stop:
	docker compose down

# Run Alembic migrations
migrate:
	cd backend && uv run alembic upgrade head

# Start FastAPI backend (with hot reload)
backend:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Vite frontend dev server
frontend:
	cd frontend && npm run dev

# Run backend tests
test:
	cd backend && uv run pytest

# Run backend tests with coverage
test-cov:
	cd backend && uv run pytest --cov=app --cov-report=term-missing

# Lint backend
lint:
	cd backend && uv run ruff check .

# Format backend
format:
	cd backend && uv run ruff format .

# Install all dependencies
install:
	cd backend && uv sync
	cd frontend && npm install
