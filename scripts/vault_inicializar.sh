#!/usr/bin/env bash
# Inicializa o Vault do compose (Etapa 7.2), so no modo de desenvolvimento. Idempotente: pode rodar a
# cada subida (o Vault volta selado depois de reiniciar).
#
#  1. `vault operator init` (1 parte, limiar 1) na primeira vez; a chave de unseal e o token raiz
#     ficam em .vault-dev/init.json (fora do repositorio, modo 600);
#  2. unseal automatico com essa chave;
#  3. habilita o Transit e o AppRole, cria a chave de verificacao `lupa-saude` (GET /saude) e a
#     chave unica `lupa` (DEKs dos processos), grava a politica minima (vault/politicas/lupa.hcl)
#     e o papel `lupa` (token de 1 h);
#  4. gera um secret_id novo e grava LUPA_COFRE_BACKEND, LUPA_VAULT_ROLE_ID e LUPA_VAULT_SECRET_ID
#     so no .env (nunca no .env.example nem em arquivo versionado).
#
# Opcoes: --so-unseal (so destrava, sem secret_id novo).
# Depois: `docker compose up -d api worker` para a API e o worker lerem o .env novo.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python}"
command -v "$PY" >/dev/null 2>&1 || PY=python3
DIR=.vault-dev
INIT="$DIR/init.json"
ENV_ARQ="${LUPA_ENV_ARQUIVO:-.env}"
SO_UNSEAL=0
if [ "${1:-}" = "--so-unseal" ]; then SO_UNSEAL=1; fi
vault_cmd() { docker compose exec -T "$@"; }
json() { "$PY" -c "import json,sys; print(json.load(sys.stdin)$1)"; }
estado_campo() { vault_cmd vault vault status -format=json 2>/dev/null | json "['$1']" || true; }

estado=$(vault_cmd vault vault status -format=json || true)
inicializado=$(printf '%s' "$estado" | json "['initialized']")
if [ "$inicializado" != "True" ]; then
  mkdir -p "$DIR" && chmod 700 "$DIR"
  vault_cmd vault vault operator init -key-shares=1 -key-threshold=1 -format=json > "$INIT"
  chmod 600 "$INIT"
  echo "vault: inicializado (chave de unseal e token raiz em $INIT)"
fi
[ -f "$INIT" ] || { echo "vault ja inicializado mas $INIT nao existe" >&2; exit 1; }
CHAVE=$(json "['unseal_keys_b64'][0]" < "$INIT")
RAIZ=$(json "['root_token']" < "$INIT")
if [ "$(estado_campo sealed)" = "True" ]; then
  vault_cmd vault vault operator unseal "$CHAVE" >/dev/null
  echo "vault: unseal ok"
fi
if [ "$SO_UNSEAL" = "1" ]; then exit 0; fi

com_raiz() { docker compose exec -T -e VAULT_TOKEN="$RAIZ" vault vault "$@"; }
com_raiz secrets list -format=json | grep -q '"transit/"' || com_raiz secrets enable transit >/dev/null
com_raiz auth list -format=json | grep -q '"approle/"' || com_raiz auth enable approle >/dev/null
# Etapa 8.1: chave de verificacao do GET /saude (componente `cofre`).
com_raiz list -format=json transit/keys 2>/dev/null | grep -q '"lupa-saude"' ||
  com_raiz write -f transit/keys/lupa-saude >/dev/null
# Versao 0.2 (D14): chave unica `lupa`, que envolve a DEK de cada processo.
com_raiz list -format=json transit/keys 2>/dev/null | grep -q '"lupa"' ||
  com_raiz write -f transit/keys/lupa >/dev/null
com_raiz policy write lupa - < vault/politicas/lupa.hcl >/dev/null
com_raiz write auth/approle/role/lupa token_policies=lupa token_ttl=1h token_max_ttl=4h \
  secret_id_ttl=0 >/dev/null
ROLE_ID=$(com_raiz read -format=json auth/approle/role/lupa/role-id | json "['data']['role_id']")
SECRET_ID=$(com_raiz write -format=json -f auth/approle/role/lupa/secret-id | json "['data']['secret_id']")

"$PY" - "$ENV_ARQ" "$ROLE_ID" "$SECRET_ID" <<'PYEOF'
import sys
from pathlib import Path

caminho, role_id, secret_id = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
novos = {
    "LUPA_COFRE_BACKEND": "vault",
    "LUPA_VAULT_ROLE_ID": role_id,
    "LUPA_VAULT_SECRET_ID": secret_id,
}
linhas = caminho.read_text(encoding="utf-8").splitlines() if caminho.exists() else []
saida = [l for l in linhas if l.split("=", 1)[0].strip() not in novos]
saida += [f"{chave}={valor}" for chave, valor in novos.items()]
caminho.write_bytes(("\n".join(saida) + "\n").encode("utf-8"))
PYEOF
echo "vault: Transit, chaves lupa-saude e lupa, politica 'lupa' e AppRole prontos; role_id/secret_id gravados em $ENV_ARQ"
echo "rode: docker compose up -d api worker"
