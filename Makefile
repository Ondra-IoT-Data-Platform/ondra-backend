# Makefile configuration

.PHONY: run app

MANAGE := uv run python app/manage.py
DOCKER-RUN = docker compose exec app python app/manage.py
name = ""
run:
	$(MANAGE) runserver

migrations:
	$(MANAGE) makemigrations

migrate:
	$(MANAGE) migrate

superuser:
	$(MANAGE) createsuperuser

shell:
	$(MANAGE) shell

showmigrations:
	$(MANAGE) showmigrations

test:
	uv run pytest

lint:
	uv run ruff check . --fix
	uv run mypy .

app:
	$(MANAGE) startapp $(name) app/$(name)


# Docker commands
up:
	docker compose up

down:
	docker compose down

down-all:
	docker compose down --volumes

build:
	docker compose build

build-no-cache:
	docker compose build --no-cache

build-up:
	docker compose up --build

app-run:
	$(DOCKER-RUN) runserver

app-shell:
	$(DOCKER-RUN) shell

app-migrations:
	$(DOCKER-RUN) makemigrations

app-migrate:
	$(DOCKER-RUN) migrate

app-showmigrations:
	$(DOCKER-RUN) showmigrations

app-superuser:
	$(DOCKER-RUN) createsuperuser

makemigrations:
	docker compose run --rm --entrypoint "" app python manage.py makemigrations

makemigrate:
	docker compose run --rm --entrypoint "" app python manage.py migrate

app-test:
	docker compose exec app pytest

format:
	uv run ruff format .

pre-commit-all:
	uv run pre-commit run --all-files

pre-commit:
	uv run pre-commit run

pre-commit-install:
	uv run pre-commit install

# ---- Maintenance -----
install:
	uv sync --all-extras --dev

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

help:
	@echo "Available commands:"
	@echo "  run             - Start the development server"
	@echo "  makemigrations  - Create new migrations based on model changes"
	@echo "  migrate         - Apply database migrations"
	@echo "  createsuperuser - Create a new superuser account"
	@echo "  shell           - Open the Django shell"
	@echo "  test            - Run tests using pytest"
	@echo "  lint            - Run linters (ruff and mypy)"
	@echo "  format          - Format code using ruff"
	@echo "  install         - Install dependencies using uv"
	@echo "  clean           - Remove cache files"
	@echo "  help            - Show this help message"
	@echo "  pre-commit-all  - Run all pre-commit hooks"
	@echo "  pre-commit      - Run pre-commit hooks"
	@echo "  pre-commit-install - Install pre-commit hooks"
