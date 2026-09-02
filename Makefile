# OceanEmbed — developer command interface
# Standardized commands for setup, testing, linting, training, and local execution.

.PHONY: help setup dev-venv lint format test test-all verify-env verify-contracts verify-datasets run-stack run-training

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

setup: ## Create python environments and install dependencies for all modules
	uv python install 3.11
	uv venv .venv
	. .venv/bin/activate && uv pip install -e . \
		&& uv pip install -e backend \
		&& uv pip install -e ml \
		&& uv pip install -e data-engineering

lint: ## Run repository-wide linting and formatting checks
	ruff check backend ml data-engineering scripts
	ruff format --check backend ml data-engineering scripts

format: ## Auto-format code
	ruff check --fix backend ml data-engineering scripts
	ruff format backend ml data-engineering scripts

test: ## Run the default local test suite (backend + ml + data-engineering)
	pytest

test-all: ## Run all tests, lint, and contract verification together
	make lint
	make test
	python scripts/verify-contracts.py

verify-env: ## Detect missing runtime dependencies / incompatible versions
	python scripts/verify-environment.py

verify-contracts: ## Validate API/data/ML contracts against implementations
	python scripts/verify-contracts.py

verify-datasets: ## Check current dataset availability and metadata (Copernicus describe)
	python data-engineering/scripts/verify_datasets.py

run-stack: ## Start the complete local application stack
	scripts/run-local-stack.sh

run-training: ## Run a small reproducible local training experiment
	scripts/run-local-training.sh

docker-build: ## Build application Docker images
	scripts/build-images.sh

deploy-staging: ## Deploy the current build to staging
	scripts/deploy-staging.sh