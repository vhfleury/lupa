#!/usr/bin/env bash
# Etapa 7.9: capturas de tela reais dos guias (docs/imagens/*.png) com Playwright, sobre os
# processos SINTETICOS do E2E. Mesmo preparo do e2e.sh (preparar-e2e.sh); no fim roda o
# projeto "capturas" (intranet/web/e2e/capturas.config.ts), que cadastra o MFA e retrata os autos. Os PNGs vao direto para docs/imagens por bind mount (nada copiado do conteiner).
# Uso: bash intranet/web/scripts/capturas.sh
set -euo pipefail
source "$(dirname "$0")/preparar-e2e.sh"

preparar_e2e
mkdir -p docs/imagens
# Git Bash no Windows: caminho do host no formato do Docker e sem conversao MSYS.
origem="$(pwd -W 2>/dev/null || pwd)/docs/imagens"
MSYS_NO_PATHCONV=1 docker compose --profile e2e run --rm -T --user "0:0" \
  -e LUPA_CAPTURAS_DIR=/capturas \
  -v "$origem:/capturas" \
  e2e npx playwright test -c capturas.config.ts --project=capturas "$@"
ls -l docs/imagens
