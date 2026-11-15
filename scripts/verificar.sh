#!/usr/bin/env bash
# Roda lint, tipagem e testes dos dois pacotes em sequencia; falha no primeiro erro.
# Roda no host, com a stack de pe (`docker compose up -d --build --wait`): a pipeline e verificada
# na imagem do `worker` e a intranet na da `api` (D21), ambas com /app como diretorio de trabalho.
set -euo pipefail
cd "$(dirname "$0")/.."
PIPELINE=(docker compose exec -T -e LUPA_EXIGIR_INTEGRACAO=1 worker python)
INTRANET=(docker compose exec -T -e LUPA_EXIGIR_INTEGRACAO=1 api python)
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
# Etapa 6: lint, typecheck e testes unitarios do front, sempre em conteiner: reconstroi o estagio
# `verificacao` da imagem do front.
echo "== front =="
docker build --target verificacao -q intranet/web >/dev/null
echo "front: lint, typecheck e testes ok (build da imagem)"
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
# Etapa 6.10: suite E2E (Playwright), opcional. Ative com LUPA_VERIFICAR_E2E=1; o e2e.sh sobe a
# stack isolada com o cliente falso e, ao terminar, remove o ambiente sintético.
if [ "${LUPA_VERIFICAR_E2E:-0}" = "1" ]; then
  echo "== e2e =="
  bash intranet/web/scripts/e2e.sh
else
  echo "== e2e == (pulado; defina LUPA_VERIFICAR_E2E=1 para rodar a suite Playwright)"
fi
