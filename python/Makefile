
SHELL = /bin/bash
.SHELLFLAGS = -o pipefail -c

.PHONY: help
help: ## Print info about all commands
	@echo "Commands:"
	@echo
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[01;32m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: deps
deps: ## Install dependencies using pipenv
	pipenv install --dev

.PHONY: lint
lint: ## Run lints (eg, flake8, mypy)
	pipenv run flake8 . --exit-zero
	pipenv run isort -q -c . || true
	pipenv run mypy *.py sandcrawler/ tests/ --ignore-missing-imports

.PHONY: fmt
fmt: ## Run code formating on all source code
	pipenv run isort --atomic .
	pipenv run black --line-length 96 sandcrawler/ tests/ scripts/ *.py

.PHONY: test
test: ## Run all tests and lints
	pipenv run pytest

.PHONY: coverage
coverage: ## Run all tests with coverage
	pipenv run pytest --cov --cov-report=term --cov-report=html
