.PHONY: up down logs backend-install backend-lint backend-test backend-migrate backend-seed

# --- Local stack (infra/docker-compose.yml — PLAN §8.4, §20.1) --------------
up:
	docker compose -f infra/docker-compose.yml up --build

down:
	docker compose -f infra/docker-compose.yml down -v

logs:
	docker compose -f infra/docker-compose.yml logs -f

# --- Backend dev shortcuts (backend/pyproject.toml, uv-managed venv) --------
backend-install:
	cd backend && uv venv --python 3.12 .venv && uv pip install -e ".[dev]" --python .venv/bin/python

backend-lint:
	cd backend && .venv/bin/ruff check app tests && .venv/bin/black --check app tests && .venv/bin/mypy app tests

backend-test:
	cd backend && .venv/bin/pytest

backend-migrate:
	cd backend && .venv/bin/alembic upgrade head

backend-seed:
	cd backend && .venv/bin/python -m app.db.seeds.run_seeds
