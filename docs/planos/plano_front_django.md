# Plano — front da intranet em Django

19 de novembro de 2026 · Estado: **aprovado** · Atende a
[especificação da 0.2](../especificacao/0.2/especificacao.md): RF-INT-01 a RF-INT-05, RES-06,
RES-12, RNF-08, RNF-09; decisões 46 a 53. [ADR 0019](../adr/0019-front-django-renderizado-no-servidor.md).

## O que muda

### Banco

| Objeto | Antes | Depois |
| --- | --- | --- |
| `record_source` (`TEXT`) das linhas novas gravadas pela API em `link_evento_auditoria`, `link_chamada_modelo` e nos satélites de acesso, agente e processos | `intranet.acesso`, `intranet.agente`, `intranet.processos`, `intranet.auditoria` | `api.acesso`, `api.agente`, `api.processos`, `api.auditoria`; linhas já gravadas ficam como estão (D9) |

Nenhuma tabela, coluna, índice, função ou view muda. Não há migration.

### Arquivos

| Arquivo | Ação |
| --- | --- |
| `intranet/api/src/lupa_intranet/` | renomear para `intranet/api/src/lupa_api/`; imports, `resources.files(...)` e constantes `ORIGEM` (D9) |
| `intranet/api/tests/**`, `intranet/api/scripts/*.py` | alterar: imports `lupa_api` |
| `intranet/api/pyproject.toml`, `intranet/api/Dockerfile` | alterar: nome do pacote, `packages`, cobertura e caminhos |
| `pipeline/tests/unit/test_dependencias.py`, `pipeline/tests/validacoes/test_motor_e_regras.py` | alterar: pacote proibido `lupa_api` (e `lupa_web`) |
| `pipeline/scripts/limpar_dev.py` | mover para `intranet/api/scripts/limpar_dev.py`, com imports `lupa_api`; teste para `intranet/api/tests/unit/` (P1) |
| `intranet/web/` (SvelteKit: `src/`, `static/`, `e2e/`, `scripts/`, `package*.json`, `node_modules`, configs de Vite, Svelte, TS, ESLint, `Caddyfile`, `Dockerfile`) | remover (decisão 51) |
| `intranet/web/pyproject.toml`, `requirements.txt`, `requirements-dev.txt` | criar: pacote `lupa_web`, Django, httpx, WhiteNoise, segno, uvicorn; dev com pytest, pytest-django, respx, pytest-playwright, django-stubs, ruff, mypy (via `make lock`) |
| `intranet/web/Dockerfile` | criar: `python:3.12-slim`, usuário não root, `uvicorn lupa_web.asgi:application` (D1, D6) |
| `intranet/web/src/lupa_web/configuracao.py`, `asgi.py`, `urls.py` | criar: settings sem `DATABASES`, sessão desligada, CSRF, WhiteNoise, templates (D4) |
| `intranet/web/src/lupa_web/cliente_api.py` | criar: `httpx.AsyncClient` para `LUPA_WEB_API_URL`, repasse de cookie e IP (A1) |
| `intranet/web/src/lupa_web/telas/<tela>.py` | criar: uma view por tela da RF-INT-02 (acesso, processos, processo, dossiê, validações, visualizador, chat, auditoria, usuários) |
| `intranet/web/src/lupa_web/templates/` | criar: `base.html`, parciais em `componentes/` (cabeçalho, menu, aviso, confirmação, senha temporária, QR) e uma pasta por tela; fragmentos HTMX em `fragmentos/` |
| `intranet/web/src/lupa_web/static/css/` | criar: `base.css`, `componentes.css` e uma folha por tela, extraídas dos estilos Svelte (D7) |
| `intranet/web/src/lupa_web/static/js/htmx.min.js`, `static/js/envio.js`, `static/js/tema.js` | criar: HTMX versionado no repositório, o progresso do envio e a troca de tema (D8) |
| `intranet/web/tests/unit/`, `tests/telas/`, `tests/integracao/`, `tests/e2e/` | criar: testes de `lupa_web` (D5) |
| `intranet/web/e2e/Dockerfile` | criar: imagem Python com `pytest-playwright` e Chromium, perfil `e2e` (D6) |
| `intranet/web/scripts/e2e.sh` | reescrever: sobe o projeto Compose temporário e roda `pytest -m e2e` na imagem `e2e` |
| `intranet/api/scripts/e2e_preparar.py`, `e2e_processos.py`, `e2e_semear_chat.py` | manter; só imports |
| `docker-compose.yml` | alterar: serviço `front` com a imagem Python, rede `borda`, `LUPA_WEB_API_URL`, volume `envios-pendentes` (D16); `e2e` com a imagem nova |
| `intranet/web/src/lupa_web/envios_pendentes.py` | criar: guardar, recuperar e apagar o arquivo pendente de complemento (D16, A4) |
| `intranet/proxy/Caddyfile` | alterar: remove `handle_path /api/*`; tudo vai a `front:8000`; CSP sem `unsafe-hashes` (D2, D10) |
| `intranet/api/scripts/verificar_cabecalhos.py` | alterar: CSP esperada nova |
| `scripts/verificar.sh`, `Makefile` | alterar: etapa `web` (ruff, format, mypy, pytest em `front`) no lugar de `docker build --target verificacao`; rótulo `api` no lugar de `intranet` |
| `CLAUDE.md` | alterar: `lupa_api`, `lupa_web`, seção Front, testes E2E |
| `docs/sistema/front.md` | reescrever: front Django |
| `docs/arquitetura.md` | alterar: componente `front`, proxy sem `/api` |
| `docs/adr/0019-front-django-renderizado-no-servidor.md` | criar |
| `docs/adr/0006-front-sveltekit-spa-atras-de-proxy.md`, `docs/adr/0016-dois-pacotes.md` | alterar: status "Substituído por 0019" |
| `docs/imagens/` | substituir: capturas geradas pela suíte E2E nova |
| `CHANGELOG.md` | alterar: seção `Não publicado` |
| `docs/README.md` | alterar: inclui este plano e o ADR 0019 |

