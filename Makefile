# Makefile - Comprehensive Development & Production Commands

.PHONY: help build run stop clean test data logs lint format check docker-build docker-run

# Default target
help: ## Show this help message
	@echo "AI Cost & Insights Copilot - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Environment setup
setup: ## Initial project setup
	@echo "🏗️ Setting up AI Cost & Insights Copilot..."
	@if [ ! -f .env ]; then \
		echo "📝 Creating .env file from template..."; \
		cp .env.example .env; \
		echo "⚠️ Please edit .env file with your configuration"; \
	fi
	@mkdir -p data logs tests scripts
	@echo "✅ Setup complete!"

# Build commands
build: ## Build all Docker containers
	@echo "🏗️ Building AI Cost & Insights Copilot containers..."
	docker-compose build --parallel
	@echo "✅ Build complete!"

build-dev: ## Build development containers with cache busting
	@echo "🏗️ Building development containers..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache
	@echo "✅ Development build complete!"

# Run commands
run: setup ## Start all services in production mode
	@echo "🚀 Starting AI Cost & Insights Copilot..."
	docker-compose up -d
	@echo "✅ Services started successfully!"
	@echo ""
	@echo "🌐 Access URLs:"
	@echo "   Frontend: http://localhost:8501"
	@echo "   API: http://localhost:8000"
	@echo "   API Docs: http://localhost:8000/docs"
	@echo "   Health Check: http://localhost:8000/health"
	@echo ""
	@echo "📊 To view logs: make logs"
	@echo "⏹️ To stop: make stop"

run-dev: setup ## Start all services in development mode with hot reload
	@echo "🔧 Starting development environment..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "✅ Development environment started!"

run-local: setup data ## Run services locally without Docker
	@echo "🔧 Starting local development environment..."
	@echo "📊 Starting API server..."
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
	@sleep 3
	@echo "🖥️ Starting Streamlit frontend..."
	cd frontend && streamlit run app.py --server.port 8501 &
	@echo "✅ Local services started!"
	@echo "   API: http://localhost:8000"
	@echo "   Frontend: http://localhost:8501"

# Stop commands
stop: ## Stop all services
	@echo "🛑 Stopping AI Cost & Insights Copilot..."
	docker-compose down
	@echo "✅ Services stopped!"

stop-dev: ## Stop development services
	@echo "🛑 Stopping development environment..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
	@echo "✅ Development environment stopped!"

# Data commands
data: ## Generate sample data
	@echo "📊 Generating sample data..."
	@if [ -f scripts/generate_sample_data.py ]; then \
		python scripts/generate_sample_data.py; \
	else \
		docker-compose run --rm data-init; \
	fi
	@echo "✅ Sample data generated!"

data-clean: ## Clean and regenerate data
	@echo "🧹 Cleaning existing data..."
	rm -f data/app.db
	@echo "📊 Regenerating sample data..."
	$(MAKE) data
	@echo "✅ Data cleaned and regenerated!"

# Testing commands
test: ## Run all tests
	@echo "🧪 Running all tests..."
	python -m pytest tests/ -v --tb=short
	@echo "✅ Tests completed!"

test-unit: ## Run unit tests only
	@echo "🧪 Running unit tests..."
	python -m pytest tests/test_unit.py -v
	@echo "✅ Unit tests completed!"

test-integration: ## Run integration tests
	@echo "🧪 Running integration tests..."
	python -m pytest tests/test_integration.py -v
	@echo "✅ Integration tests completed!"

test-api: ## Run API tests
	@echo "🧪 Running API tests..."
	python -m pytest tests/test_api.py -v
	@echo "✅ API tests completed!"

test-coverage: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage..."
	python -m pytest tests/ --cov=app --cov-report=html --cov-report=term
	@echo "✅ Coverage report generated in htmlcov/"

# Quality commands
lint: ## Run code linting
	@echo "🔍 Running linting..."
	flake8 app/ tests/ --max-line-length=100 --ignore=E203,W503
	black app/ tests/ --check --diff
	isort app/ tests/ --check-only --diff
	@echo "✅ Linting complete!"

format: ## Format code
	@echo "🎨 Formatting code..."
	black app/ tests/
	isort app/ tests/
	@echo "✅ Code formatted!"

type-check: ## Run type checking
	@echo "🔍 Running type checks..."
	mypy app/ --ignore-missing-imports
	@echo "✅ Type checking complete!"

check: lint type-check ## Run all quality checks
	@echo "✅ All quality checks passed!"

# Logging commands
logs: ## View logs from all services
	docker-compose logs -f

logs-api: ## View API logs only
	docker-compose logs -f api

logs-frontend: ## View frontend logs only
	docker-compose logs -f frontend

