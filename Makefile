.PHONY: help install run lint format clean docker-up docker-build migrate migrate-revert migrate-generate pre-commit

help:
	@echo "🔍 Displaying help:"; grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies using poetry
	@echo "📦 Installing dependencies..."; poetry install

run: ## Run the Telegram bot
	@echo "🚀 Running the Telegram bot..."; poetry run python -m bot

run-watch: ## Run the Telegram bot with watchfiles
	@echo "🔄 Running the Telegram bot with watchfiles..."; poetry run watchfiles "python -m bot" bot

lint: ## Lint the code with Ruff
	@echo "🔍 Linting code..."; poetry run ruff check bot

format: ## Format the code with Black
	@echo "🖋️ Formatting code..."; poetry run black bot

mypy: ## Lint the code with MyPy
	@echo "🔍 Checking types with MyPy..."; poetry run mypy bot

check-all: mypy lint format ## Run all linters

clean: ## Clean temporary files
	@echo "🧹 Cleaning temporary files..."; find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -exec rm -rf {} +

docker-up: ## Start the project with Docker
	@echo "🐳 Starting Docker..."; docker-compose up --build

docker-build: ## Rebuild Docker images
	@echo "🔨 Rebuilding Docker images..."; docker-compose build

migrate: ## Run database migrations
	@echo "🔄 Running database migrations..."; poetry run alembic upgrade head

migrate-revert: ## Revert migrations
	@echo "⏪ Reverting migrations..."; \
	poetry run alembic downgrade -1

migrate-generate: ## Generate migrations
	@echo "📝 Generating migrations..."; \
	if [ "$(filter-out $@,$(MAKECMDGOALS))" = "" ]; then \
	    echo "Error: migration message is required"; exit 1; \
	fi; \
	poetry run alembic revision --autogenerate -m "$(filter-out $@,$(MAKECMDGOALS))"

pre-commit: ## Install pre-commit hooks
	@echo "🔗 Installing pre-commit hooks..."; pre-commit install

%:
	@:
