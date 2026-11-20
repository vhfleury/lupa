# Plano — Padrão visual da intranet

Requisitos: RF-VIS-01, RF-VIS-02, RF-VIS-03, RF-VIS-04, RF-VIS-05, RF-VIS-06 e RNF-09, da seção 4.13 da
[especificação da 0.2](../especificacao/0.2/especificacao.md), decisões 54 a 58.

## O que muda

Nenhum objeto do banco muda.

| Objeto | Antes | Depois |
| --- | --- | --- |
| Tokens CSS (`:root`, tema claro e escuro) | declarados em `base.css`, paleta azul, `system-ui` | `tokens.css` único: cores verdes (D1), fontes Source, espaço, raio |
| Fontes | do sistema | `static/fontes/`: Source Serif 4 600, Source Sans 3 400/400 itálico/600, Source Code Pro 400, woff2 latino, OFL (D3, D4) |
| Componentes (templates) | 8 em `templates/componentes/`, marcação própria nas telas | 11 do catálogo de RF-VIS-04 em `templates/componentes/`, chamados por `{% include ... with %}` (D2) |
| Rota `/padrao` (view `telas/padrao.py`) | não existe | página do catálogo; 404 fora de `LUPA_AMBIENTE=desenvolvimento` |
| Axe no E2E | tags WCAG 2.1 A e AA | todas as regras, inclusive boas práticas, em toda tela e na `/padrao`, nos dois temas |
| Capturas | telas da suíte | mais `/padrao` em claro, escuro e 375 px; guias em `docs/imagens/` regerados |

| Arquivo | Ação |
| --- | --- |
| `intranet/web/src/lupa_web/static/css/tokens.css` | criar |
| `intranet/web/src/lupa_web/static/css/base.css`, `componentes.css` e os 10 CSS de tela | alterar: só referências a tokens |
| `intranet/web/src/lupa_web/static/fontes/*.woff2`, `LICENSE.md` | criar |
| `intranet/web/src/lupa_web/templates/componentes/{botao,aviso,tabela,campo,acao,paginacao,vazio,badge,cartao,progresso,selo}.html` | criar ou alterar (`aviso.html` existe) |
| `intranet/web/src/lupa_web/templates/padrao.html`, `telas/padrao.py`, `urls.py` | criar / alterar |
| templates de todas as telas em `templates/` | alterar: usar os componentes |
| `intranet/web/tests/unit/test_tokens.py`, `test_conformidade_templates.py` | criar |
| `intranet/web/tests/telas/test_padrao.py` e testes de tela afetados | criar / alterar |
| `intranet/web/tests/e2e/test_acessibilidade.py`, `test_capturas.py` | alterar |
| `docs/sistema/padrao-visual.md`, `docs/sistema/front.md`, `docs/README.md`, `CHANGELOG.md` | criar / alterar |
| `docs/imagens/*` | regerar |

O que não muda:

- API, rotas e dados da API; estrutura das telas e ações de RF-INT-02.
- CSP (`font-src 'self'` já existe), Caddyfile, `docker-compose.yml`, Dockerfiles e requirements.
- JavaScript próprio (`envio.js`, `tema.js`, `visualizador.js`) e o seletor de tema.

## Problemas

- P1. As cores e as fontes estão espalhadas: `base.css` declara os tokens, e `inicio.css`, `login.css`, `processos.css` e `visualizador.css` têm cor literal.
- P2. Resultado de validação e botão primário passam a usar o mesmo verde, então só a forma os distingue (RF-VIS-03).
- P3. As telas montam botão, tabela e aviso com marcação própria.
- P4. O axe só roda as tags WCAG A e AA.

## Decisões

- D1. Paleta: primária `#00613b` no tema claro e `#4cc489` no escuro, fundo branco. Sucesso, atenção e falha mantêm verde, âmbar e vermelho. Todo par texto/fundo tem pelo menos 4,5:1, e borda, foco e tarja têm pelo menos 3:1 sobre o fundo (decisões 54 e 57).
- D2. Componentes por `{% include "componentes/<nome>.html" with ... %}`, sem templatetags.
- D3. Fontes mínimas: Source Serif 4 600 (h1 a h3), Source Sans 3 400, 400 itálico e 600, Source Code Pro 400. Subconjunto latino em woff2 e `font-display: swap`.
- D4. Os woff2 vêm das releases oficiais `adobe-fonts` no GitHub. O SHA-256 de cada arquivo é registrado em `padrao-visual.md`, e o `LICENSE.md` (OFL) vai ao lado.
- D5. Conformidade por teste unitário, que varre:
  - os CSS fora de `tokens.css`, que não podem ter cor hexadecimal, `rgb(`, `hsl(` nem `font-family` literal;
  - os templates fora de `componentes/`, que não podem ter `<button`, `<table`, `<progress` nem `class="aviso`.
- D6. O teste de contraste lê `tokens.css` e confere uma lista explícita de pares, declarada no próprio teste, nos dois temas.
- D7. Badge: pílula neutra, só para estados de fluxo (ingestão, conversa, papel). Selo: tarja lateral de 4 px no tom do resultado, sobre o fundo claro do mesmo tom, com o texto do resultado.
- D8. A `/padrao` exige sessão válida, como as demais telas. Fora do desenvolvimento devolve 404 antes de chamar a API.
- D9. Migração em duas etapas:
  - a fase 1 entrega os tokens, as fontes, o catálogo e a `/padrao`, e o usuário aprova o visual pelas capturas;
  - as fases 2 a 6 levam um grupo de telas cada.
- D10. As capturas continuam só geradas, sem comparação pixel a pixel.

## Fases

1. Tokens, fontes, 11 componentes e `/padrao`, com o teste de contraste. Aprovação visual pelas capturas da `/padrao` (P1, P2; D1–D4, D6–D8; RF-VIS-01, 02, 03, 04, 05).
2. Acesso: login, TOTP, troca de senha, erros e acesso negado (P3; D2, D5; RF-VIS-04).
3. Início, processos, processo e envio (P3; D2, D5, D7; RF-VIS-04).
4. Dossiê, validações e visualizador (P2, P3; D2, D5, D7; RF-VIS-03, 04).
5. Chat (P3; D2, D5; RF-VIS-04).
6. Auditoria e usuários; o teste de conformidade (D5) passa a valer para todos os templates (P1, P3; D5; RF-VIS-01, 04).
7. Axe com todas as regras nos dois temas, capturas da `/padrao` e guias regerados (P4; D10; RF-VIS-06, RNF-09).
8. `padrao-visual.md`, `front.md`, `docs/README.md` e CHANGELOG (RF-VIS-04).

## Passo a passo do algoritmo

### A1 — Requisição a `/padrao`

1. Entrada: GET `/padrao`. Ação: ler `LUPA_AMBIENTE`. Saída: o ambiente.
2. Se o ambiente for diferente de `desenvolvimento`, responder 404 sem chamar a API. Para aqui.
3. Ação: o middleware de sessão confere a sessão na API, como nas demais telas. Saída: o usuário ou o redirecionamento.
4. Se não houver sessão, redirecionar para `/login`. Para aqui.
5. Entrada: dados sintéticos fixos em `telas/padrao.py`. Ação: renderizar `padrao.html`, que inclui cada componente em cada variante. Saída: HTML 200.

### A2 — Teste de contraste (`test_tokens.py`)

1. Entrada: `tokens.css`. Ação: extrair as variáveis de `:root` e de cada bloco do tema escuro. Saída: um dicionário de tokens por tema.
2. Se um token da lista de pares não existir num tema, o teste falha citando o token e o tema.
3. Entrada: a lista de pares (texto ou não texto, frente, fundo). Ação: calcular a razão de contraste WCAG de cada par em cada tema. Saída: as razões.
4. Se um par de texto ficar abaixo de 4,5:1, ou um par não textual abaixo de 3:1, o teste falha citando o par, o tema e a razão.

### A3 — Teste de conformidade (`test_conformidade_templates.py`)

