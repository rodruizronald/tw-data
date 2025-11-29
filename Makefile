# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                      JOB PROCESSING PIPELINE - MAKEFILE                      ║
# ╠══════════════════════════════════════════════════════════════════════════════╣
# ║  A comprehensive build system for managing the job processing pipeline       ║
# ║                                                                              ║
# ║  Usage: make <target>                                                        ║
# ║  Help:  make help                                                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │                              CONFIGURATION                                   │
# └──────────────────────────────────────────────────────────────────────────────┘

# Load environment variables from .env file if it exists
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Python configuration
PYTHON        ?= python
PIP           ?= pip

# Docker configuration
COMPOSE_FILE  := docker/docker-compose.yml
COMPOSE       := docker-compose -f $(COMPOSE_FILE)

# Container names
CONTAINER_DB        := tw-mongodb
CONTAINER_PIPELINE  := tw-pipeline
CONTAINER_DASHBOARD := tw-dashboard

# Paths
BACKUP_DIR    := ./backups
SRC_DIRS      := src tools

# Default target
.DEFAULT_GOAL := help

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │                              PHONY TARGETS                                   │
# └──────────────────────────────────────────────────────────────────────────────┘

.PHONY: \
    help \
    install clean \
    format-check import-check type-check lint yaml-check check-all \
    format fix-imports fix-lint fix-all \
    pre-commit-install pre-commit-run pre-commit-update \
    up down restart status purge \
    restart-pipeline restart-dashboard \
    rebuild rebuild-pipeline rebuild-dashboard \
    recreate-pipeline recreate-dashboard \
    logs logs-pipeline logs-server logs-db logs-dashboard \
    shell-db shell-pipeline shell-dashboard \
    backup restore verify-indexes clean-data \
    dashboard \
	prefect-server prefect-config prefect-reset

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║                         1. ENVIRONMENT SETUP                                 ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

install: ## Install development dependencies and Playwright browsers
	@echo "📦 Installing development dependencies..."
	@$(PIP) install -e ".[dev]"
	@echo "🎭 Installing Playwright browsers..."
	@playwright install
	@echo "✅ Development dependencies installed successfully"

clean: ## Clean Python cache files and build artifacts
	@echo "🧹 Cleaning up Python cache files..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup completed successfully"

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║                          2. CODE QUALITY                                     ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ┌────────────────────────────────────┐
# │          2.1 Checks                │
# └────────────────────────────────────┘

format-check: ## Check code formatting with Ruff (no changes)
	@echo "🔍 Checking code formatting with Ruff..."
	@ruff format --check --diff $(SRC_DIRS)
	@echo "✅ Ruff formatting check passed"

import-check: ## Check import sorting with Ruff (no changes)
	@echo "🔍 Checking import sorting with Ruff..."
	@ruff check --select I --diff $(SRC_DIRS)
	@echo "✅ Import sorting check passed"

type-check: ## Run static type checking with mypy
	@echo "🔍 Running type checking with mypy..."
	@mypy $(SRC_DIRS)
	@echo "✅ Type checking passed"

lint: ## Run linting with Ruff
	@echo "🔍 Running linting with Ruff..."
	@ruff check $(SRC_DIRS) --statistics
	@echo "✅ Linting passed"

yaml-check: ## Validate YAML files with yamllint
	@echo "🔍 Checking YAML files with yamllint..."
	@yamllint pipeline.yaml companies.yaml .pre-commit-config.yaml
	@echo "✅ YAML linting passed"

check-all: format-check import-check lint type-check ## Run all code quality checks
	@echo ""
	@echo "════════════════════════════════════════"
	@echo "✅ All code quality checks passed!"
	@echo "════════════════════════════════════════"

# ┌────────────────────────────────────┐
# │          2.2 Auto-fixes            │
# └────────────────────────────────────┘

format: ## Auto-format code with Ruff
	@echo "🔧 Auto-formatting code with Ruff..."
	@ruff format $(SRC_DIRS)
	@echo "✅ Formatting applied"

fix-imports: ## Auto-fix import sorting with Ruff
	@echo "🔧 Fixing import sorting with Ruff..."
	@ruff check --select I --fix $(SRC_DIRS)
	@echo "✅ Import sorting fixed"

fix-lint: ## Auto-fix linting issues with Ruff
	@echo "🔧 Auto-fixing linting issues with Ruff..."
	@ruff check --fix $(SRC_DIRS)
	@echo "✅ Linting issues fixed"

fix-all: format fix-lint fix-imports ## Apply all auto-fixes (format + lint + imports)
	@echo ""
	@echo "════════════════════════════════════════"
	@echo "✅ All fixes applied!"
	@echo "════════════════════════════════════════"

