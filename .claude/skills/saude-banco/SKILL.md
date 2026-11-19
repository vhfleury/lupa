---
name: saude-banco
description: Estado do PostgreSQL do Lupa (serviço db) — disponibilidade, reinícios, conexões, bloqueios e advisory locks, tamanho, autovacuum, revisão Alembic aplicada e estado da fila de ingestão —, entregue em texto curto. Executada pelo agente especialista-banco. Use quando o pedido for "como está o banco", lentidão, espaço em disco ou "a fila andou?".
argument-hint: "[foco, ex.: tamanho do volume ou fila de ingestão]"
---

# Saúde do banco

Pedido: $ARGUMENTS

## Quem executa

O `especialista-banco` carrega esta skill e faz a coleta. Fora dele: chame o agente com "saúde do
banco" e o foco pedido.

## Coleta

| # | Verificação | Fonte |
|---|---|---|
| 1 | Contêiner ativo e saudável, reinícios | `docker compose ps db`, `docker inspect -f '{{.RestartCount}} {{.State.StartedAt}}' $(docker compose ps -q db)` |
| 2 | Erros recentes | `docker compose logs --tail 200 db` filtrado por `FATAL`, `ERROR`, `PANIC` |
| 3 | Versão e início do servidor | `version()`, `pg_postmaster_start_time()` |
| 4 | Conexões por estado e usuário; `idle in transaction` antigas | `pg_stat_activity` |
| 5 | Bloqueios e advisory locks | `pg_blocking_pids`, `pg_locks` com `locktype = 'advisory'` |
| 6 | Tamanho do banco e dos 10 maiores objetos (hubs, links, satélites) | `pg_database_size`, `pg_total_relation_size` |
| 7 | Autovacuum e tuplas mortas estimadas | `pg_stat_user_tables` |
| 8 | Revisão aplicada × arquivos em `migrations/versions/` | `alembic_version` e `ls` |
| 9 | Fila de ingestão: itens por estado e idade do mais antigo | `v_fila_ingestao` |
| 10 | Espaço do volume | `docker system df -v` (linha de `db-dados`) |

Toda consulta pela receita de `.claude/skills/consulta-banco/SKILL.md`.

## Retorno

1. Primeira frase: estado (`saudável no escopo verificado`, `atenção`, `crítico`, `inconclusivo`)
   e horário da coleta.
2. Lista curta: pontos de atenção, revisão pendente, fila parada ou lock antigo.
3. Tabela `Verificação | Resultado | Gravidade`.
4. Recomendações separadas do que foi executado (nada é alterado).
5. Limites da coleta.
