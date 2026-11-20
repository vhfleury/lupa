# syntax=docker/dockerfile:1
# Testes ponta a ponta do front (0.2, plano_front_django D5, D6): pytest-playwright com Chromium,
# contra a stack real pelo proxy. Dependencias do dev de lupa_web, com hashes; usuario nao root.
# Base bookworm: o Playwright 1.49 so instala as dependencias do Chromium ate o Debian 12.
# Contexto: raiz do repositorio.
FROM python:3.12-slim-bookworm
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH" PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONPATH=/app/intranet/web/src DJANGO_SETTINGS_MODULE=lupa_web.configuracao \
    LUPA_WEB_CHAVE_SECRETA=e2e PYTEST_ADDOPTS="-p no:cacheprovider"
RUN python -m venv /opt/venv
COPY intranet/web/requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install --require-hashes -r /tmp/requirements-dev.txt \
    && playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/* /tmp/requirements-dev.txt
RUN groupadd --system --gid 10001 lupa && useradd --system --uid 10001 --gid lupa --create-home lupa
WORKDIR /app
COPY --chown=lupa:lupa intranet/web/pyproject.toml ./intranet/web/pyproject.toml
COPY --chown=lupa:lupa intranet/web/src ./intranet/web/src
COPY --chown=lupa:lupa intranet/web/tests ./intranet/web/tests
USER lupa
CMD ["python", "-m", "pytest", "-c", "intranet/web/pyproject.toml", "intranet/web/tests/e2e", "-m", "e2e", "--no-cov"]
