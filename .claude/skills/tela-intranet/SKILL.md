---
name: tela-intranet
description: Conduz a criação ou a atualização de uma tela da intranet do Lupa (Django com templates e HTMX em intranet/web) de ponta a ponta — escopo, mapeamento, inventário de dados com fonte real nas views v_* e rotas da API, mock renderizado no próprio front com dado sintético, iteração com o usuário, requisito/plano/tarefas, implementação em TDD e validação. Use sempre que o pedido for criar tela, redesenhar, reorganizar, "melhorar o layout", adicionar colunas, ações ou painéis, ou mudar o que uma tela mostra.
argument-hint: "[tela e o que mudar, ex.: /processos — mostrar o estado da ingestão sem abrir o processo]"
---

# Tela da intranet

Pedido: $ARGUMENTS

Orquestra `/ux-review`, `/analise-exploratoria`, `/spec`, `/plano`, `/tarefas`, o agente `tdd` e
`/valida-intranet`. As duas maiores fontes de retrabalho são desenhar com dado que não existe (ou
cujo significado foi presumido pelo nome do campo) e implementar antes de o usuário aprovar o
layout.

## Fases

| # | Fase | Saída | Quando pular |
|---|---|---|---|
| 0 | Escopo | tipo (nova / atualização / ajuste pontual), tela, papel que a usa, pergunta que ela responde | nunca |
| 1 | Mapeamento | rota de tela, `src/lib`, `api.ts`, rota da API, view `v_*`, componentes, permissões | — |
| 2 | Diagnóstico | layout atual e problemas por impacto | ajuste pontual |
| 3 | Inventário de dados | tabela dado → `v_view.coluna` / campo da rota → existe? → esforço | nunca |
| 4 | Mock | mock renderizado no próprio front com dado sintético | ajuste de 1 elemento |
| 5 | Iteração | layout aprovado pelo usuário | nunca, se houve mock |
| 6 | Requisito e plano | requisito na especificação (`/spec`) → aprovação → `/plano` → `/tarefas` | ajuste pontual sem mudança de requisito |
| 7 | Implementação | código + testes pelo agente `tdd` | — |
| 8 | Validação | `/valida-intranet` + navegador + relatório | nunca |

Não altere código de produção antes da fase 7 (o mock da fase 4 fica fora do commit até ser
aprovado). Ajuste pontual: 0, 1 e 3 enxutos, depois 7 e 8, fazendo ao pé da letra o que foi pedido.

## 1. Mapeamento

- Antes do código: requisitos da tela em `docs/especificacao/0.2/especificacao.md`,
  `docs/sistema/front.md` e `git status` para trabalho em andamento nos mesmos arquivos (não
  sobrescrever).
- Depois, com caminho real: tela em `intranet/web/src/routes/`, lógica em
  `intranet/web/src/lupa_web/telas/` e `templates/`, chamada em `cliente_api.py`, CSS em
  `static/css/`, rota em `intranet/api/src/lupa_api/`, view `v_*`,
  parciais compartilhados, testes em `intranet/web/tests/` e `intranet/api/tests/`, outras telas
  que usam as mesmas peças.

## 3. Inventário de dados

| Informação | `v_view.coluna` ou campo da rota | Significado confirmado em | Situação | Esforço |
|---|---|---|---|---|

- Significado confirmado em `docs/sistema/modelo-de-dados.md`, na view ou na rota, nunca pelo nome.
- Dado inexistente exige mudança na API ou no modelo: vira requisito e plano, e passa pelo
  `especialista-banco` (view) ou `especialista-validacoes` (resultado de validação).
- Regra jurídica nunca vai para o front nem para a rota.

## 4–5. Mock e iteração

- Mock renderizado no próprio front (template com dado sintético), aberto em
  `https://localhost:8443`, e aprovado pelo usuário antes do commit.
- Marcar no mock a origem de cada dado (campo existente × dado novo).
- Respeitar o tema (`tema.ts`, claro e escuro), componentes existentes e textos em português.
- Cada rodada: mudar só o que o usuário citou.

## 7–8. Implementação e validação

- Agente `tdd` com testes em `intranet/web/tests/` e, para a rota, em `intranet/api/tests/`.
- `especialista-intranet` em modo `revisao` antes do PR.
- `/valida-intranet`, rebuild e conferência no navegador; fluxo coberto pelo E2E roda
  `bash intranet/web/scripts/e2e.sh`.
