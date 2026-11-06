.PHONY: up down test lint typecheck format migrate verificar lock

UV_COMPILE = uv pip compile pyproject.toml --generate-hashes --python-version 3.12 \
	--python-platform x86_64-manylinux_2_28 --custom-compile-command "make lock"

up:
	docker compose up -d --build --wait

down:
	docker compose down

test:
	docker compose exec api python -m pytest

lint:
	docker compose exec api python -m ruff check src tests

typecheck:
	docker compose exec api python -m mypy src tests

format:
	python -m ruff format src tests
	python -m ruff check --fix src tests

migrate:
	docker compose exec api alembic upgrade head

verificar:
	docker compose exec api bash scripts/verificar.sh

lock:
	$(UV_COMPILE) -o requirements.txt
	$(UV_COMPILE) --extra dev -c requirements.txt -o requirements-dev.txt
