#!/usr/bin/env bash
# Valida o intranet/proxy/Caddyfile (modo interno, unico) com `caddy validate` num conteiner
# descartavel da mesma imagem do proxy. Nada e gravado no host.
set -euo pipefail
cd "$(dirname "$0")/../../.."
export MSYS_NO_PATHCONV=1
IMAGEM=caddy:2.8.4-alpine
docker run --rm -v "$PWD/intranet/proxy:/etc/caddy:ro" \
  -e XDG_DATA_HOME=/tmp/d -e XDG_CONFIG_HOME=/tmp/c "$IMAGEM" sh -c '
    saida=$(caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1); rc=$?
    echo "$saida" | tail -n 1; exit $rc'
echo "caddy validate: ok"
