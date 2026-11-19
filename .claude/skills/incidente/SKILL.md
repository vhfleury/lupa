---
name: incidente
description: Conduz o diagnóstico de uma falha do Lupa (autos que não entram, fila parada, peça mal classificada, validação com resultado errado, chat sem citação, login falhando, contêiner que não sobe) até a causa e registra o post-mortem em docs/incidentes/. Use quando o pedido for investigar, diagnosticar ou registrar um incidente.
---

# Incidente

## Passo a passo

| # | Ação | Entrada | Saída |
|---|---|---|---|
| 1 | Delimitar o sintoma | relato do usuário | o que falhou, desde quando, quais processos (por hash) ou telas |
| 2 | Localizar o caminho | `ingestao/worker.py` → `processamento.py` → etapa; ou tela → `src/lib` → rota → view `v_*`; ou `validacoes/motor.py` → validação | caminho de execução |
| 3 | Ler o log | `docker compose logs --tail 200 <serviço>` (JSON estruturado) | exceção, módulo e horário |
| 4 | Estado no banco, se o usuário pedir | `v_fila_ingestao`, eventos, `alembic_version` via `especialista-banco` | etapa e estado afetados |
| 5 | Cruzar com mudanças | `git log --since=<início> -- <arquivos do caminho>` | commit candidato |
| 6 | Especialista da área em diagnóstico | ingestão, validações, intranet, infra ou banco | causa provável com evidência |
| 7 | Confirmar a causa | teste que reproduz, pelo agente `tdd`, com dado sintético | causa confirmada ou hipótese |
| 8 | Propor a correção | causa | correção e quem implementa; nada alterado sem pedido |
| 9 | Registrar | itens 1–8 | `docs/incidentes/AAAA-MM-DD-<tema>.md` e entrada em `docs/README.md` |

## Desvios

- Contêiner, rede ou proxy: `especialista-infra`.
- Banco lento, sem espaço ou lock preso: `especialista-banco` com `saude-banco`, a pedido do
  usuário.
- Causa não confirmada: o post-mortem registra a hipótese e a evidência que falta.
- Procedimento de resposta: seção "Incidentes" de `docs/operacao/operacao.md`.

## Regras

- Sem correção no mesmo passo do diagnóstico: a correção segue branch, teste que reproduz o bug,
  PR.
- Post-mortem sem narrativa: data, sintoma, causa, correção e pendências.
- Sem conteúdo de autos, nome de parte ou número de processo no post-mortem nem no chat.
