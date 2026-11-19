---
name: valida-intranet
description: Executa a validação obrigatória da intranet do Lupa (API em intranet/api e front em intranet/web) — ruff, formatação, mypy e pytest no contêiner api; lint, svelte-check e Vitest no front; rebuild e conferência no navegador. Use antes de concluir qualquer tarefa que altere intranet/.
---

# Validação da intranet

## Passo a passo

| # | Ação | Comando | Falha quando |
|---|---|---|---|
| 1 | Listar alterações | `git status --porcelain` e `git diff --stat develop...HEAD` | arquivo fora do escopo |
| 2 | Dependências | conferir o diff | pacote npm ou Python novo sem pedido; `requirements*.txt` fora de `make lock` |
| 3 | Rebuild | `docker compose up -d --build --wait` | serviço não sobe |
| 4 | Lint e formatação da API | `docker compose exec api ruff check intranet/api/src intranet/api/tests` e `ruff format --check` nos mesmos | qualquer achado |
| 5 | Tipagem da API | `docker compose exec api mypy --config-file intranet/api/pyproject.toml intranet/api/src intranet/api/tests` | erro |
| 6 | Testes da API | `docker compose exec api python -m pytest -c intranet/api/pyproject.toml intranet/api/tests` | falha, skip de integração ou cobertura < 90% |
| 7 | Front | `docker build --target verificacao intranet/web` (ou `npm run verificar` em `intranet/web/`) | aviso ou falha |
| 8 | Navegador | abrir `https://localhost:8443` na tela alterada, com conta sintética; console sem erro | erro ou seção sumida |
| 9 | E2E | `bash intranet/web/scripts/e2e.sh`, se o fluxo alterado é coberto pelo E2E | falha |
| 10 | Completo | `bash scripts/verificar.sh`, se tocou agente, segurança ou proxy | falha |
| 11 | Relatório | requisito, comandos e saída resumida | — |

## Regras

- Testes do agente com o cliente roteirizado; chamada real ao modelo (`llm`) fica fora e entra em
  "revisão manual".
- Componente Svelte só de apresentação e fluxo E2E entram em "revisão manual" quando não testados.
- O que não puder ser executado entra no relatório como não validado.
