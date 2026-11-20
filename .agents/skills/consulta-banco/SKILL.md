---
name: consulta-banco
description: Consulta o PostgreSQL do Lupa (serviço db do docker-compose) em sessão somente leitura, sem efeito colateral. Use para qualquer checagem pontual de dados ou de estrutura no banco, sempre a pedido do usuário.
---

# Consulta ao banco (somente leitura)

Pedido: $ARGUMENTS

## Quem executa

- Toda consulta é feita pelo agente `especialista-banco`. Fora dele, não conecte: chame o agente
  com o pedido e a frase do usuário que autorizou a consulta.
- Sem pedido do usuário, não há consulta.

## Conexão

Dentro do contêiner do Postgres, com as variáveis do próprio contêiner (sem ler o `.env`):

```bash
docker compose exec -T db sh -c 'PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=15s -c lock_timeout=2s" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -X -A -F " | " -c "<SELECT ...>"'
```

## Passo a passo

| # | Ação | Saída |
|---|---|---|
| 1 | `docker compose ps db` para conferir que o serviço está saudável | serviço ativo |
| 2 | Conferir nome e colunas do objeto em `docs/sistema/modelo-de-dados.md`, `dominio/tabelas.py`, `dominio/visoes.py` ou `information_schema.columns` | colunas confirmadas |
| 3 | Executar só `SELECT`/`WITH`/`EXPLAIN`/`SHOW` com colunas nomeadas e `LIMIT`, de preferência sobre as views `v_*` | linhas |
| 4 | Reportar a query executada e o resultado resumido | resposta |

## Regras

- Sem `SELECT *`; sem `INSERT`, `UPDATE`, `DELETE` ou DDL.
- Migration só por `alembic ... upgrade head` no contêiner `api`, pelo `especialista-banco`
  (seção "Aplicação de migration" do agente).
- Retorno só com contagens, estados e hashes: nunca conteúdo de peça, nome de parte, número de
  processo, texto de pergunta ou de resposta do chat.
