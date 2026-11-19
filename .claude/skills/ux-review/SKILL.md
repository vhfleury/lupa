---
name: ux-review
description: Revisão de UX de uma tela da intranet do Lupa com evidência real no navegador; devolve pontos de melhoria priorizados por impacto e esforço, sem implementar. Use quando o pedido for avaliar, revisar ou melhorar a usabilidade de uma tela.
argument-hint: "[rota da tela, ex.: /processos]"
---

# Revisão de UX

Tela: $ARGUMENTS

Persona: designer de produto de ferramentas jurídicas internas, usadas por assessores e por um
desembargador que precisam conferir um processo rápido, achar a página de origem de cada
informação e não confundir apoio com decisão.

## Passo a passo

| # | Entrada | Ação | Saída |
|---|---|---|---|
| 1 | rota | Mapear tela (`routes/`), `src/lib/<assunto>`, `api.ts`, rota da API, view `v_*`, componentes | tabela |
| 2 | mapa | Ler os requisitos da tela na especificação da 0.2 e em `docs/sistema/front.md`; anotar o objetivo | objetivo em 1 frase |
| 3 | tela | Abrir no navegador (`https://localhost:8443`), logado com conta sintética do papel que usa a tela | tela carregada |
| 4 | tela | Medir pelo DOM (`javascript_tool`): altura, rolagem horizontal, largura das tabelas, ação principal acima da dobra, contraste; repetir a 375 px; console e rede | medidas |
| 5 | medidas | Teste dos 5 segundos: o estado do processo e a ação principal estão visíveis sem rolar? | leitura |
| 6 | medidas | Contradições: mesmo rótulo com valores diferentes, contagem do cabeçalho que discorda da lista, informação sem link para a página de origem | lista |
| 7 | medidas | Checklist abaixo, nota 0 a 2 | tabela |
| 8 | notas | 5 a 8 pontos de nota 0 ou 1 e maior impacto | lista |
| 9 | lista | Evidência, problema, proposta, arquivos, impacto, esforço | pontos |
| 10 | pontos | Ordenar por impacto × esforço | relatório |

## Checklist

| Grupo | Item | Nota 2 quando |
|---|---|---|
| Primeiro olhar | Informação principal | visível sem rolar |
| Primeiro olhar | Hierarquia | título → estado → detalhe |
| Primeiro olhar | Título | diz o que a tela responde |
| Leitura | Tabelas | sem rolagem horizontal; até 8 colunas |
| Leitura | Origem | toda informação extraída leva à página dos autos |
| Leitura | Apoio × decisão | resultado de validação lido como apoio, sem tom de decisão |
| Leitura | Formatação | datas `dd/mm/aaaa`, número CNJ formatado, números à direita |
| Leitura | Cor | cor de estado nunca é o único sinal |
| Navegação | Menu | item ativo destacado; papel vê só o que pode |
| Navegação | Consistência | mesmos componentes de `src/lib/componentes/` das outras telas |
| Estados | Vazio e carregando | diz o que aconteceu e o que fazer |
| Estados | Ingestão | estado da fila visível e atualizado |
| Acessibilidade | Contraste | 4.5:1 medido por CSS computado; tema escuro incluído |
| Responsivo | 375 px | sem rolagem horizontal |
| Erros | Console e rede | sem erro, sem 404 |

## Regras

- Não implementar.
- Sem proposta de dependência nova; se for inevitável, marcar como estrutural.
- Cada ponto com evidência observável.
- Screenshots no scratchpad, só com dado sintético; nunca abrir processo real.

## Escala

| Medida | 1 | 2 | 3 |
|---|---|---|---|
| Impacto | cosmético | atrasa a leitura | induz leitura errada ou esconde dado |
| Esforço | só componente Svelte | tela + `src/lib` | rota da API ou view `v_*` |

## Relatório

Tela e objetivo; primeiro olhar; contradições; tabela de heurísticas; ganhos rápidos (esforço 1);
estruturais (esforço 2–3); não avaliado. Fechar com a ordem sugerida, sem executar.