### O que não muda

- Rotas, contratos JSON, permissões, sessão, TOTP, bloqueio e auditoria da API.
- `lupa_pipeline`, worker, ingestão, validações, modelo Data Vault e views `v_*`.
- O diretório `intranet/api/` e a imagem `api`.
- Serviços `db`, `minio`, `minio-init`, `worker` e as redes.
- Linhas de `record_source` já gravadas.

## Problemas

- **P1.** `pipeline/scripts/limpar_dev.py` importa `lupa_intranet`, contra a regra de dependência
  do `CLAUDE.md`; o script vai para `intranet/api/scripts/` na fase 1.
- **P2.** A CSP atual depende do hash do anunciador de rota do SvelteKit (`unsafe-hashes`).
- **P3.** O QR do MFA, o progresso do envio, o seletor de tema e o visualizador hoje dependem de
  JavaScript do SvelteKit.
- **P4.** O IP do cliente que a API audita chega por `X-Forwarded-For`, que ela só aceita da rede
  `borda`; o Django passa a ser quem chama a API.
- **P5.** A resposta do chat leva segundos; o envio de PDF ou ZIP pode ter dezenas de megabytes.

## Decisões

- **D1.** Django em ASGI sob uvicorn; views assíncronas; cliente `httpx.AsyncClient` único por
  processo, criado no ciclo de vida do ASGI.
- **D2.** O Caddy deixa de rotear `/api`; o navegador só alcança o `front`. O Django chama
  `http://api:8000` pela rede `borda` e repassa a imagem PNG das páginas do visualizador.
- **D3.** Sessão (decisão 48): o Django lê o cookie da API do pedido, envia-o na chamada e copia
  para a resposta todo `Set-Cookie` que a API devolver. 401 da API vira redirecionamento a
  `/login`; 403 vira a página de acesso negado.
- **D4.** Sem banco (decisão 50): `DATABASES = {}`, sem `django.contrib.auth`, `sessions`,
  `admin` nem `contenttypes`. CSRF pelo cookie `csrftoken` do Django (`CSRF_USE_SESSIONS = False`),
  `SameSite=Strict`, `Secure`.
- **D5.** Testes: unitários e de tela com a API simulada por `respx`; marcador `integracao` contra
  a API real do compose; marcador `e2e` com `pytest-playwright` sobre o proxy (decisão 52).
- **D6.** Imagem `front` em `python:3.12-slim` com dependências de dev, roda o Django e os testes
  de `lupa_web`; imagem `e2e` separada com Chromium, perfil `e2e`.