# ┌────────────────────────────────────┐
# │        2.3 Pre-commit Hooks        │
# └────────────────────────────────────┘

pre-commit-install: ## Install pre-commit hooks
	@echo "🪝 Installing pre-commit hooks..."
	@pre-commit install
	@echo "✅ Pre-commit hooks installed"

pre-commit-run: ## Run pre-commit on all files
	@echo "🪝 Running pre-commit on all files..."
	@pre-commit run --all-files
	@echo "✅ Pre-commit checks completed"

pre-commit-update: ## Update pre-commit hooks to latest versions
	@echo "🪝 Updating pre-commit hooks..."
	@pre-commit autoupdate
	@echo "✅ Pre-commit hooks updated"

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║                       3. DOCKER SERVICES                                     ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ┌────────────────────────────────────┐
# │      3.1 Lifecycle (All)           │
# └────────────────────────────────────┘

up: ## Start all services (MongoDB + Prefect + Pipeline)
	@echo "🚀 Starting all services..."
	@$(COMPOSE) up -d
	@echo ""
	@echo "════════════════════════════════════════"
	@echo "✅ All services started!"
	@echo "════════════════════════════════════════"
	@echo ""
	@echo "📊 Prefect UI:  http://localhost:4200"
	@echo "🗄️  MongoDB:    localhost:27017"
	@echo ""
	@echo "💡 Useful commands:"
	@echo "   make logs          - View all logs"
	@echo "   make logs-pipeline - View pipeline logs"
	@echo "   make status        - Check service status"
	@echo "   make down          - Stop all services"

down: ## Stop all services
	@echo "🛑 Stopping all services..."
	@$(COMPOSE) down
	@echo "✅ All services stopped"

restart: ## Restart all services
	@echo "🔄 Restarting all services..."
	@$(COMPOSE) restart
	@echo "✅ All services restarted"

status: ## Show service status and health checks
	@echo "📊 Service Status:"
	@echo ""
	@$(COMPOSE) ps
	@echo ""
	@echo "🏥 Health Checks:"
	@docker exec $(CONTAINER_DB) mongosh -u admin -p admin --authenticationDatabase admin --eval "db.adminCommand('ping')" --quiet 2>/dev/null \
		&& echo "   ✅ MongoDB: Healthy" || echo "   ❌ MongoDB: Unhealthy"
	@curl -sf http://localhost:4200/api/health > /dev/null \
		&& echo "   ✅ Prefect Server: Healthy" || echo "   ❌ Prefect Server: Unhealthy"

purge: ## Remove all services AND volumes (⚠️  DATA LOSS!)
	@echo "⚠️  WARNING: This will remove ALL volumes (MongoDB + Prefect data)!"
	@echo "   This action cannot be undone."
	@echo ""
	@read -p "Type 'DELETE' to confirm: " confirm; \
	if [ "$$confirm" = "DELETE" ]; then \
		echo ""; \
		echo "🗑️  Stopping services and removing all volumes..."; \
		$(COMPOSE) down -v; \
		echo "✅ All volumes removed"; \
		echo "💡 Run 'make up' to start with fresh volumes"; \
	else \
		echo "❌ Operation cancelled"; \
	fi

# ┌────────────────────────────────────┐
# │    3.2 Lifecycle (Individual)      │
# └────────────────────────────────────┘

restart-pipeline: ## Restart pipeline service only
	@echo "🔄 Restarting pipeline..."
	@$(COMPOSE) restart pipeline
	@echo "✅ Pipeline restarted"
	@echo "💡 Run 'make logs-pipeline' to view logs"

restart-dashboard: ## Restart dashboard service only
	@echo "🔄 Restarting dashboard..."
	@$(COMPOSE) restart dashboard
	@echo "✅ Dashboard restarted"
	@echo "💡 Run 'make logs-dashboard' to view logs"

# ┌────────────────────────────────────┐
# │         3.3 Rebuild                │
# └────────────────────────────────────┘

rebuild: ## Rebuild and restart all services
	@echo "🔨 Rebuilding all services..."
	@$(COMPOSE) up -d --build
	@echo "✅ All services rebuilt and restarted"
	@echo "💡 Run 'make logs' to view logs"

rebuild-pipeline: ## Rebuild and restart pipeline only
	@echo "🔨 Rebuilding pipeline..."
	@$(COMPOSE) up -d --build --no-deps pipeline
	@echo "✅ Pipeline rebuilt and restarted"
	@echo "💡 Run 'make logs-pipeline' to view logs"

rebuild-dashboard: ## Rebuild and restart dashboard only
	@echo "🔨 Rebuilding dashboard..."
	@$(COMPOSE) up -d --build --no-deps dashboard
	@echo "✅ Dashboard rebuilt and restarted"
	@echo "💡 Run 'make logs-dashboard' to view logs"

