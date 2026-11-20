#!/usr/bin/env bash
# Roda lint, tipagem e testes dos tres pacotes Python em sequencia; falha no primeiro erro.
# Roda no host, com a stack de pe (`docker compose up -d --build --wait`): a pipeline e verificada
# na imagem do `worker`, a API na da `api` (D21) e o front na do `front`, todas com /app como diretorio de trabalho.
set -euo pipefail
cd "$(dirname "$0")/.."
PIPELINE=(docker compose exec -T -e LUPA_EXIGIR_INTEGRACAO=1 worker python)
INTRANET=(docker compose exec -T -e LUPA_EXIGIR_INTEGRACAO=1 api python)
WEB=(docker compose exec -T -e LUPA_EXIGIR_INTEGRACAO=1 front python)
echo "== pipeline: ruff check ==";          "${PIPELINE[@]}" -m ruff check pipeline/src pipeline/tests
echo "== pipeline: ruff format --check =="; "${PIPELINE[@]}" -m ruff format --check pipeline/src pipeline/tests
echo "== pipeline: mypy --strict ==";       "${PIPELINE[@]}" -m mypy --config-file pipeline/pyproject.toml pipeline/src pipeline/tests
echo "== pipeline: pytest ==";              "${PIPELINE[@]}" -m pytest -c pipeline/pyproject.toml pipeline/tests
echo "== intranet: ruff check ==";          "${INTRANET[@]}" -m ruff check intranet/api/src intranet/api/tests
echo "== intranet: ruff format --check =="; "${INTRANET[@]}" -m ruff format --check intranet/api/src intranet/api/tests
echo "== intranet: mypy --strict ==";       "${INTRANET[@]}" -m mypy --config-file intranet/api/pyproject.toml intranet/api/src intranet/api/tests
echo "== intranet: pytest ==";              "${INTRANET[@]}" -m pytest -c intranet/api/pyproject.toml intranet/api/tests
echo "== ponta a ponta da ingestao (integracao, sem skip) =="
docker compose exec -T -e LUPA_EXIGIR_INTEGRACAO=1 api python -m pytest -c intranet/api/pyproject.toml \
  -m integracao intranet/api/tests/ingestao/test_ponta_a_ponta.py --no-cov -q
echo "== regressao de injecao (corpus 4B.8, metas da 4D.5, sem skip) =="
METRICAS_INJECAO=/tmp/metricas_injecao.json
MSYS_NO_PATHCONV=1 docker compose exec -T -e LUPA_EXIGIR_INTEGRACAO=1 -e LUPA_METRICAS_INJECAO="$METRICAS_INJECAO" worker \
  python -m pytest -c pipeline/pyproject.toml -m injecao pipeline/tests/ingestao/test_injecao_corpus.py --no-cov -q