- **D7.** CSS extraído dos componentes Svelte para `static/css/`, por assunto, com as mesmas
  classes, variáveis de tema e layout (decisão 53).
- **D8.** HTMX 2 versionado em `static/js/`, com `htmx.config.allowEval = false`,
  `includeIndicatorStyles = false` e `selfRequestsOnly = true`. JavaScript próprio só em
  `envio.js` (progresso do envio pelo evento `htmx:xhr:progress`), `tema.js` (troca de tema) e
  `visualizador.js` (atalhos de teclado do visualizador, decisão do usuário em 20/11/2026); sem script
  inline.
- **D9.** `record_source` das linhas novas passa de `intranet.*` para `api.*`; linhas antigas não
  mudam (sem `UPDATE`, RES-13). Consultas que filtram por `record_source` aceitam os dois prefixos.
- **D10.** CSP nova: `script-src 'self'; style-src 'self'`, sem `unsafe-hashes`; demais
  diretivas iguais.
- **D11.** QR code do MFA gerado no servidor com `segno`, em SVG inline no template.
- **D12.** Estáticos servidos pelo WhiteNoise, com hash no nome (`CompressedManifestStaticFilesStorage`).
- **D13.** Timeouts do cliente: `LUPA_WEB_TIMEOUT_API` (padrão 30 s) para as rotas comuns e
  `LUPA_WEB_TIMEOUT_CHAT` (padrão 180 s) para a pergunta do chat e o envio de arquivo.
- **D14.** O envio de arquivo usa `TemporaryFileUploadHandler` e é repassado à API em streaming;
  o limite de tamanho do Django é o mesmo da API, lido de `LUPA_WEB_TAMANHO_MAXIMO_ENVIO`.
- **D15.** `SECRET_KEY` vem de `LUPA_WEB_CHAVE_SECRETA`; sem a variável, o front gera uma chave
  aleatória a cada subida, e os tokens CSRF emitidos antes de um reinício são recusados uma vez
  (decisão do usuário em 20/11/2026, durante T10.3).
- **D16.** Envio pendente de complemento: a API não devolve identificador e apaga o arquivo; o
  Django guarda o arquivo no volume `envios-pendentes` (disco, montado em
  `/var/lupa/envios-pendentes` no `front`) sob um código aleatório de 32 bytes, junto com o hash
  SHA-256 do cookie de sessão de quem enviou. Validade de 2 horas. O pendente é apagado quando a
  API aceita o complemento ou recusa o arquivo; a cada envio novo, o Django apaga os vencidos
  (decisão do usuário em 20/11/2026, durante T10.8).
- **D17.** Diferenças do SvelteKit fechadas na paridade (decisão do usuário em 20/11/2026, durante
  T10.14): o painel "Início" em `/` é reproduzido com os mesmos dados da API; a opção "Visualizar
  como assessor" do desembargador é removida; o "+ Novo processo" abre e fecha o cadastro com
  `<details>`, sem JavaScript novo.
- **D18.** `Referrer-Policy: same-origin` no proxy e no Django, no lugar de `no-referrer`: com
  `no-referrer` o navegador manda `Origin: null` no POST de formulário e o CSRF do Django recusa
  todos (bug achado pelo E2E na T10.15; decisão do usuário em 20/11/2026). Não se aceita `null`
  em `CSRF_TRUSTED_ORIGINS`.

## Fases

1. Renomear `lupa_intranet` para `lupa_api` e `ORIGEM` para `api.*` (RES-12; D9; P1).
2. Esqueleto de `lupa_web`: pacote, settings, imagem, serviço `front`, cliente da API e verificação (RES-12, RNF-08; D1, D3, D4, D6, D12, D13).
3. Proxy sem `/api` e CSP nova (RF-INT-01; D2, D10; P2).
4. Acesso: login com TOTP, troca de senha, MFA com QR, logout (RF-INT-02, RF-INT-03; D3, D11; P3).
5. Processos: lista, cadastro por arquivo com progresso, processo, arquivos com diagnóstico e alertas, responsáveis, correção de classe e descarte (RF-INT-02, RF-INT-04; D8, D14; P5).
6. Dossiê, índice e reclassificação de peças, fatos com correção e histórico, achados, anotações e visualizador com imagem e bbox repassados (RF-INT-02, RF-INT-05; D2).
7. Chat com HTMX, histórico, revisão e liberação (RF-INT-02, RF-INT-05; D8, D13; P5).
8. Auditoria com exportação, verificação e relatório de uso; gestão de assessores (RF-INT-02, RF-INT-03).
9. CSS e tema reproduzindo o layout atual (RF-INT-02; D7, D8; P3).
10. Suíte E2E em `pytest-playwright` e capturas dos guias (RNF-09; D5, D6).
11. Remoção do SvelteKit, `verificar.sh`, `CLAUDE.md` e documentação (RES-06; decisão 51).

