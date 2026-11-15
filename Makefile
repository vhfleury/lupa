.PHONY: up down test lint typecheck format migrate verificar lock

UV_COMPILE = uv pip compile --generate-hashes --python-version 3.12 \
	--python-platform x86_64-manylinux_2_28 --custom-compile-command "make lock"
PIPELINE = docker compose exec worker python -m
INTRANET = docker compose exec api python -m

up:
	docker compose up -d --build --wait

down:
	docker compose down

test:
	$(PIPELINE) pytest -c pipeline/pyproject.toml pipeline/tests
	$(INTRANET) pytest -c intranet/api/pyproject.toml intranet/api/tests

lint:
	$(PIPELINE) ruff check pipeline/src pipeline/tests
	$(INTRANET) ruff check intranet/api/src intranet/api/tests

typecheck:
	$(PIPELINE) mypy --config-file pipeline/pyproject.toml pipeline/src pipeline/tests
	$(INTRANET) mypy --config-file intranet/api/pyproject.toml intranet/api/src intranet/api/tests

format:
	python -m ruff format pipeline/src pipeline/tests intranet/api/src intranet/api/tests
	python -m ruff check --fix pipeline/src pipeline/tests intranet/api/src intranet/api/tests

migrate:
	docker compose exec api alembic -c pipeline/src/lupa_pipeline/migrations/alembic.ini upgrade head

verificar:
	bash scripts/verificar.sh

lock:
	$(UV_COMPILE) pipeline/pyproject.toml -o pipeline/requirements.txt
	$(UV_COMPILE) pipeline/pyproject.toml --extra dev -c pipeline/requirements.txt \
		-o pipeline/requirements-dev.txt
	$(UV_COMPILE) pipeline/pyproject.toml intranet/api/pyproject.toml \
		-o intranet/api/requirements.txt
	$(UV_COMPILE) pipeline/pyproject.toml intranet/api/pyproject.toml --extra dev \
		-c intranet/api/requirements.txt -o intranet/api/requirements-dev.txt
