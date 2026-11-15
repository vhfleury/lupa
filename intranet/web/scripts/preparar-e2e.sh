# Preparo comum de e2e.sh e capturas.sh. Cada execução ganha um projeto Compose vazio.
# A API e o worker usam PostgreSQL, MinIO e Vault desse projeto. O navegador usa o proxy interno.
limpar_e2e() {
  local codigo=$?
  trap - EXIT INT TERM
  docker compose down --volumes --remove-orphans >&2 || codigo=1
  rm -f -- "$LUPA_ENV_ARQUIVO" "$LUPA_VAULT_DEV_DIR/init.json"
  rmdir "$LUPA_VAULT_DEV_DIR" 2>/dev/null || true
  rmdir "$LUPA_E2E_TEMP" || codigo=1
  exit "$codigo"
}

preparar_e2e() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
  local py="${PYTHON:-python}" credenciais processos chat
  command -v "$py" >/dev/null 2>&1 || py=python3
  umask 077
  LUPA_E2E_TEMP="$(mktemp -d "${TMPDIR:-/tmp}/lupa-e2e.XXXXXXXX")"
  LUPA_ENV_ARQUIVO="$LUPA_E2E_TEMP/stack.env"
  LUPA_VAULT_DEV_DIR="$LUPA_E2E_TEMP/cofre"
  LUPA_E2E_ENV="$LUPA_ENV_ARQUIVO"
  if command -v cygpath >/dev/null 2>&1; then LUPA_E2E_ENV="$(cygpath -m "$LUPA_ENV_ARQUIVO")"; fi
  export LUPA_ENV_ARQUIVO LUPA_VAULT_DEV_DIR LUPA_E2E_ENV
  COMPOSE_PROJECT_NAME="lupa-e2e-$("$py" -c 'import secrets; print(secrets.token_hex(6))')"
  export COMPOSE_PROJECT_NAME
  echo "E2E no projeto $COMPOSE_PROJECT_NAME" >&2
  export COMPOSE_PATH_SEPARATOR='|' COMPOSE_FILE='docker-compose.yml|intranet/web/e2e/compose.yaml'
  export COMPOSE_ENV_FILES="$LUPA_E2E_ENV"
  export LUPA_AGENTE_CLIENTE=falso
  "$py" - "$LUPA_ENV_ARQUIVO" <<'PY'
import secrets
import sys
from pathlib import Path

template = Path(".env.example").read_text(encoding="utf-8").splitlines()
valores = {k: secrets.token_hex(24) for k in (
    "POSTGRES_PASSWORD", "LUPA_DB_SENHA_APP", "LUPA_MINIO_SECRET_KEY", "LUPA_DESEMBARGADOR_SENHA"
)}
valores["LUPA_AMBIENTE"] = "teste"
linhas = [linha for linha in template if linha.split("=", 1)[0] not in valores]
linhas.extend(f"{k}={v}" for k, v in valores.items())
Path(sys.argv[1]).write_text("\n".join(linhas) + "\n", encoding="utf-8")
PY
  trap limpar_e2e EXIT
  trap 'exit 130' INT TERM
  docker compose config --quiet
  docker compose --profile e2e build api worker front e2e
  docker compose up -d db vault minio minio-init
  # O Vault novo começa selado. Aguarde a resposta de status antes do init/unseal.
  local pronto=0
  for _ in {1..30}; do
    if docker compose exec -T vault vault status -format=json >/dev/null 2>&1; then pronto=1; break
    elif [ "$?" = 2 ]; then pronto=1; break
    fi
    sleep 1
  done
  [ "$pronto" = 1 ] || { echo "Vault do E2E indisponível" >&2; return 1; }
  bash scripts/vault_inicializar.sh
  # O script de migração usa o dono do banco. Os serviços passam a usar lupa_app.
  docker compose run --rm -T api alembic -c pipeline/src/lupa_pipeline/migrations/alembic.ini upgrade head
  docker compose run --rm --no-deps -T api python intranet/api/scripts/criar_usuario_banco.py
  REDE_BORDA_SUBREDE="$(docker network inspect "${COMPOSE_PROJECT_NAME}_borda" --format '{{(index .IPAM.Config 0).Subnet}}')"
  export REDE_BORDA_SUBREDE
  docker compose up -d --wait api worker front proxy

  credenciais="$(docker compose exec -T api python intranet/api/scripts/e2e_preparar.py)"
  LUPA_E2E_DES_USUARIO="$(printf '%s\n' "$credenciais" | sed -n 1p)"
  LUPA_E2E_DES_SENHA="$(printf '%s\n' "$credenciais" | sed -n 2p)"
  export LUPA_E2E_DES_USUARIO LUPA_E2E_DES_SENHA
  if [ "${1:-}" = acesso ]; then return; fi
  processos="$(docker compose exec -T api python intranet/api/scripts/e2e_processos.py)"
  LUPA_E2E_PROC_USUARIO="$(printf '%s\n' "$processos" | sed -n 1p)"
  LUPA_E2E_PROC_SENHA="$(printf '%s\n' "$processos" | sed -n 2p)"
  LUPA_E2E_PROC_ID="$(printf '%s\n' "$processos" | sed -n 3p)"
  export LUPA_E2E_PROC_USUARIO LUPA_E2E_PROC_SENHA LUPA_E2E_PROC_ID
  chat="$(docker compose exec -T api python intranet/api/scripts/e2e_semear_chat.py)"
  LUPA_E2E_CHAT_PROCESSO="$(printf '%s\n' "$chat" | sed -n 1p)"
  LUPA_E2E_HOSTIL_PROCESSO="$(printf '%s\n' "$chat" | sed -n 2p)"
  export LUPA_E2E_CHAT_PROCESSO LUPA_E2E_HOSTIL_PROCESSO
}
