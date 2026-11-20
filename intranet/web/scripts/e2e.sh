#!/usr/bin/env bash
# Roda a suite ponta a ponta do front (pytest-playwright, marcador e2e) contra a stack real do
# compose, num projeto temporario com contas e processos sinteticos e o cliente falso do agente.
# O preparo (stack, contas, remocao dos volumes ao sair) fica em preparar-e2e.sh. As capturas dos
# guias ficam no capturas.sh, que precisa de uma stack sem os efeitos destes fluxos.
# Uso: bash intranet/web/scripts/e2e.sh [argumentos do pytest]
set -euo pipefail
source "$(dirname "$0")/preparar-e2e.sh"

preparar_e2e
docker compose --profile e2e run --rm -T e2e python -m pytest -c intranet/web/pyproject.toml \
  intranet/web/tests/e2e -m e2e --no-cov --ignore=intranet/web/tests/e2e/test_capturas.py "$@"