## Passo a passo do algoritmo

### A1 — Chamada do Django à API

1. Entrada: pedido HTTP do navegador; ação: lê o cookie de sessão da API (`NOME_COOKIE`) e o
   `X-Forwarded-For` posto pelo Caddy; saída: cabeçalhos de repasse.
2. Entrada: método, caminho da API e corpo; ação: chama `LUPA_WEB_API_URL` com o cookie e o
   `X-Forwarded-For` repassados e o timeout de D13; saída: resposta da API.
3. Desvio: a API não responde no prazo ou a conexão falha; ação: registra o evento sem corpo nem
   cookie; saída: página de erro 502 com "Serviço indisponível", sem tentar de novo.
4. Entrada: resposta da API; ação: copia cada `Set-Cookie` da API para a resposta ao navegador;
   saída: cookie renovado ou apagado no navegador.
5. Desvio: status 401; saída: redirecionamento 303 para `/login` (pedido HTMX: cabeçalho
   `HX-Redirect: /login`).
6. Desvio: status 403; saída: página "Acesso negado" com status 403.
7. Desvio: `GET /auth/sessao` indica troca de senha ou MFA pendente; saída: redirecionamento
   para `/trocar-senha`, antes de qualquer outra tela.
8. Desvio: status 4xx com corpo de erro da API; saída: mensagem da API no formulário da tela,
   com o mesmo status.
9. Saída final: JSON da API para a view montar o contexto do template.

### A2 — Formulário com CSRF

1. Entrada: GET de uma tela com formulário; ação: o Django emite `csrftoken` e o campo oculto;
   saída: página com o token.
2. Entrada: POST (formulário ou HTMX com `hx-headers` do token); ação: `CsrfViewMiddleware`
   confere; saída: segue para A1.
3. Desvio: token ausente ou inválido; saída: 403 sem chamar a API.

### A3 — Login com TOTP

1. Entrada: usuário e senha; ação: A1 em `POST /auth/login`; saída: pedido de código TOTP.
2. Entrada: código; ação: A1 em `POST /auth/mfa`; saída: `Set-Cookie` da API copiado e
   redirecionamento para `/` (painel "Início", D17; `/trocar-senha` com troca pendente), como no
   SvelteKit.
3. Desvio: credencial ou código recusado, ou usuário bloqueado; saída: a mensagem da API no
   formulário, sem dizer qual campo errou.
4. Desvio: MFA ainda não configurado; ação: A1 obtém a URI `otpauth`; `segno` gera o SVG; saída:
   tela de configuração com o QR, confirmada por A1 em `POST /auth/mfa/confirmar`.

### A4 — Envio de arquivo com progresso

1. Entrada: PDF ou ZIP no formulário `hx-post` com `hx-encoding="multipart/form-data"`; ação:
   `envio.js` mostra a barra com `htmx:xhr:progress`; saída: arquivo no Django.
2. Desvio: tamanho acima de `LUPA_WEB_TAMANHO_MAXIMO_ENVIO`; saída: fragmento com o motivo, sem
   chamar a API.
3. Entrada: arquivo temporário; ação: apaga os pendentes vencidos (D16); A1 em streaming para `POST /processos/arquivos` (novo) ou
   `POST /processos/<id>/arquivos` (anexo); saída:
   resultado (criado, anexado, duplicado, faltando campos).
4. Desvio: faltam número ou classe; ação: guarda o arquivo como pendente (D16); saída: fragmento
   que pede os campos, com os números encontrados e o código do pendente em campo oculto.
5. Entrada: complemento com código, número e classe; ação: recupera o pendente se o código existe,
   não venceu e o hash do cookie confere; A1 em streaming com o arquivo guardado; saída: resultado
   como no passo 3.