1. Entrada: os CSS de `static/css/` exceto `tokens.css`. Ação: procurar cor literal e `font-family` sem `var(`. Saída: as ocorrências.
2. Entrada: os templates fora de `templates/componentes/`. Ação: procurar as marcações proibidas de D5. Saída: as ocorrências.
3. Se houver ocorrência, o teste falha listando arquivo e linha.
4. Até a fase 6, os grupos de telas ainda não migrados ficam numa lista de pendentes do teste, e cada fase tira o seu grupo. Na fase 6 a lista fica vazia e sai do teste.

### A4 — Axe no E2E

1. Entrada: cada tela da suíte e a `/padrao`, nos temas claro e escuro. Ação: injetar o `axe.min.js` e rodar `axe.run` sem filtro de tags. Saída: as violações.
2. Se houver qualquer violação, o teste da tela falha citando a regra e o seletor.
3. Na `/padrao`: ação capturar em claro e escuro a 1200 px e em claro a 375 px. Saída: os PNG `padrao-<tema>-<largura>.png`.

## Checklist de testes

- RF-VIS-01: `intranet/web/tests/unit/test_conformidade_templates.py::test_css_de_tela_nao_tem_cor_nem_fonte_literal` — só `tokens.css` declara cor ou fonte.
- RF-VIS-01: `intranet/web/tests/unit/test_tokens.py::test_tema_escuro_redefine_todos_os_tokens_de_cor` — todo token de cor do tema claro existe no escuro.
- RF-VIS-02: `intranet/web/tests/unit/test_tokens.py::test_pares_de_texto_atingem_4_5_nos_dois_temas` — contraste de texto.
- RF-VIS-02: `intranet/web/tests/unit/test_tokens.py::test_borda_foco_e_tarja_atingem_3_nos_dois_temas` — contraste não textual.
- RF-VIS-02: `intranet/web/tests/unit/test_tokens.py::test_primaria_e_verde_do_padrao` — `#00613b` e `#4cc489`.
- RF-VIS-02: `intranet/web/tests/e2e/test_seguranca.py::test_fontes_vem_da_propria_origem` — nenhuma requisição de fonte a domínio externo, e a CSP com `font-src 'self'`.
- RF-VIS-03: `intranet/web/tests/telas/test_validacoes.py::test_resultado_tempestivo_aparece_no_selo_de_sucesso` — classe do selo e texto do resultado.
- RF-VIS-03: `intranet/web/tests/telas/test_validacoes.py::test_atencao_e_falha_usam_selo_do_seu_tom` — variantes distintas do botão.
- RF-VIS-04: `intranet/web/tests/unit/test_conformidade_templates.py::test_templates_de_tela_usam_componentes` — sem marcação proibida fora de `componentes/`.
- RF-VIS-04: `intranet/web/tests/telas/test_processos.py::test_estado_de_ingestao_aparece_no_badge` — badge neutro, sem selo.
- RF-VIS-04: `intranet/web/tests/e2e/test_acessibilidade.py::test_tabela_larga_rola_sozinha_em_375px` — a página não rola na horizontal.
- RF-VIS-05: `intranet/web/tests/telas/test_padrao.py::test_padrao_mostra_cada_componente_em_desenvolvimento` — os 11 componentes presentes.
- RF-VIS-05: `intranet/web/tests/telas/test_padrao.py::test_padrao_devolve_404_fora_do_desenvolvimento` — 404 sem chamada à API.
- RF-VIS-05: `intranet/web/tests/telas/test_padrao.py::test_padrao_sem_sessao_vai_ao_login` — redirecionamento.
- RF-VIS-06: `intranet/web/tests/e2e/test_acessibilidade.py::test_axe_sem_violacoes_em_toda_tela` — todas as regras, nos dois temas.
- RF-VIS-06: `intranet/web/tests/e2e/test_capturas.py::test_capturas_do_padrao_nos_tres_formatos` — três PNG gerados.
- RNF-09: `bash intranet/web/scripts/e2e.sh` — suíte completa verde.
- Revisão manual: os templates só de apresentação, o visual das capturas da fase 1 e as dos guias.

## Execução

1. Commit por tarefa e PR único da branch `feat/padrao-visual`.
2. No servidor do piloto: `docker compose up -d --build --wait`. Não há migration.
