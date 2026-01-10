# Makefile for DepegAlert Bot Development
# Provides convenient commands for development tasks

.PHONY: help install install-dev format lint test clean docker-dev docker-prod security check all

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON = python3
PIP = pip3
COMPOSE = docker-compose
COMPOSE_DEV = docker-compose -f docker-compose.dev.yml

help: ## Show this help message
	@echo "DepegAlert Bot Development Commands"
	@echo "=================================="
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Installation targets
install: ## Install production dependencies
	$(PIP) install -r requirements.txt

install-dev: ## Install development dependencies
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

# Code quality targets
format: ## Format code with Black and isort
	@echo "🎨 Formatting code..."
	black .
	isort .
	@echo "✅ Code formatting complete"

format-check: ## Check if code is properly formatted
	@echo "🔍 Checking code formatting..."
	black --check --diff .
	isort --check-only --diff .
	@echo "✅ Code formatting is correct"

lint: ## Run all linting checks
	@echo "🔍 Running linting checks..."
	flake8 .
	mypy .
	@echo "✅ Linting complete"

lint-fix: ## Fix automatically fixable linting issues
	@echo "🔧 Fixing linting issues..."
	autopep8 --in-place --recursive .
	@echo "✅ Auto-fixes applied"

security: ## Run security checks
	@echo "🔒 Running security checks..."
	bandit -r . -f json -o bandit-report.json || true
	safety check
	@echo "✅ Security checks complete"

# Testing targets
test: ## Run tests with coverage
	@echo "🧪 Running tests..."
	python -m pytest
	@echo "✅ Tests complete"

test-unit: ## Run unit tests only
	@echo "🧪 Running unit tests..."
	python -m pytest tests/unit -m unit
	@echo "✅ Unit tests complete"

test-integration: ## Run integration tests only
	@echo "🧪 Running integration tests..."
	python -m pytest tests/integration -m integration
	@echo "✅ Integration tests complete"

test-coverage: ## Run tests and generate coverage report
	@echo "📊 Running tests with coverage..."
	python -m pytest --cov-report=html --cov-report=term
	@echo "📊 Coverage report: htmlcov/index.html"

test-watch: ## Run tests in watch mode (requires pytest-xvs)
	@echo "👀 Running tests in watch mode..."
	python -m pytest -f

# Quality assurance
check: ## Run all code quality checks
	@echo "🔍 Running all quality checks..."
	make format-check
	make lint
	make security
	make test
	@echo "✅ All checks passed"

all: format lint security test ## Run format, lint, security, and test

pre-commit: ## Install pre-commit hooks
	@echo "🔗 Installing pre-commit hooks..."
	pre-commit install
	@echo "✅ Pre-commit hooks installed"

pre-commit-run: ## Run pre-commit hooks on all files
	@echo "🔗 Running pre-commit hooks..."
	pre-commit run --all-files
	@echo "✅ Pre-commit checks complete"

# Docker targets
docker-dev: ## Start development environment with Docker
	@echo "🐳 Starting development environment..."
	./dev-start.sh start

docker-dev-admin: ## Start development environment with admin tools
	@echo "🐳 Starting development environment with admin tools..."
	./dev-start.sh admin

docker-dev-stop: ## Stop development environment
	@echo "🐳 Stopping development environment..."
	$(COMPOSE_DEV) down

docker-dev-clean: ## Clean development environment (removes volumes)
	@echo "🧹 Cleaning development environment..."
	$(COMPOSE_DEV) down -v
	docker system prune -f

docker-prod: ## Start production environment
	@echo "🐳 Starting production environment..."
	$(COMPOSE) up -d

docker-logs: ## View development container logs
	@echo "📝 Viewing development logs..."
	$(COMPOSE_DEV) logs -f bot-dev

# Database targets
db-migrate: ## Run database migrations
	@echo "📊 Running database migrations..."
	$(COMPOSE_DEV) --profile migrate run --rm migrate-dev

db-shell: ## Access database shell
	@echo "📊 Connecting to database..."
	$(COMPOSE_DEV) exec postgres-dev psql -U depeg_dev -d depeg_alert_dev

db-reset: ## Reset development database
	@echo "🔄 Resetting development database..."
	$(COMPOSE_DEV) down postgres-dev
	docker volume rm depeg-alert_postgres_dev_data || true
	$(COMPOSE_DEV) up -d postgres-dev
	sleep 10
	make db-migrate

# Utility targets
clean: ## Clean build artifacts and cache files
	@echo "🧹 Cleaning build artifacts..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	@echo "✅ Cleanup complete"

clean-docker: ## Clean Docker containers and images
	@echo "🐳 Cleaning Docker resources..."
	docker system prune -af
	docker volume prune -f
	@echo "✅ Docker cleanup complete"

# Development utilities
run-local: ## Run bot locally (requires .env file)
	@echo "🤖 Running bot locally..."
	$(PYTHON) -m bot.main

run-scheduler: ## Run scheduler only
	@echo "⏰ Running scheduler..."
	$(PYTHON) -c "from bot.scheduler import start_scheduler; start_scheduler()"

deps-check: ## Check for dependency updates
	@echo "📦 Checking for dependency updates..."
	pip list --outdated

deps-tree: ## Show dependency tree
	@echo "🌳 Dependency tree:"
	pipdeptree

# Documentation targets
docs: ## Generate documentation (if docs exist)
	@echo "📚 Generating documentation..."
	@echo "Documentation generation not configured yet"

# Release targets
version: ## Show current version
	@echo "Version: 2.0.0"

release-check: ## Check if ready for release
	@echo "🚀 Checking release readiness..."
	make check
	@echo "✅ Ready for release"

# Quick development commands
dev: docker-dev ## Alias for docker-dev
stop: docker-dev-stop ## Alias for docker-dev-stop
logs: docker-logs ## Alias for docker-logs