6. Desvio: código inexistente, vencido ou de outra sessão; saída: fragmento "Envio expirado,
   selecione o arquivo de novo", sem chamar a API.
7. Desvio: arquivo recusado; ação: apaga o pendente, se houver; saída: fragmento com o motivo da
   API.
8. Saída final: apaga o pendente, se houver; `HX-Redirect` para a tela do processo.
9. Entrada: tela do processo com arquivo não finalizado; ação: fragmento de estado com
   `hx-trigger="every 5s"` chama A1; saída: estado atualizado; para quando todos os arquivos
   estão em estado final.

### A5 — Pergunta no chat

1. Entrada: texto da pergunta no formulário `hx-post`; ação: mostra o indicador "aguardando
   resposta"; saída: pedido ao Django.
2. Entrada: pergunta; ação: A1 em `POST /processos/<id>/chat` com `LUPA_WEB_TIMEOUT_CHAT`; saída:
   resposta com citações conferidas, aviso de teto ou aviso de revisão.
3. Desvio: aviso de teto ou de revisão; saída: fragmento com o aviso, sem bloco de IA.
4. Desvio: nenhuma citação conferida; saída: fragmento "sem evidência".
5. Saída final: fragmento com a pergunta e a resposta em bloco rotulado como gerado por IA, cada
   citação com link para `/processos/<id>/visualizador?arquivo=…&pagina=…`, anexado ao fim da
   conversa (`hx-swap="beforeend"`).

### A6 — Imagem da página no visualizador

1. Entrada: GET `/processos/<id>/arquivos/<arquivo>/paginas/<n>/imagem`; ação: A1 na mesma rota da
   API; saída: bytes PNG.
2. Desvio: status diferente de 200; saída: o mesmo status, sem corpo da API.
3. Saída final: PNG com `Content-Type: image/png` e `Cache-Control: private`, os da API.

## Testes

Arquivos de `lupa_web` em `intranet/web/tests/`; os de `lupa_api` seguem em `intranet/api/tests/`.