logs-tail: ## Tail recent logs
	docker-compose logs --tail=100 -f

# Shell commands
shell: ## Open shell in API container
	docker-compose exec api /bin/bash

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend /bin/bash

shell-db: ## Open database shell
	@if [ -f data/app.db ]; then \
		sqlite3 data/app.db; \
	else \
		echo "❌ Database not found. Run 'make data' first."; \
	fi

# Maintenance commands
restart: stop run ## Restart all services
	@echo "🔄 Services restarted!"

restart-api: ## Restart API service only
	@echo "🔄 Restarting API service..."
	docker-compose restart api
	@echo "✅ API service restarted!"

restart-frontend: ## Restart frontend service only
	@echo "🔄 Restarting frontend service..."
	docker-compose restart frontend
	@echo "✅ Frontend service restarted!"

clean: ## Clean up containers, images, and volumes
	@echo "🧹 Cleaning up..."
	docker-compose down -v --rmi all --remove-orphans
	docker system prune -f
	@echo "✅ Cleanup complete!"

clean-data: ## Clean data directory
	@echo "🧹 Cleaning data directory..."
	rm -rf data/*.db logs/*.log
	@echo "✅ Data cleaned!"

# Status commands
status: ## Show status of all services
	@echo "📊 Service Status:"
	docker-compose ps

health: ## Check health of all services
	@echo "🏥 Health Check:"
	@curl -s http://localhost:8000/health | python -m json.tool 2>/dev/null || echo "❌ API not responding"
	@curl -s http://localhost:8501/_stcore/health >/dev/null && echo "✅ Frontend: Healthy" || echo "❌ Frontend: Unhealthy"

ps: status ## Alias for status

# Development commands
dev: run-dev ## Start development environment (alias)

install: ## Install development dependencies
	@echo "📦 Installing development dependencies..."
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	@echo "✅ Dependencies installed!"

update: ## Update dependencies
	@echo "📦 Updating dependencies..."
	pip install --upgrade -r requirements.txt
	@echo "✅ Dependencies updated!"

# Production commands
prod: ## Start production environment
	@echo "🚀 Starting production environment..."
	docker-compose --profile production up -d
	@echo "✅ Production environment started!"

backup: ## Backup data and logs
	@echo "💾 Creating backup..."
	@mkdir -p backups
	@tar -czf backups/backup-$(shell date +%Y%m%d-%H%M%S).tar.gz data/ logs/
	@echo "✅ Backup created in backups/"

# Monitoring commands
monitor: ## Show real-time system monitoring
	@echo "📊 System Monitoring (Press Ctrl+C to exit):"
	@while true; do \
		clear; \
		echo "=== AI Cost & Insights Copilot - System Monitor ==="; \
		echo ""; \
		echo "Service Status:"; \
		docker-compose ps; \
		echo ""; \
		echo "Resource Usage:"; \
		docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>/dev/null || echo "No containers running"; \
		echo ""; \
		echo "Health Status:"; \
		make health 2>/dev/null; \
		echo ""; \
		echo "Last updated: $$(date)"; \
		sleep 5; \
	done

# Documentation commands
docs: ## Generate documentation
	@echo "📚 Generating documentation..."
	@if command -v sphinx-build >/dev/null 2>&1; then \
		sphinx-build -b html docs/ docs/_build/html/; \
		echo "✅ Documentation generated in docs/_build/html/"; \
	else \
		echo "⚠️ Sphinx not installed. Install with: pip install sphinx"; \
	fi

# Deployment commands
deploy: ## Deploy to production (requires additional setup)
	@echo "🚀 Deploying to production..."
	@echo "⚠️ This requires additional configuration for your deployment target"

# Utility commands
version: ## Show version information
	@echo "AI Cost & Insights Copilot"
	@echo "Version: 2.1.0"
	@echo "Build: $$(date)"

env: ## Show environment information
	@echo "Environment Information:"
	@echo "Docker: $$(docker --version 2>/dev/null || echo 'Not installed')"
	@echo "Docker Compose: $$(docker-compose --version 2>/dev/null || echo 'Not installed')"
	@echo "Python: $$(python --version 2>/dev/null || echo 'Not installed')"
	@echo "Node: $$(node --version 2>/dev/null || echo 'Not installed')"

# Quick start command
quickstart: setup build data run ## Complete quickstart setup
	@echo ""
	@echo "🎉 AI Cost & Insights Copilot is ready!"
	@echo ""
	@echo "🌐 Open your browser to:"
	@echo "   • Frontend: http://localhost:8501"
	@echo "   • API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "📖 Try asking questions like:"
	@echo "   • 'What was total spend in September?'"
	@echo "   • 'Which resources look idle?'"
	@echo "   • 'Show me cost trends'"