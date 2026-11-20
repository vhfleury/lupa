---
name: valida-pipeline
description: Executa nos contêineres a validação obrigatória de pipeline/ (ruff, formatação, mypy, migrations, guarda de segredos e dados, suíte da pipeline e da intranet que a importa, verificar.sh quando exigido). Use antes de concluir qualquer tarefa que altere pipeline/.
---

# Validação da pipeline

## Passo a passo

| # | Ação | Comando | Falha quando |
|---|---|---|---|
| 1 | Listar alterações | `git status --porcelain` e `git diff --stat develop...HEAD` | arquivo fora do escopo |
| 2 | Migrations | filtrar o passo 1 por `pipeline/src/lupa_pipeline/migrations/` | revisão não prevista no plano, sem `downgrade`, sem teste com `migrar`, ou revisão já aplicada editada |
| 3 | Rebuild | `docker compose up -d --build --wait api worker` | serviço não sobe |
| 4 | Lint e formatação | `docker compose exec worker ruff check pipeline/src pipeline/tests` e `ruff format --check` nos mesmos | qualquer achado |
| 5 | Tipagem | `docker compose exec worker mypy --config-file pipeline/pyproject.toml pipeline/src pipeline/tests` | erro |
| 6 | Segredos e dados | Grep no diff por senha, token, chave, número CNJ que não venha de `gerar_numero_cnj`, CPF; arquivo de `dados/` versionado | qualquer achado |
| 7 | Suíte da pipeline | `docker compose exec worker python -m pytest -c pipeline/pyproject.toml pipeline/tests` | falha, skip ou cobertura < 90% |
| 8 | Testes novos sozinhos | mesmo comando com o arquivo e `--no-cov` | falha ou skip |
| 9 | Suíte da intranet | `docker compose exec api python -m pytest -c intranet/api/pyproject.toml intranet/api/tests` | falha |
| 10 | Completo | `bash scripts/verificar.sh`, se tocou ingestão, agente, segurança ou migrations | falha |
| 11 | PEP 8 e clean code | agente `pep8-clean-code` nos `.py` alterados | achado em trecho alterado |
| 12 | Relatório | requisito, comandos e saída resumida (vermelho inicial e verde final) | — |

Atalho para 4, 5, 7 e 9 juntos: `make lint typecheck test`.

## Regras

- Tudo no contêiner; o `.venv` local só para teste sem banco.
- Suíte não pôde rodar: ao menos `python -m compileall -q pipeline intranet/api`, e reportar como
  não validado.
- PostgreSQL ou MinIO indisponível: integração não validada, nunca pulada em silêncio.