# ┌────────────────────────────────────┐
# │         3.4 Recreate               │
# └────────────────────────────────────┘

recreate-pipeline: ## Recreate pipeline container (pull config changes)
	@echo "🔄 Recreating pipeline container..."
	@$(COMPOSE) up -d pipeline
	@echo "✅ Pipeline recreated"
	@echo "💡 Run 'make logs-pipeline' to view logs"

recreate-dashboard: ## Recreate dashboard container (pull config changes)
	@echo "🔄 Recreating dashboard container..."
	@$(COMPOSE) up -d dashboard
	@echo "✅ Dashboard recreated"
	@echo "💡 Run 'make logs-dashboard' to view logs"

# ┌────────────────────────────────────┐
# │           3.5 Logs                 │
# └────────────────────────────────────┘

logs: ## View logs from all services (follow mode)
	@echo "📋 Showing all logs (Ctrl+C to exit)..."
	@$(COMPOSE) logs -f

logs-pipeline: ## View pipeline logs only (follow mode)
	@echo "📋 Showing pipeline logs (Ctrl+C to exit)..."
	@$(COMPOSE) logs -f pipeline

logs-server: ## View Prefect server logs only (follow mode)
	@echo "📋 Showing Prefect server logs (Ctrl+C to exit)..."
	@$(COMPOSE) logs -f prefect

logs-db: ## View MongoDB logs only (follow mode)
	@echo "📋 Showing MongoDB logs (Ctrl+C to exit)..."
	@$(COMPOSE) logs -f mongodb

logs-dashboard: ## View dashboard logs only (follow mode)
	@echo "📋 Showing dashboard logs (Ctrl+C to exit)..."
	@$(COMPOSE) logs -f dashboard

# ┌────────────────────────────────────┐
# │        3.6 Shell Access            │
# └────────────────────────────────────┘

shell-db: ## Open MongoDB shell
	@echo "🐚 Connecting to MongoDB shell..."
	@docker exec -it $(CONTAINER_DB) mongosh -u admin -p admin --authenticationDatabase admin

shell-pipeline: ## Open bash shell in pipeline container
	@echo "🐚 Connecting to pipeline container..."
	@docker exec -it $(CONTAINER_PIPELINE) bash

shell-dashboard: ## Open bash shell in dashboard container
	@echo "🐚 Connecting to dashboard container..."
	@docker exec -it $(CONTAINER_DASHBOARD) bash

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║                        4. DATABASE OPERATIONS                                ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

backup: ## Create MongoDB backup to ./backups/
	@echo "💾 Creating MongoDB backup..."
	@mkdir -p $(BACKUP_DIR)
	@docker exec $(CONTAINER_DB) mongodump \
		--username admin \
		--password admin \
		--authenticationDatabase admin \
		--db job_scraper \
		--out /tmp/backup
	@docker cp $(CONTAINER_DB):/tmp/backup/job_scraper $(BACKUP_DIR)/backup-$(shell date +%Y%m%d-%H%M%S)
	@echo "✅ Backup saved to $(BACKUP_DIR)/backup-$(shell date +%Y%m%d-%H%M%S)"

restore: ## Restore MongoDB from backup
	@echo "📂 Available backups:"
	@ls -1 $(BACKUP_DIR)/ 2>/dev/null || echo "   No backups found"
	@echo ""
	@read -p "Enter backup folder name: " backup; \
	if [ -d "$(BACKUP_DIR)/$$backup" ]; then \
		docker cp $(BACKUP_DIR)/$$backup $(CONTAINER_DB):/tmp/restore && \
		docker exec $(CONTAINER_DB) mongorestore \
			--username admin \
			--password admin \
			--authenticationDatabase admin \
			--db job_scraper \
			--drop \
			/tmp/restore && \
		echo "✅ MongoDB restore completed"; \
	else \
		echo "❌ Backup folder not found"; \
		exit 1; \
	fi

verify-indexes: ## Verify MongoDB indexes exist
	@echo "🔍 Verifying MongoDB indexes..."
	@docker exec $(CONTAINER_DB) mongosh \
		-u admin \
		-p admin \
		--authenticationDatabase admin \
		--eval "db.getSiblingDB('job_scraper').job_listings.getIndexes()" \
		--quiet
	@echo "✅ Index verification completed"

