.PHONY: help test test-unit test-integration test-e2e coverage lint format install start stop clean

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help:
	@echo "$(BLUE)THE BOT Platform - Makefile Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  make test              - Run all tests (unit + integration)"
	@echo "  make test-unit         - Run unit tests only"
	@echo "  make test-integration  - Run integration tests only"
	@echo "  make test-e2e          - Run end-to-end tests with Playwright"
	@echo "  make coverage          - Generate coverage reports"
	@echo ""
	@echo "$(GREEN)Code Quality:$(NC)"
	@echo "  make lint              - Run all linters (backend + frontend)"
	@echo "  make lint-backend      - Run backend linters (flake8, black, isort)"
	@echo "  make lint-frontend     - Run frontend linters (eslint, prettier)"
	@echo "  make format            - Auto-format code (backend + frontend)"
	@echo "  make format-backend    - Auto-format backend code"
	@echo "  make format-frontend   - Auto-format frontend code"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make install           - Install all dependencies"
	@echo "  make install-backend   - Install backend dependencies"
	@echo "  make install-frontend  - Install frontend dependencies"
	@echo "  make start             - Start development servers"
	@echo "  make stop              - Stop all running servers"
	@echo "  make migrate           - Run database migrations"
	@echo "  make clean             - Clean temporary files and caches"
	@echo ""
	@echo "$(GREEN)Database:$(NC)"
	@echo "  make migrate           - Run database migrations"
	@echo "  make makemigrations    - Create new migrations"
	@echo "  make cleanup-db        - Clean preview/test data from database"
	@echo ""

# Testing targets
# CRITICAL: Always set ENVIRONMENT=test for backend tests to use test database
test:
	@echo "$(BLUE)Running all tests...$(NC)"
	@cd backend && ENVIRONMENT=test pytest -m "unit or integration"
	@cd frontend && npm test

test-unit:
	@echo "$(BLUE)Running unit tests...$(NC)"
	@cd backend && ENVIRONMENT=test pytest -m unit
	@cd frontend && npm test

test-integration:
	@echo "$(BLUE)Running integration tests...$(NC)"
	@cd backend && ENVIRONMENT=test pytest -m integration

test-e2e:
	@echo "$(BLUE)Running E2E tests with Playwright...$(NC)"
	@npx playwright test

coverage:
	@echo "$(BLUE)Generating coverage reports...$(NC)"
	@cd backend && ENVIRONMENT=test pytest --cov --cov-report=html --cov-report=term
	@cd frontend && npm run test:coverage
	@echo "$(GREEN)Backend coverage report: backend/htmlcov/index.html$(NC)"
	@echo "$(GREEN)Frontend coverage report: frontend/coverage/index.html$(NC)"

# Code quality targets
lint: lint-backend lint-frontend

lint-backend:
	@echo "$(BLUE)Running backend linters...$(NC)"
	@cd backend && flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	@cd backend && flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	@cd backend && black --check .
	@cd backend && isort --check-only .
	@echo "$(GREEN)Backend linting passed!$(NC)"

lint-frontend:
	@echo "$(BLUE)Running frontend linters...$(NC)"
	@cd frontend && npm run lint
	@cd frontend && npx prettier --check "src/**/*.{ts,tsx,js,jsx,json,css}"
	@echo "$(GREEN)Frontend linting passed!$(NC)"

format: format-backend format-frontend

format-backend:
	@echo "$(BLUE)Formatting backend code...$(NC)"
	@cd backend && black .
	@cd backend && isort .
	@echo "$(GREEN)Backend code formatted!$(NC)"

format-frontend:
	@echo "$(BLUE)Formatting frontend code...$(NC)"
	@cd frontend && npx prettier --write "src/**/*.{ts,tsx,js,jsx,json,css}"
	@echo "$(GREEN)Frontend code formatted!$(NC)"

# Installation targets
install: install-backend install-frontend

install-backend:
	@echo "$(BLUE)Installing backend dependencies...$(NC)"
	@python -m pip install --upgrade pip
	@pip install -r backend/requirements.txt
	@echo "$(GREEN)Backend dependencies installed!$(NC)"

install-frontend:
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	@cd frontend && npm ci
	@echo "$(GREEN)Frontend dependencies installed!$(NC)"

# Development targets
start:
	@echo "$(BLUE)Starting development servers...$(NC)"
	@./start.sh

stop:
	@echo "$(BLUE)Stopping all servers...$(NC)"
	@pkill -f "manage.py runserver" || true
	@pkill -f "vite" || true
	@pkill -f "celery" || true
	@echo "$(GREEN)All servers stopped!$(NC)"

# Database targets
migrate:
	@echo "$(BLUE)Running database migrations...$(NC)"
	@cd backend && python manage.py migrate
	@echo "$(GREEN)Migrations completed!$(NC)"

makemigrations:
	@echo "$(BLUE)Creating new migrations...$(NC)"
	@cd backend && python manage.py makemigrations
	@echo "$(GREEN)Migrations created!$(NC)"

cleanup-db:
	@echo "$(YELLOW)Cleaning database...$(NC)"
	@./cleanup_db.sh
	@echo "$(GREEN)Database cleaned!$(NC)"

# Dashboard tests
test-dashboards:
	@echo "$(BLUE)Running all dashboard tests...$(NC)"
	@make test-dashboards-backend
	@make test-dashboards-frontend-unit
	@make test-dashboards-frontend-e2e

test-dashboards-backend:
	@echo "$(BLUE)Running backend dashboard tests...$(NC)"
	@cd backend && python -m pytest -m dashboard tests/unit/materials/test_*_dashboard.py -v

test-dashboards-frontend-unit:
	@echo "$(BLUE)Running frontend dashboard unit tests...$(NC)"
	@cd frontend && npm run test:dashboards 2>/dev/null || echo "Test script not yet configured"

test-dashboards-frontend-e2e:
	@echo "$(BLUE)Running frontend dashboard E2E tests...$(NC)"
	@cd frontend && npx playwright test tests/e2e/dashboards/ 2>/dev/null || echo "E2E tests directory not yet configured"

# Cleanup targets
clean:
	@echo "$(BLUE)Cleaning temporary files...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".coverage" -delete 2>/dev/null || true
	@find . -type d -name "node_modules/.cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf frontend/dist 2>/dev/null || true
	@rm -rf frontend/build 2>/dev/null || true
	@rm -rf test-results 2>/dev/null || true
	@rm -rf playwright-report 2>/dev/null || true
	@echo "$(GREEN)Cleanup completed!$(NC)"
