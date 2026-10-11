.PHONY: help build up down restart logs clean setup migrate

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Initial setup - copy .env file
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ .env file created. Please edit it with your API keys!"; \
		echo "   - Generate SECRET_KEY: openssl rand -hex 32"; \
		echo "   - Get ANTHROPIC_API_KEY from: https://console.anthropic.com/"; \
	else \
		echo "⚠️  .env file already exists"; \
	fi

build: ## Build all containers
	docker-compose build

up: ## Start all services
	docker-compose up

up-d: ## Start all services in detached mode
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View logs from all services
	docker-compose logs -f

logs-backend: ## View backend logs
	docker-compose logs -f backend

logs-frontend: ## View frontend logs
	docker-compose logs -f frontend

logs-db: ## View database logs
	docker-compose logs -f db

migrate: ## Run database migrations
	docker-compose exec backend alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="description")
	docker-compose exec backend alembic revision --autogenerate -m "$(MSG)"

create-admin: ## Create admin user in the database
	docker-compose exec backend python create_admin_direct.py

shell-backend: ## Open shell in backend container
	docker-compose exec backend bash

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend sh

shell-db: ## Open PostgreSQL shell
	docker-compose exec db psql -U postgres -d marketing_saas

clean: ## Remove all containers, volumes, and images
	docker-compose down -v --rmi all

clean-db: ## Remove only database volume
	docker-compose down -v

dev: setup build up-d ## Complete development setup
	@echo ""
	@echo "🚀 Development environment is starting..."
	@echo ""
	@echo "Services will be available at:"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend:  http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "View logs with: make logs"
	@echo ""
