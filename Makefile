# Shortcuts for local development. Run `make help` to list them.
.DEFAULT_GOAL := help
PYTHON ?= python3

.PHONY: help install seed api web dev test lint build up down clean

help:  ## Show this list
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-9s %s\n", $$1, $$2}'

install:  ## Install backend (pip) and frontend (npm) dependencies
	cd backend && $(PYTHON) -m pip install -r requirements-dev.txt
	cd frontend && npm install

seed:  ## Clean the CSV with pandas and (re)load the database
	cd backend && $(PYTHON) -m paddle_finder.data.seed

api:  ## Run the Flask API on http://localhost:5001
	cd backend && $(PYTHON) -m flask --app paddle_finder.api run --debug --port 5001

web:  ## Run the React dev server on http://localhost:5173
	cd frontend && npm run dev

test:  ## Run every test (pytest + vitest)
	cd backend && $(PYTHON) -m pytest
	cd frontend && npm test

lint:  ## Lint Python and type-check TypeScript
	cd backend && ruff check .
	cd frontend && npm run typecheck

build:  ## Build the frontend for production
	cd frontend && npm run build

up:  ## Run the whole stack in Docker (web :8080, api :5001, db :5433)
	docker compose up --build

down:  ## Stop the Docker stack
	docker compose down

clean:  ## Remove build output and the local SQLite database
	rm -rf frontend/dist backend/instance backend/.pytest_cache backend/.coverage
