# Padrão visual da intranet

O padrão visual atende à seção 4.13 da [especificação da 0.2](../especificacao/0.2/especificacao.md)
(RF-VIS-01 a RF-VIS-06) e foi implantado pelo [plano do padrão visual](../planos/plano_padrao_visual.md).
Vale para toda tela do front `lupa_web` ([interface](front.md)).

## Tokens

`intranet/web/src/lupa_web/static/css/tokens.css` é a única folha com cor, fonte, espaço e raio
literais. `base.html` a carrega antes de `base.css`; as demais folhas só usam `var(--…)`.

| Grupo | Tokens |
| --- | --- |
| Fundo e texto | `--fundo`, `--superficie`, `--superficie-suave`, `--texto`, `--texto-suave` |
| Borda e foco | `--borda`, `--borda-campo`, `--foco` |
| Primária | `--primaria` (`#00613b` no claro, `#4cc489` no escuro), `--primaria-texto` |
| Resultado | `--sucesso`, `--atencao`, `--perigo`, cada um com `-fundo` |
| Aviso | `--aviso-fundo`, `--aviso-texto` |
| Badge | `--badge-fundo`, `--badge-texto`, `--badge-borda` |
| Fontes | `--fonte-titulo` (Source Serif 4), `--fonte` (Source Sans 3), `--mono` (Source Code Pro) |
| Medidas | `--raio`, `--raio-pilula`, `--tarja` (4 px), `--espaco-1` a `--espaco-5` |

O tema escuro redefine todos os tokens de cor, pelo sistema ou pela escolha manual (`tema.js`).
`intranet/web/tests/unit/test_tokens.py` confere 4,5:1 nos pares de texto e 3:1 em borda, foco e
tarja, nos dois temas. `intranet/web/tests/unit/test_conformidade_templates.py` falha se um CSS
fora de `tokens.css` tiver cor ou `font-family` literal, ou se um template fora de
`templates/componentes/` tiver `<button`, `<table`, `<progress` ou `class="aviso`.

Os títulos `h1` a `h3` usam `--fonte-titulo` com peso 600. O corpo usa peso 400 e 600; não há
peso 700, porque a face não é carregada.

## Componentes

Cada componente é um template em `templates/componentes/`, chamado por `include ... with`, sem
templatetag. A raiz de cada um tem `data-componente="<nome>"`. Como o `include` herda o contexto,
passe vazio (`href=""`, `variante=""`) o parâmetro que a tela também tenha no contexto.

| Componente | Parâmetros |
| --- | --- |
| `botao` | `rotulo`, `variante` (`secundario`, `perigo`), `href` (vira link), `tipo`, `nome`/`valor`, `rotulo_acessivel`, `formulario`, `desabilitado` |
| `aviso` | `mensagem`, `tipo` (`info`, `sucesso`, `erro`), `testid`, `status` |
| `tabela` | `legenda`, `colunas`, `linhas` ou `corpo` (template das linhas), `testid` |
| `campo` | `rotulo`, `nome`, `id_campo`, `tipo` (`select`, `textarea` ou de `input`), `valor`, `opcoes`, `dica`, `autocomplete`, `obrigatorio` |
| `acao` | `rotulo`, `acao`, `campos`, `rotulo_enviar` |
| `paginacao` | `pagina`, `total_paginas`, `anterior_href`, `proxima_href` |
| `vazio` | `mensagem`, `dica`, `acao_rotulo`, `acao_href` |
| `badge` | `texto`, `testid`, `estado` |
| `cartao` | `titulo`, `texto`, `id_cartao`, `destaque` |
| `progresso` | `rotulo`, `valor`, `id_progresso` |
| `selo` | `tom` (`sucesso`, `atencao`, `falha`), `texto`, `detalhe`, `testid` |

Exemplo:

```django
{% include "componentes/botao.html" with rotulo="Salvar classe" variante="" href="" %}
{% include "componentes/tabela.html" with legenda="Processos" colunas=colunas_processos testid="lista-processos" corpo="processos/_linhas_processos.html" %}
```

A tabela fica numa região rolável com foco (`tabindex="0"`) e legenda oculta; a 375 px só ela
rola de lado. As colunas vêm da view, em constantes `COLUNAS_*`.

O badge é uma pílula neutra para estado de fluxo: situação da ingestão, estado do arquivo, status
do fato, sinais da peça. O selo é reservado ao resultado de validação: tarja lateral de
`--tarja` no tom e fundo claro do mesmo tom, com o texto do resultado. `rotulos.TOM_DO_RESULTADO`
liga `conforme` a sucesso, `verificar` a atenção e `atencao` a falha.

## Página `/padrao`

`telas/padrao.py` mostra cada componente em cada variante, com dados sintéticos fixos. Exige
sessão e só existe com `LUPA_AMBIENTE=desenvolvimento`; fora dele responde 404 sem chamar a API.
O serviço `front` recebe `LUPA_AMBIENTE` do `docker-compose.yml`, e o E2E fixa `desenvolvimento`
para ele em `intranet/web/e2e/compose.yaml`.

## Acessibilidade e capturas

`intranet/web/tests/e2e/test_acessibilidade.py` roda o axe sem filtro de tags, boas práticas
incluídas, em toda tela e na `/padrao`, nos temas claro e escuro, e não aceita violação.
`bash intranet/web/scripts/capturas.sh` regera `docs/imagens/`; com `LUPA_CAPTURAS_VISUAL=<pasta>`
grava também cada tela em claro e escuro a 1200 e 375 px e a `/padrao` em
`padrao-claro-1200.png`, `padrao-escuro-1200.png` e `padrao-claro-375.png`. As capturas não são
comparadas pixel a pixel.

## Fontes

Os woff2 ficam em `static/fontes/`, com a licença OFL 1.1 em `LICENSE.md`. Vêm das releases
oficiais `adobe-fonts` no GitHub, da variante TTF de cada release, inteiros. A CSP já tem
`font-src 'self'`; nenhuma fonte vem de outro domínio.

| Arquivo | Origem | Bytes | SHA-256 |
| --- | --- | --- | --- |
| `SourceSerif4-Semibold.woff2` | source-serif 4.005R, `TTF/SourceSerif4-Semibold.ttf.woff2` | 80732 | `457a13ac92e977d82e376038a2daac7fdb5433610910bf5787bdf6c1c3781865` |
| `SourceSans3-Regular.woff2` | source-sans 3.052R, `TTF/SourceSans3-Regular.ttf.woff2` | 109632 | `53492fb3a0def77354f166a55d09b63a10855e91c206c7620a81cf56e97f8ec3` |
| `SourceSans3-It.woff2` | source-sans 3.052R, `TTF/SourceSans3-It.ttf.woff2` | 86452 | `4d80b3b801f4c457f1b4adbd3911d8501338e6d282141663770c38d3a2e97859` |
| `SourceSans3-Semibold.woff2` | source-sans 3.052R, `TTF/SourceSans3-Semibold.ttf.woff2` | 108900 | `47b9b661b9f395fe7f0d0e119637fba5c8dad97bde3df60066fd24229c0792f4` |
| `SourceCodePro-Regular.woff2` | source-code-pro 2.042R-u/1.062R-i/1.026R-vf, `TTF/SourceCodePro-Regular.ttf.woff2` | 74052 | `714eee29b70d191f5bf4b3a06b68f2c50522b1303d31c7d44dcefdcc5f9defd0` |