MSYS_NO_PATHCONV=1 "${PIPELINE[@]}" -c "import json,sys; m=json.load(open(sys.argv[1])); print({k: m[k] for k in ('versoes','recall','falso_positivo','injecoes_textuais','injecoes_detectadas','paginas_semente_01')})" "$METRICAS_INJECAO"
# 0.2 (plano_front_django, RNF-08): lint, tipagem e testes de lupa_web na imagem do `front`.
echo "== web: ruff check ==";               "${WEB[@]}" -m ruff check intranet/web/src intranet/web/tests
echo "== web: ruff format --check ==";      "${WEB[@]}" -m ruff format --check intranet/web/src intranet/web/tests
echo "== web: mypy --strict ==";            "${WEB[@]}" -m mypy --config-file intranet/web/pyproject.toml intranet/web/src intranet/web/tests
# T10.8: assessor sintetico novo para o envio do front a API real (test_envio_api_real.py).
# Usa o desembargador da stack; numa stack nova cria um sintetico de senha aleatoria (troca no
# primeiro acesso). As senhas so passam por variavel.
read -r LUPA_WEB_TESTE_USUARIO LUPA_WEB_TESTE_SENHA < <(docker compose exec -T api python - <<'PY'
import secrets
import sys
from contextlib import redirect_stdout
from datetime import UTC, datetime

sys.path.insert(0, "intranet/api/scripts")
from e2e_processos import desembargador, sessao_e2e
from lupa_api.acesso.instalacao import criar_desembargador_inicial
from lupa_api.acesso.servico import Contexto, criar_usuario
from lupa_pipeline.config import get_settings
from lupa_pipeline.dominio.enums import PapelUsuario

inicial = {
    "LUPA_DESEMBARGADOR_USUARIO": f"desembargador.verificar.{secrets.token_hex(3)}",
    "LUPA_DESEMBARGADOR_SENHA": secrets.token_urlsafe(18),
}
with redirect_stdout(sys.stderr):
    if criar_desembargador_inicial(get_settings(), inicial) != 0:
        sys.exit("desembargador sintetico nao criado")
with sessao_e2e() as sessao:
    nome = f"assessor.web.{secrets.token_hex(3)}"
    ctx = Contexto(None, None, datetime.now(UTC))
    criado = criar_usuario(sessao, desembargador(sessao), nome, PapelUsuario.ASSESSOR, ctx)
    print(nome, criado.senha_temporaria)
PY
)
export LUPA_WEB_TESTE_USUARIO LUPA_WEB_TESTE_SENHA
echo "== web: pytest ==";                   docker compose exec -T -e LUPA_EXIGIR_INTEGRACAO=1 \
  -e LUPA_WEB_TESTE_USUARIO -e LUPA_WEB_TESTE_SENHA front \
  python -m pytest -c intranet/web/pyproject.toml intranet/web/tests
# Etapa 6.10: cabecalhos de seguranca do proxy (CSP, HSTS, Permissions-Policy, COOP...). Falha se
# faltar algum ou se a CSP afrouxar; com o proxy fora do ar so avisa (LUPA_EXIGIR_CABECALHOS=1 exige).
echo "== cabecalhos de seguranca =="
"${INTRANET[@]}" intranet/api/scripts/verificar_cabecalhos.py --url "${LUPA_PROXY_URL:-https://proxy:8443}" ${LUPA_EXIGIR_CABECALHOS:+--exigir}
echo "== isolamento de rede do worker =="
"${PIPELINE[@]}" pipeline/scripts/verificar_rede.py
# Etapa 5.8: suite de injecao do agente sobre autos ingeridos (cliente falso roteirizado), sem skip.
echo "== suite de injecao do agente (Etapa 5.8, sem skip) =="
METRICAS_AGENTE=/tmp/metricas_agente.json
MSYS_NO_PATHCONV=1 docker compose exec -T -e LUPA_EXIGIR_INTEGRACAO=1 -e LUPA_METRICAS_AGENTE="$METRICAS_AGENTE" api \
  python -m pytest -c intranet/api/pyproject.toml -m agente intranet/api/tests/agente --no-cov -q
MSYS_NO_PATHCONV=1 "${INTRANET[@]}" -c "import json,sys; m=json.load(open(sys.argv[1])); print({k: m[k] for k in ('versao_modelo','versao_prompt','cenarios','achados_suprimidos','achados_criados','vazamentos','embutidas_executadas','respostas_bloqueadas')})" "$METRICAS_AGENTE"
# T10.15: suite E2E (pytest-playwright), opcional. Ative com LUPA_VERIFICAR_E2E=1; o e2e.sh sobe a
# stack isolada com o cliente falso e, ao terminar, remove o ambiente sintético.
if [ "${LUPA_VERIFICAR_E2E:-0}" = "1" ]; then
  echo "== e2e =="
  bash intranet/web/scripts/e2e.sh
else
  echo "== e2e == (pulado; defina LUPA_VERIFICAR_E2E=1 para rodar a suite pytest-playwright)"
fi