- RES-12: `pipeline/tests/unit/test_dependencias.py::test_pipeline_nao_importa_lupa_api_nem_lupa_web` — nenhum módulo de `lupa_pipeline` importa os outros pacotes.
- RES-12: `intranet/web/tests/unit/test_dependencias.py::test_lupa_web_nao_importa_lupa_api_nem_lupa_pipeline` — `lupa_web` só fala por HTTP.
- RES-12 (D9): `intranet/api/tests/auditoria/test_registrador.py::test_evento_novo_grava_record_source_api` — linha nova com `api.auditoria`.
- RES-12 (D9): `intranet/api/tests/auditoria/test_consulta.py::test_auditoria_lista_eventos_com_record_source_antigo_e_novo` — eventos `intranet.*` e `api.*` aparecem juntos.
- D4: `intranet/web/tests/unit/test_configuracao.py::test_lupa_web_nao_configura_banco` — `DATABASES` vazio e apps de banco ausentes.
- RF-INT-01: `intranet/web/tests/telas/test_processos.py::test_lista_de_processos_vem_renderizada_da_api` — HTML com os processos simulados e uma chamada a `/processos` na API.
- RF-INT-01: `intranet/web/tests/e2e/test_seguranca.py::test_navegador_nao_faz_requisicao_para_api` — nenhuma requisição do navegador para `/api`.
- RF-INT-01 (D2): `intranet/web/tests/integracao/test_proxy.py::test_proxy_responde_404_para_api` — `/api/saude` pelo proxy não chega à API.
- RF-INT-02: `intranet/web/tests/telas/test_paridade.py::test_cada_tela_responde_ao_papel_permitido` — parametrizado pelas onze telas e pelas ações das fases 4 a 8.
- RF-INT-02: `intranet/web/tests/telas/test_paridade.py::test_assessor_recebe_acesso_negado_em_auditoria_e_usuarios` — 403 da API vira a página de acesso negado.
- RF-INT-03: `intranet/web/tests/unit/test_cliente_api.py::test_cookie_da_api_e_repassado_e_set_cookie_volta` — cookie enviado e `Set-Cookie` copiado.
- RF-INT-03: `intranet/web/tests/unit/test_cliente_api.py::test_x_forwarded_for_e_repassado` — IP do cliente chega à API.
- RF-INT-03: `intranet/web/tests/telas/test_acesso.py::test_sessao_expirada_redireciona_para_login` — 401 vira 303 para `/login`.
- RF-INT-03: `intranet/web/tests/telas/test_acesso.py::test_pedido_htmx_com_sessao_expirada_recebe_hx_redirect` — cabeçalho `HX-Redirect`.
- RF-INT-03: `intranet/web/tests/telas/test_csrf.py::test_post_sem_csrf_e_recusado_sem_chamar_api` — 403 e nenhuma chamada registrada no `respx`.
- RF-INT-03: `intranet/web/tests/unit/test_cliente_api.py::test_api_fora_do_ar_mostra_servico_indisponivel` — 502 sem retentativa.
- RF-INT-02 (A3): `intranet/web/tests/telas/test_acesso.py::test_login_com_codigo_errado_mostra_recusa_generica` — mensagem sem dizer o campo.
- RF-INT-02 (D11): `intranet/web/tests/telas/test_acesso.py::test_configuracao_de_mfa_mostra_qr_em_svg` — SVG do `segno` com a URI simulada.
- RF-INT-04: `intranet/web/tests/telas/test_envio.py::test_pdf_sem_classe_pede_a_classe_e_reenvio_usa_o_mesmo_arquivo` — fragmento com campo de classe e código do pendente; o complemento reenvia à API o arquivo guardado, sem novo upload.
- RF-INT-04 (D16): `intranet/web/tests/unit/test_envios_pendentes.py::test_pendente_vencido_ou_de_outra_sessao_nao_e_recuperado` — validade de 2 horas e hash do cookie.
- RF-INT-04 (D16): `intranet/web/tests/unit/test_envios_pendentes.py::test_pendente_e_apagado_apos_aceite_e_vencidos_no_envio_novo` — limpeza.
- RF-INT-04: `intranet/web/tests/telas/test_envio.py::test_arquivo_acima_do_limite_e_recusado_sem_chamar_api` — motivo no fragmento.
- RF-INT-04: `intranet/web/tests/telas/test_processo.py::test_estado_do_arquivo_para_de_atualizar_no_estado_final` — fragmento sem `hx-trigger` quando tudo está em estado final.
- RF-INT-04: `intranet/web/tests/integracao/test_envio_api_real.py::test_envio_de_pdf_sintetico_cria_processo_pela_api` — envio real, marcador `integracao`.
- RF-INT-05: `intranet/web/tests/telas/test_chat.py::test_resposta_conferida_aparece_em_bloco_rotulado_com_link_da_pagina` — rótulo de IA e link do visualizador.
- RF-INT-05: `intranet/web/tests/telas/test_chat.py::test_resposta_sem_citacao_conferida_mostra_sem_evidencia` — "sem evidência".
- RF-INT-05: `intranet/web/tests/telas/test_chat.py::test_aviso_de_teto_aparece_sem_bloco_de_ia` — aviso de teto.
- RF-INT-05: `intranet/web/tests/telas/test_dossie.py::test_evidencia_do_dossie_abre_a_pagina_do_arquivo` — link da evidência.
- RF-INT-02 (A6): `intranet/web/tests/telas/test_visualizador.py::test_imagem_da_pagina_e_repassada_com_tipo_e_cache_da_api` — PNG e cabeçalhos.
- D10: `intranet/api/scripts/verificar_cabecalhos.py` (teste em `intranet/api/tests/unit/test_verificar_cabecalhos.py::test_csp_sem_unsafe_hashes`) — CSP nova.
- RNF-08: `scripts/verificar.sh` — ruff, format, mypy `--strict` e pytest com cobertura de 90% em `lupa_web` no contêiner `front`.
- RNF-09: `intranet/web/tests/e2e/test_fluxos.py` (login, processos, dossiê, chat, auditoria, gestão de assessores) e `intranet/web/tests/e2e/test_capturas.py::test_gera_capturas_dos_guias` — marcador `e2e`, fora do ciclo; revisão manual das capturas.

Revisão manual: conferência visual do layout contra o atual (D7) e as capturas de `docs/imagens/`.

## Execução

1. Commit e PR para `develop` citando as tarefas das fases 1 a 11.
2. `docker compose up -d --build --wait --remove-orphans`.
3. `bash scripts/verificar.sh` e `LUPA_VERIFICAR_E2E=1 bash intranet/web/scripts/e2e.sh`.
