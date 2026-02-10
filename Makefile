.PHONY: dev start test lint format build up down

dev:
	poetry run uvicorn app.main:app --reload --port 8000

start:
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

test:
	poetry run pytest tests/ -v

lint:
	poetry run ruff check app/ tests/

format:
	poetry run ruff check app/ tests/ --fix

build:
	docker build -t pdf-processor .

up:
	docker compose up --build

down:
	docker compose down
