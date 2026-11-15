#!/usr/bin/env bash
# Roda os testes ponta a ponta do front (Playwright) contra a stack real do compose.
# O preparo (stack e contas sintéticas, remoção dos volumes de teste ao sair) fica em preparar-e2e.sh.
# Uso: bash intranet/web/scripts/e2e.sh [argumentos do playwright]
set -euo pipefail
source "$(dirname "$0")/preparar-e2e.sh"

if [ "$#" = 1 ] && [ "$1" = --project=acesso ]; then
  preparar_e2e acesso
else
  preparar_e2e
fi
docker compose --profile e2e run --rm -T e2e npx playwright test "$@"
