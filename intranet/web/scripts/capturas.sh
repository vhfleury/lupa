#!/usr/bin/env bash
# Capturas de tela dos guias (docs/imagens/*.png) sobre os processos SINTETICOS, numa stack nova
# com o mesmo preparo do e2e.sh (preparar-e2e.sh). Roda intranet/web/tests/e2e/test_capturas.py:
# os PNGs vao direto para docs/imagens por bind mount. Com LUPA_CAPTURAS_VISUAL=<pasta do host>,
# grava tambem cada tela nos temas claro e escuro e em 375 px nessa pasta.
# Uso: bash intranet/web/scripts/capturas.sh [argumentos do pytest]
set -euo pipefail
source "$(dirname "$0")/preparar-e2e.sh"

caminho_docker() {
  mkdir -p "$1"
  (cd "$1" && (pwd -W 2>/dev/null || pwd))
}

preparar_e2e
montagens=(-v "$(caminho_docker docs/imagens):/capturas" -e LUPA_CAPTURAS_DIR=/capturas)
if [ -n "${LUPA_CAPTURAS_VISUAL:-}" ]; then
  montagens+=(-v "$(caminho_docker "$LUPA_CAPTURAS_VISUAL"):/visual" -e LUPA_CAPTURAS_VISUAL=/visual)
fi
# Git Bash no Windows: caminho do host no formato do Docker e sem conversao MSYS.
MSYS_NO_PATHCONV=1 docker compose --profile e2e run --rm -T --user "0:0" "${montagens[@]}" \
  e2e python -m pytest -c intranet/web/pyproject.toml intranet/web/tests/e2e/test_capturas.py \
  -m e2e --no-cov "$@"
ls -l docs/imagens
