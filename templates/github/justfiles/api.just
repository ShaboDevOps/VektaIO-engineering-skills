# VektaIO API (FastAPI). CI runs `just ci`; PRs to main also run `just release-check`.
set dotenv-load := true

setup:
    uv sync
    uv run pre-commit install

dev:
    uv run fastapi dev app/main.py

worker:
    uv run celery -A app.workers.celery_app worker -l info

format:
    uv run ruff format .
    uv run ruff check --fix .

lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run lint-imports

typecheck:
    uv run mypy --strict -n auto app

test:
    uv run pytest -n auto --cov=app --cov-fail-under=85

migrate:
    uv run alembic upgrade head

makemigration name:
    uv run alembic revision --autogenerate -m "{{name}}"

seed:
    uv run python -m scripts.seed

loadtest:
    uv run locust -f load_tests/locustfile.py

gen:
    uv run python -m scripts.export_openapi

# Everything CI checks on every PR
ci:
    just lint
    just typecheck
    uv run python scripts/check_migrations.py
    just migrate
    just test

# Release gate (PRs into main): fresh-DB migrations up/down + OpenAPI breaking-change check
release-check:
    just migrate
    uv run alembic downgrade -1
    just migrate
    uv run python -m scripts.export_openapi
    @echo "Compare openapi.json against the last release tag (e.g. with oasdiff) — see engineering-workflow"

deploy env:
    @echo "TODO: deploy to {{env}} (build image tagged with version + SHA, run migration job, roll out)"; exit 1
