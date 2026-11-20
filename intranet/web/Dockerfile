# syntax=docker/dockerfile:1
# Front do Lupa em Django (D1, D6): uvicorn, usuario nao root; a imagem tambem roda os testes de
# lupa_web (dependencias de dev com INSTALAR_DEV=true). Contexto: raiz do repositorio.
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY intranet/web/requirements.txt intranet/web/requirements-dev.txt ./
RUN pip install --require-hashes -r requirements.txt
ARG INSTALAR_DEV=false
RUN if [ "$INSTALAR_DEV" = "true" ]; then pip install --require-hashes -r requirements-dev.txt; fi

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/intranet/web/src DJANGO_SETTINGS_MODULE=lupa_web.configuracao \
    LUPA_WEB_ESTATICOS=/app/estaticos COVERAGE_FILE=/tmp/.coverage MYPY_CACHE_DIR=/tmp/mypy \
    RUFF_CACHE_DIR=/tmp/ruff PYTEST_ADDOPTS="-p no:cacheprovider"
RUN groupadd --system --gid 10001 lupa && useradd --system --uid 10001 --gid lupa --no-create-home lupa
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=lupa:lupa intranet/web/pyproject.toml ./intranet/web/pyproject.toml
COPY --chown=lupa:lupa intranet/web/src ./intranet/web/src
COPY --chown=lupa:lupa intranet/web/tests ./intranet/web/tests
RUN LUPA_WEB_CHAVE_SECRETA=coleta python -m django collectstatic --noinput -v 0 \
    && mkdir -p /var/lupa/envios-pendentes && chown lupa:lupa /var/lupa/envios-pendentes
USER lupa
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/saude', timeout=2).status == 200 else 1)"
CMD ["uvicorn", "lupa_web.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
