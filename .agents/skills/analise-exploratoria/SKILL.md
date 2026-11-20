---
name: analise-exploratoria
description: 'Análise exploratória de dados do Lupa (views v_* do Data Vault, saídas dos sintéticos e medições de extração): inventário, qualidade, distribuições, cruzamentos e hipóteses com as queries que as confirmariam, registrada em docs/analises/. Use quando o pedido for explorar, entender ou levantar números de um conjunto de dados, inclusive para sustentar um requisito da especificação.'
---

# Análise exploratória

Pedido: $ARGUMENTS

## Fontes

| Fonte | Como ler |
|---|---|
| Banco | receita de `.claude/skills/consulta-banco/SKILL.md`, pelo `especialista-banco`; o próprio pedido do usuário autoriza a consulta |
| Sintéticos e medições | `pipeline/scripts/medir.py`, `medir_extracao.py`, `calibrar.py` no contêiner `worker`; saída no scratchpad |

Nunca ler `dados/` (processos reais) nem copiar arquivo de autos para o repositório.

## Passo a passo

| # | Entrada | Ação | Saída |
|---|---|---|---|
| 1 | pedido | Fixar pergunta, fonte, período e grão (linha = o quê) | escopo em 1 linha |
| 2 | fonte | Inventário: colunas e tipos (`docs/sistema/modelo-de-dados.md`), contagem, `min`/`max` da data de carga, amostra de 10 linhas só com colunas técnicas | tabela |
| 3 | inventário | Qualidade: nulos, duplicatas pela chave de hash, estados inconsistentes, satélites sem hub | tabela |
| 4 | numéricas | Quantis p5–p95, média, mín., máx. | tabela |
| 5 | categóricas | Top 10 com participação e cauda | tabela |
| 6 | data | Série por dia ou mês da métrica principal; lacunas | tabela ou gráfico |
| 7 | pergunta | Até 3 cruzamentos | tabelas |
| 8 | tabelas | Leituras: o que os números mostram, sem causa | lista |
| 9 | leituras | Hipóteses com a query que confirma | tabela |
| 10 | tudo | Relatório em `docs/analises/AAAA-MM-DD-<tema>.md` e entrada em `docs/README.md` | arquivo |
| — | consulta passa do timeout | Reduzir período ou agregar no servidor | consulta ajustada |

## Regras

- Agregar no servidor; colunas nomeadas; `LIMIT` em toda amostra.
- No relatório, só agregados: sem conteúdo de peça, nome de parte, número de processo ou texto de
  pergunta.
- Scripts e resultados intermediários no scratchpad.

## Relatório

| Seção | Conteúdo |
|---|---|
| Escopo | pergunta, fonte, período, grão, linhas lidas |
| Inventário e qualidade | passos 2 e 3 |
| Distribuições | passos 4 a 6 |
| Cruzamentos | passo 7 |
| Leituras | um fato por linha |
| Hipóteses | `# \| Hipótese \| Query que confirma \| O que esperar` |
| Limitações | timeouts, colunas ignoradas, período incompleto |

Sem recomendação de ação; a decisão é do usuário. Os números citados por um requisito vêm daqui.
