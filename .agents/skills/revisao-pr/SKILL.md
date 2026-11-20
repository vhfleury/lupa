---
name: revisao-pr
description: Revisa a branch de trabalho do Lupa antes do PR em ordem fixa — escopo, código Python, especialistas da área pelo caminho dos arquivos e validação (valida-pipeline/valida-intranet) — e consolida os achados. Use antes de abrir um PR ou quando o pedido for revisar a branch, o diff ou um PR.
---

# Revisão de PR

## Passo a passo

| # | Ação | Entrada | Saída |
|---|---|---|---|
| 1 | Levantar o diff | `git diff develop...HEAD --stat` + working tree | arquivos alterados |
| 2 | Escopo | `revisor-escopo` com tarefa, requisito, arquivos esperados, plano e base `develop` | desvios |
| 3 | Código Python | `revisor-codigo` (defeitos) e `pep8-clean-code` (estilo), só revisão | achados |
| 4 | Mapear especialistas | tabela abaixo | lista |
| 5 | Especialistas | cada um em modo `revisao`, em paralelo | APROVADO, COM CONDIÇÕES ou VETADO |
| 6 | Validação | `/valida-pipeline` se tocou `pipeline/`; `/valida-intranet` se tocou `intranet/` | gates |
| 7 | Consolidar | saídas 2–6 | relatório |

## Especialista por caminho

| Caminho | Agente |
|---|---|
| `pipeline/src/lupa_pipeline/ingestao/`, `sinteticos/` | especialista-ingestao |
| `pipeline/src/lupa_pipeline/validacoes/` | especialista-validacoes |
| `pipeline/src/lupa_pipeline/dominio/`, `migrations/` | especialista-banco (só leitura do código) |
| `intranet/api/`, `intranet/web/` | especialista-intranet |
| `docker-compose*.yml`, `Dockerfile`, `intranet/proxy/`, `requirements*.txt`, `pyproject.toml`, `Makefile`, `scripts/` | especialista-infra |
| módulo novo, movido ou dividido | arquiteto |

## Desvios

- Arquivo fora do escopo no passo 2: parar e mostrar ao usuário.
- Nenhum `.py` alterado: pular o passo 3.
- VETADO: o PR não é aberto; mostrar veto e condições. Só o usuário derruba.
- Gate falhando: o PR não é aberto.

## Relatório

- Veredito geral: pronto para PR ou bloqueado (motivo).
- Achados por severidade, com `arquivo:linha` e origem.
- Condições dos especialistas.
- Validações executadas e as que não rodaram.

## Regras

- A revisão não altera código.
- PR para `develop`, citando a tarefa, só com relatório sem bloqueio.
