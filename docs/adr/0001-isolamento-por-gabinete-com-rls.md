# ADR 0001 — Isolamento por gabinete com RLS e `gabinete_id` desnormalizado

| Status | Data | Responsável |
| --- | --- | --- |
| Aceito | `{{data exata da decisão}}` (até 2026-10-22, data do primeiro commit) | Executor da Etapa 1; endossada na revisão 1 |

## Contexto

Cada gabinete só pode ver os próprios processos. A autorização é conferida no servidor pelo par (gabinete, processo). O banco precisa impor o mesmo limite, para que um erro de consulta não exponha outro gabinete.

## Restrições

- Superusuários e donos com `BYPASSRLS` ignoram RLS no PostgreSQL.
- Um filho não pode apontar para um pai de outro gabinete.

## Alternativas consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| Política de RLS com junção até `processo` | Encarece toda consulta. Com a coluna em cada tabela, a política filtra sem junções. |
| Aplicação conectada como dono das tabelas | O dono ignora RLS; o isolamento deixaria de valer. |

## Decisão

Toda tabela que pertence a um gabinete tem a coluna `gabinete_id`, `ENABLE` e `FORCE ROW LEVEL SECURITY` e a política `<tabela>_por_gabinete`, que compara com `current_setting('lupa.gabinete_id')`. FKs compostas `(x_id, gabinete_id)` garantem a consistência. A aplicação opera sob o papel `lupa_app` (`NOLOGIN`, só DML) e define o gabinete por transação.

## Consequências

- Sem a variável definida, nenhuma linha é visível.
- Tabela nova com `gabinete_id` nasce com RLS e entra em `TABELAS_COM_GABINETE`; um teste compara o conjunto com o banco.
- O `downgrade` não remove o papel `lupa_app`, que é global ao cluster.
- O usuário de conexão da API é criado por `scripts/criar_usuario_banco.py`; o dono das tabelas serve só a migrações e scripts.

## Fontes

- [decisoes/registro.md](../decisoes/registro.md), Etapa 1, itens 2 e 6
- [sistema/modelo-de-dados.md](../sistema/modelo-de-dados.md), "Row Level Security"
- `src/lupa/dominio/tabelas.py`