clean-data: ## Delete all MongoDB data (⚠️  DATA LOSS!)
	@echo "⚠️  WARNING: This will delete ALL MongoDB data!"
	@echo "   This action cannot be undone."
	@echo ""
	@read -p "Type 'DELETE' to confirm: " confirm; \
	if [ "$$confirm" = "DELETE" ]; then \
		echo ""; \
		echo "🗑️  Dropping MongoDB database..."; \
		docker exec $(CONTAINER_DB) mongosh \
			-u admin \
			-p admin \
			--authenticationDatabase admin \
			--eval "db.getSiblingDB('job_scraper').dropDatabase()" \
			--quiet; \
		echo "✅ MongoDB data deleted (Prefect data preserved)"; \
		echo "💡 Database will be recreated on next pipeline run"; \
	else \
		echo "❌ Operation cancelled"; \
	fi

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║                            5. DASHBOARD                                      ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

dashboard: ## Start Pipeline Health Dashboard locally (Streamlit)
	@echo "🚀 Starting Pipeline Health Dashboard..."
	@echo "📊 Dashboard: http://localhost:8501"
	@echo "⏹️  Press Ctrl+C to stop"
	@echo ""
	@PYTHONPATH=src streamlit run src/dashboard/app.py --server.port=8501 --server.address=localhost

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║                         6. PREFECT MANAGEMENT                                ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

prefect-server: ## Start Prefect server locally
	@echo "🚀 Starting Prefect server..."
	@echo "📊 Server: http://127.0.0.1:4200"
	@echo "⏹️  Press Ctrl+C to stop"
	@echo ""
	@prefect server start

prefect-config: ## Configure Prefect to use local server
	@echo "⚙️  Configuring Prefect to use local server..."
	@prefect config set PREFECT_API_URL=http://127.0.0.1:4200/api
	@echo "✅ Prefect configured for local server"

prefect-reset: ## Reset Prefect to default configuration
	@echo "🔄 Resetting Prefect to default configuration..."
	@prefect config unset PREFECT_API_URL
	@echo "✅ Prefect reset to default configuration"

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║                               7. HELP                                        ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

help: ## Show this help message
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════════════════════╗"
	@echo "║                      JOB PROCESSING PIPELINE - MAKEFILE                      ║"
	@echo "╚══════════════════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; section=""} \
		/^# ╔.*1\. / {section="📦 ENVIRONMENT SETUP"; printf "\n\033[1;34m%s\033[0m\n", section} \
		/^# ╔.*2\. / {section="🔍 CODE QUALITY"; printf "\n\033[1;34m%s\033[0m\n", section} \
		/^# ┌.*2\.1/ {printf "\n  \033[1;36mChecks:\033[0m\n"} \
		/^# ┌.*2\.2/ {printf "\n  \033[1;36mAuto-fixes:\033[0m\n"} \
		/^# ┌.*2\.3/ {printf "\n  \033[1;36mPre-commit:\033[0m\n"} \
		/^# ╔.*3\. / {section="🐳 DOCKER SERVICES"; printf "\n\033[1;34m%s\033[0m\n", section} \
		/^# ┌.*3\.1/ {printf "\n  \033[1;36mLifecycle (All Services):\033[0m\n"} \
		/^# ┌.*3\.2/ {printf "\n  \033[1;36mLifecycle (Individual):\033[0m\n"} \
		/^# ┌.*3\.3/ {printf "\n  \033[1;36mRebuild:\033[0m\n"} \
		/^# ┌.*3\.4/ {printf "\n  \033[1;36mRecreate:\033[0m\n"} \
		/^# ┌.*3\.5/ {printf "\n  \033[1;36mLogs:\033[0m\n"} \
		/^# ┌.*3\.6/ {printf "\n  \033[1;36mShell Access:\033[0m\n"} \
		/^# ╔.*4\. / {section="🗄️  DATABASE OPERATIONS"; printf "\n\033[1;34m%s\033[0m\n", section} \
		/^# ╔.*5\. / {section="📊 DASHBOARD"; printf "\n\033[1;34m%s\033[0m\n", section} \
		/^# ╔.*6\. / {section="🔮 PREFECT MANAGEMENT"; printf "\n\033[1;34m%s\033[0m\n", section} \
		/^[a-zA-Z_-]+:.*##/ {printf "    \033[0;32m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "────────────────────────────────────────────────────────────────────────────────"
	@echo ""
	@echo "💡 Quick Start:"
	@echo "   1. make up              # Start all services"
	@echo "   2. make logs-pipeline   # Watch pipeline execution"
	@echo "   3. make dashboard       # View metrics dashboard"
	@echo "   4. Open http://localhost:4200 for Prefect UI"
	@echo ""
	@echo "🔧 Development Workflow:"
	@echo "   make install            # Setup development environment"
	@echo "   make pre-commit-install # Install git hooks"
	@echo "   make check-all          # Run all quality checks"
	@echo "   make fix-all            # Auto-fix issues"
	@echo ""
