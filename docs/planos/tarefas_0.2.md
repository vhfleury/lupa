# Tarefas da versão 0.2

Quebra do [plano da 0.2](plano_0.2.md) em tarefas. Cada tarefa cita a fase, as decisões (D), os
algoritmos (A) de [plano_0.2_execucao.md](plano_0.2_execucao.md) e os requisitos da
[especificação](../especificacao/0.2/especificacao.md). Um commit por tarefa em
`feat/versao-0.2`. Ao concluir, marque a caixa e acrescente abaixo da tarefa o comando de teste e
a saída resumida (vermelho inicial e verde final).

## Fase 1 — Reestruturação

- [x] **T1.1** Mover `src/lupa/{config,logging,dominio,seguranca,ingestao,validacoes,sinteticos,migrations}` para `pipeline/src/lupa_pipeline/` e os testes correspondentes para `pipeline/tests/`, com `pipeline/pyproject.toml` e `requirements*.txt`. D1, D19, D20. RES-05, RES-12.
  - Feita no mesmo commit de T1.2 e T1.5: código, testes e scripts se importam e não ficam
    verdes separados. Sem teste novo (só movimentação); verificação em T1.7.
  - Linha de base (0.1, antes de mover, contêiner `api`): `python -m pytest` → 884 passed,
    2 failed, 2 skipped, 3 deselected; cobertura 97,97%.
- [x] **T1.2** Mover `src/lupa/{api,acesso,auditoria,agente}` para `intranet/api/src/lupa_intranet/` e os testes correspondentes para `intranet/api/tests/`, com `intranet/api/pyproject.toml` e `requirements*.txt`. D1, D19, D20. RES-04, RES-12.
  - Junto com T1.1 e T1.5. Além dos quatro testes listados no plano, foram para
    `intranet/api/tests/` os que usam rota da API ou login: `ingestao/test_ponta_a_ponta.py`,
    `ingestao/test_eventos_banco.py`, `seguranca/test_cifra_banco.py`, o último teste de
    `ingestao/test_worker_extracao.py` (em `test_worker_extracao_api.py`) e o teste de
    `unit/test_config.py` que chama `create_app`.
- [x] **T1.3** Teste que impede `lupa_pipeline` de importar `lupa_intranet`. D2. RES-12.
  - `pipeline/tests/unit/test_dependencias.py`. Comando: `docker compose exec worker python -m
    pytest -c pipeline/pyproject.toml pipeline/tests/unit/test_dependencias.py --no-cov -q`.
  - Vermelho (com `import lupa_intranet.api.app` temporário num módulo da pipeline, só no
    contêiner): `1 failed, 1 passed`. Verde (sem ele): `2 passed`.
- [x] **T1.4** Mover `front/` para `intranet/web/` e `proxy/` para `intranet/proxy/`. D1. RES-04, RES-06.
  - Comando: `docker build --target verificacao intranet/web` → ok (lint, typecheck e
    unitários do front).
- [x] **T1.5** Distribuir `scripts/` entre `pipeline/scripts/`, `intranet/api/scripts/` e a raiz. D1.
  - Junto com T1.1 e T1.2. `criar_usuario_banco.py` ficou em `intranet/api/scripts/` (importa
    `lupa_intranet.acesso.instalacao`); scripts de backup, piloto e Vault ficam na raiz até a
    fase 2.
- [x] **T1.6** `pipeline/Dockerfile`, `intranet/api/Dockerfile`, `docker-compose.yml`, `Makefile`, `scripts/verificar.sh`, `.dockerignore`, `.gitignore`, `.env.example` e `.claude/agents/tdd.md` nos caminhos novos; `CLAUDE.md` atualizado. D21, D22. RNF-06, RNF-08.
  - Comandos: `docker compose up -d --build --wait` → todos os serviços `healthy`;
    `docker compose -f docker-compose.yml -f docker-compose.prod.yml config -q` → ok.
- [ ] **T1.7** Suíte completa da 0.1 verde nos dois pacotes, com 90% de cobertura em cada, e `docker build --target verificacao intranet/web` verde.
  - Não marcada: dois testes falham já na 0.1 (linha de base em T1.1), por divergência entre
    teste e código depois da migração `v0011_responsaveis`, que criou `processo_responsavel`:
    `pipeline/tests/dominio/test_banco.py::test_rls_ativa_em_todas_as_tabelas_com_gabinete` e
    `intranet/api/tests/auditoria/test_limpar_dev.py::test_remove_dados_em_cascata_do_processo`.
    Em 14/11/2026 o usuário decidiu preservar esse resultado histórico. A verificação dos
    responsáveis segue na versão 0.2 pelo vínculo `link_processo_responsavel`, pela view
    `v_responsavel` e pelas rotas de atribuição e remoção (T3.6 e regressão).
  - Comandos (no host, stack de pé): `docker compose exec worker python -m pytest -c
    pipeline/pyproject.toml pipeline/tests` e `docker compose exec api python -m pytest -c
    intranet/api/pyproject.toml intranet/api/tests`.
  - Pipeline (imagem do `worker`): 602 passed, 1 failed; cobertura `lupa_pipeline` 94,03%.
  - Intranet (imagem da `api`): 284 passed, 1 failed, 2 skipped (backup, só com
    `LUPA_VERIFICAR_BACKUP=1`), 3 deselected; cobertura `lupa_intranet` 98,74%.
  - `ruff check`, `ruff format --check` e `mypy` nos dois pacotes: ok. Ponta a ponta (1
    passed), corpus de injeção (2 passed, recall 1.0, falso positivo 0.0), suíte do agente
    (9 passed), cabeçalhos do proxy (ok) e `docker build --target verificacao intranet/web`
    (ok).

## Fase 2 — Remoções de infraestrutura

- [x] **T2.1** Remover Prometheus, Grafana, `monitoramento/`, `ingestao/metricas.py`, as rotas `/metricas` e `/metricas/servico`, `prometheus-client` e os testes correspondentes. D27. Decisão 16.
  - Saíram os serviços `prometheus` e `grafana`, os segredos `metricas_token` e `grafana_senha` e
    os volumes do compose (os volumes `lupa_prometheus-dados` e `lupa_grafana-dados` ficam órfãos
    no Docker até a execução do plano), os blocos correspondentes de `docker-compose.prod.yml`,
    `monitoramento/`, `ingestao/metricas.py`, `GET /metricas`, `GET /metricas/servico`,
    `Settings.metricas_token`, as variáveis de `.env.example` e `prometheus-client` (lock com os
    argumentos do alvo `lock`). Nenhuma outra funcionalidade lia as métricas.
  - Testes removidos com o código: `intranet/api/tests/api/test_metricas_servico.py`,
    `test_rotas.py::test_metricas_so_para_administrador` e os dois testes de métricas de
    `pipeline/tests/ingestao/test_observabilidade.py`; o teste de logs do worker sem texto dos
    autos fica no arquivo.
  - Testes novos: `pipeline/tests/unit/test_config.py::test_configuracao_ignora_chaves_de_metricas_e_backup`
    e `intranet/api/tests/api/test_saude.py::test_rotas_de_metricas_nao_existem`. Comandos:
    `docker compose exec worker python -m pytest -c pipeline/pyproject.toml
    pipeline/tests/unit/test_config.py --no-cov -q` e `docker compose exec api python -m pytest -c
    intranet/api/pyproject.toml intranet/api/tests/api/test_saude.py --no-cov -q`.
  - Vermelho (testes copiados para os contêineres antes da remoção): `1 failed, 5 passed`
    (`metricas_token` ainda é campo; as chaves de backup já não eram) e `2 failed, 10 passed`
    (`/metricas/servico` 200 com o token, `/metricas` 401). Verde, depois do rebuild: `6 passed` e
    `12 passed`.
  - Suítes completas: pipeline 604 passed, 1 failed (`test_rls_ativa_em_todas_as_tabelas_com_gabinete`,
    já na linha de base), cobertura 93,98%; intranet 282 passed, 1 failed
    (`test_remove_dados_em_cascata_do_processo`, já na linha de base), 2 skipped, 3 deselected,
    cobertura 98,71%. `ruff check`, `ruff format --check` e `mypy` nos dois pacotes: ok.
- [x] **T2.2** Remover backup: serviços do compose, scripts, `tests/backup/`, marcador `backup` e `docs/operacao/backup.md`. Decisão 16.
  - Saíram os serviços `backup` e `backup-agendado` (e o bloco de `backup-agendado` em
    `docker-compose.prod.yml`), `scripts/{backup,backup_comum,backup_conteiner,cron_backup,expurgar_backups,restaurar}.sh`,
    `intranet/api/tests/backup/` (com o registro do marcador `backup`, feito no `conftest.py` da
    pasta), o passo de backup de `scripts/verificar.sh`, as variáveis `LUPA_BACKUP_*` de
    `.env.example`, as menções em `CLAUDE.md` e `docs/operacao/backup.md`. `.backups/` e
    `.backup-chaves/` continuam em `.gitignore` e `.dockerignore`, porque as pastas podem existir
    na máquina.
  - Sem teste novo além do de T2.1 (`Settings` não tem chave de backup; já verde antes).
    Comandos: `bash -n scripts/verificar.sh` → ok; `docker compose config -q` e
    `docker compose -f docker-compose.yml -f docker-compose.prod.yml config -q` → ok; depois de
    `docker compose up -d --build --wait api`, `docker compose exec api python -m pytest -c
    intranet/api/pyproject.toml intranet/api/tests` → 282 passed, 1 failed (o da linha de base),
    3 deselected, sem os 2 skipped de backup; cobertura 98,71%.
- [x] **T2.3** Remover o perfil de produção: `docker-compose.prod.yml`, `instalar_piloto.sh`, `conferir_piloto.py`, `preparar_repositorio.md`, `vault/producao/` e os modos `acme` e `fornecido` do proxy. D25. RES-11.
  - Saíram `docker-compose.prod.yml`, `scripts/{instalar_piloto.sh,conferir_piloto.py,preparar_repositorio.md}`
    (sem teste próprio), `vault/producao/`, `intranet/proxy/modos/{acme,fornecido}.caddy`,
    `sem-certificado.pem`, o ramo de produção de `scripts/vault_inicializar.sh` (e `LUPA_COMPOSE`) e
    a seção do piloto de `.env.example`. O `Caddyfile` importa só `modos/interno.caddy` (sem
    `LUPA_TLS_MODO`) e `validar_caddyfile.sh` valida esse modo único. Sem teste novo
    (infraestrutura).
  - Comandos: `bash intranet/api/scripts/validar_caddyfile.sh` → `caddy validate: ok`;
    `docker compose up -d --build --wait`, proxy recriado, `bash scripts/vault_inicializar.sh` →
    Transit e AppRole prontos; `GET /saude` → tudo `ok`; `verificar_cabecalhos.py --url
    https://proxy:8443 --exigir` → `ok em 4 rotas`; `docker compose --profile '*' config
    --services` → `api db e2e front minio minio-init proxy redis vault worker` (os de D22 mais
    `redis`, que sai em T3.8); volumes `db-dados`, `minio-dados`, `vault-dados`.
  - Fechamento da fase 2, depois do rebuild: pipeline 604 passed, 1 failed
    (`test_rls_ativa_em_todas_as_tabelas_com_gabinete`, linha de base), cobertura 93,98%;
    intranet 282 passed, 1 failed (`test_remove_dados_em_cascata_do_processo`, linha de base),
    3 deselected, cobertura 98,71%; `ruff check`, `ruff format --check` e `mypy` nos dois
    pacotes: ok. Front não alterado.

## Fase 3 — Data Vault e gabinete único

- [x] **T3.1** `dominio/chaves.py`. A1. D4, D5. RES-02.
  - `chave_hash`, `chave_link`, `hash_diff` (SHA-256 do JSON canônico; HMAC-SHA-256 com a DEK
    quando o satélite é cifrado), `hmac_processo`, `normalizar_cnj`, `normalizar_hash` e
    `json_canonico`. Teste: `pipeline/tests/dominio/test_chaves.py` (21 testes, unitários).
  - Comando: `docker compose run --rm --no-deps worker python -m pytest -c pipeline/pyproject.toml
    pipeline/tests/dominio/test_chaves.py --no-cov -q` (código montado em `/app/pipeline`).
  - Vermelho (assinaturas vazias): `17 failed, 4 passed` (os 4 comparam dois valores do esboço
    entre si). Verde: `21 passed`. `ruff check`, `ruff format --check` e `mypy` nos dois arquivos:
    ok.
- [x] **T3.2** `dominio/tabelas.py` no Data Vault, `migrations/esquema_v0001.py`, `versions/v0001_data_vault.py` e `test_migracao_0001`; remoção das revisões `v0001` a `v0012`. D3, D6, D7, D8, D9, D18. RES-02, RES-03, RES-13.
  - `tabelas.py` declara as 56 tabelas como `Table` do SQLAlchemy Core (13 hubs, 15 links, 28
    satélites) com `info` para a gravação; `esquema_v0001.py` cria tabelas, índices, CHECKs
    gerados dos enums, `<tabela>_imutavel`, `lupa_bloquear_alteracao`,
    `lupa_fato_exige_evidencia`, `lupa_descartar_processo` (A13, passos 2 a 6), as 20 views e as
    permissões de `lupa_app`. Enums: `PapelUsuario` sem administrador, `StatusProcesso` sem
    `bloqueado`, `ClasseProcessual`, `Polo` e `QualidadeParte` (D15); os jurídicos ficam da 0.1
    até a fase 4. `dominio/sessao.py` fica só com `assumir_papel_aplicacao`.
  - Saíram com a funcionalidade: as revisões `v0001` a `v0012`, os `esquema_v0002` a `v0010`,
    `pipeline/tests/seguranca/test_migracao_0010.py`, os testes de RLS, de migração e de nome
    real de `pipeline/tests/dominio/test_banco.py` (o de fato sem evidência e o de nome em coluna
    autorizada foram reescritos em `test_migracao_0001.py`; os de UPDATE em achado e DELETE em
    `fato_evidencia` passam a ser cobertos pelo teste de imutabilidade de T3.3). Os testes de
    repositório que ficam em `test_banco.py` são reescritos em T3.10.
  - Desvios registrados no plano: `bloqueado_ate` nulo marca o zeramento das falhas por login
    certo (sem `DELETE`); `v_bloqueio_login` traz `zerado_em` e `falhas`; `v_fato.vigente` é
    "tem evidência vigente"; as duas anotações usam o rótulo de cifra `anotacao.texto`;
    `load_dts` sempre do banco; `papel` de sessão e desafio com CHECK de `PapelUsuario`.
  - Comando: `docker compose run --rm --no-deps worker python -m pytest -c pipeline/pyproject.toml
    pipeline/tests/dominio/test_migracao_0001.py --no-cov -q`.
  - Vermelho (upgrade só com os hubs): `8 failed, 3 passed` (os 3 olham só o modelo ou os hubs).
    Verde: `11 passed`. `ruff check`, `ruff format --check` e `mypy` nos arquivos da tarefa: ok.
- [x] **T3.3** `dominio/gravacao.py` e `dominio/visoes.py`; teste de imutabilidade sob `lupa_app`. A2. D6, D13. RES-13.
  - `gravar_hub`, `gravar_link`, `gravar_satelite` e `chave_do_hub` (A2); `visoes.py` mapeia as
    20 views em classes `Visao*` de metadados próprios, que recusam gravação pelo ORM. Testes:
    `pipeline/tests/dominio/test_gravacao.py` (21) e `pipeline/tests/dominio/test_visoes.py` (5).
  - Comando: `docker compose run --rm --no-deps worker python -m pytest -c pipeline/pyproject.toml
    pipeline/tests/dominio/test_gravacao.py pipeline/tests/dominio/test_visoes.py --no-cov -q`.
  - Vermelho (assinaturas vazias): `24 failed, 3 passed` (os 3 são os de `lupa_app` sem UPDATE e
    DELETE, que dependem só das permissões criadas em T3.2). Verde: `27 passed`. `ruff check`,
    `ruff format --check` e `mypy` nos quatro arquivos: ok.
- [x] **T3.4** Enum `PapelUsuario` com dois papéis; `acesso/` sobre hubs e satélites; `criar_desembargador.py`. A14. D11. RF-ACE-01 a 05.
  - `acesso/{papeis,sessoes,servico,autorizacao,rotas,instalacao}.py` reescritos: dois papéis
    sem escopo de gabinete; leitura por `v_usuario`, `v_sessao`, `v_desafio_mfa` e
    `v_bloqueio_login`; gravação por `dominio.gravacao`; `ultimo_acesso_em` só a cada 60 s
    (D11); falhas e bloqueios em `hub_chave_login` com zeramento por linha nova; a API cria só
    assessor e a gestão alcança só assessores; ids em hex (D12). `criar_admin.py` virou
    `intranet/api/scripts/criar_desembargador.py` (`LUPA_DESEMBARGADOR_USUARIO` e `_SENHA`, também
    em `.env.example`). `tratar_erro_acesso` passou de `api/app.py` para `acesso/erros.py`.
    `exige_processo` lê `v_processo` pelo id em hex; a abertura da DEK entra em T3.5.
  - Ajustes fora de `acesso/` necessários ao login: `auditoria/eventos.py` (`NovoEvento` com
    `hk_usuario` e `hk_processo`, sem `gabinete_id`; sai `GABINETE_CRIADO`) e
    `auditoria/registrador.py` (cadeia única em `link_evento_auditoria`, A15 passos 2 a 6);
    `apoio_comum.py` ganhou `UsuarioTeste` (com `hk`), `semear_usuario` e `eventos_do_banco`
    sobre `v_auditoria`; o `conftest.py` da intranet monta `app_teste` só com as rotas de acesso.
  - Testes removidos com a funcionalidade: gabinetes, administrador, escopo de gabinete e RLS
    (`test_usuarios.py`, `test_unidades.py`, `test_banco_acesso.py`) e a lista de gabinetes
    (`test_sessao_e_gabinetes.py`, renomeado `test_sessao.py`). Testes novos:
    `test_ultimo_acesso_so_ganha_linha_nova_depois_de_60_segundos`,
    `test_login_certo_zera_as_falhas_do_nome`, os de gestão por dois papéis, os de
    `criar_desembargador` e `intranet/api/tests/auditoria/test_registrador.py`.
  - Comando: `docker compose run --rm --no-deps api python -m pytest -c
    intranet/api/pyproject.toml intranet/api/tests/acesso
    intranet/api/tests/auditoria/test_registrador.py --no-cov -q`.
  - Vermelho: os testes reescritos não importam sobre o código da 0.1 (sem `UsuarioTabela`); com
    o código novo e seis mutações (sem o intervalo de 60 s, sem zerar falhas, sem a recusa de
    segundo desembargador, assessor com `GERIR_ASSESSOR`, logout sem revogar, API criando
    desembargador): `8 failed, 48 passed`; registrador sem conferir hash e sem encadear:
    `2 failed`. Verde: `56 passed` e `2 passed`. `ruff check`, `ruff format --check` e `mypy`
    nos arquivos da tarefa: ok.
- [x] **T3.5** Cofre com chave única, DEK em `sat_processo_chave`, caminho de objeto novo; cifra dos satélites. D14. RF-SEG-01, RF-SEG-02, RES-08.
  - `seguranca/cofre.py` com `CHAVE_DADOS = "lupa"` (saem as chaves por gabinete e de
    identidades); `contexto.py` indexado pelo `hk_processo` (bytes); `envelope.py` com o
    `hk_processo` de 32 bytes no cabeçalho e no AAD do campo `lupa1:`; `seguranca/chaves.py`
    reduzido a `criar_chave_processo` (DEK nova em `sat_processo_chave`) e `carregador_sql`
    (lê `v_processo`); `ingestao/storage.py` com `chave_objeto(hk_processo, sha256)` →
    `processo/<hex>/<sha256>` e `prefixo_processo`; `exige_processo` abre a DEK
    (`ativar_processo`). `gravar_satelite` usa HMAC com a DEK do processo ativo nos satélites
    cifrados (D5). `vault/politicas/lupa.hcl` só com a chave `lupa`; `vault_inicializar.sh` cria
    `lupa`. `apoio_comum.py` ganhou `criar_processo` e `criar_pagina` no modelo novo e limpa o
    contexto de cifra padrão a cada teste.
  - Saíram com a funcionalidade: a rotação por gabinete, a cifra de identidades de réu e os
    testes deles (`test_cofre.py`, `test_dado_em_claro_recusado.py`). O contrato completo do
    cofre (rotacionar, recifrar, destruir) fica só no cofre em memória: a política nova não deixa
    a aplicação apagar a chave `lupa` do Vault.
  - Testes novos: `pipeline/tests/seguranca/test_cifra_satelites.py` (9),
    `intranet/api/tests/acesso/test_autorizacao.py` (3) e os de `hk` no campo, chave `lupa` e
    caminho do objeto em `test_envelope.py`, `test_cofre.py` e `test_storage.py`.
  - Comandos: `docker compose run --rm --no-deps worker python -m pytest -c
    pipeline/pyproject.toml pipeline/tests/seguranca/test_cifra_satelites.py
    pipeline/tests/seguranca/test_dado_em_claro_recusado.py pipeline/tests/seguranca/test_envelope.py
    pipeline/tests/seguranca/test_cofre.py pipeline/tests/ingestao/test_storage.py --no-cov -q` e
    `docker compose run --rm --no-deps api python -m pytest -c intranet/api/pyproject.toml
    intranet/api/tests/acesso/test_autorizacao.py --no-cov -q`.
  - Vermelho (os testes novos não importam sobre o código de T3.4; com o código novo e quatro
    mutações: `hash_diff` sem DEK, caminho com `gabinete/`, DEK envolvida por outra chave,
    cabeçalho sem conferir 32 bytes): `7 failed, 36 passed, 1 skipped`; `exige_processo` sem
    `ativar_processo`: `1 failed, 2 passed`. Verde, depois de `docker compose build api worker`,
    cada arquivo sozinho: `9`, `6`, `12`, `7 passed, 1 skipped`, `9` e `3 passed`. O pulado é o
    contrato com o Vault real: o Vault de desenvolvimento ainda tem a política da 0.1 (sem a
    chave `lupa`) até `bash scripts/vault_inicializar.sh` rodar de novo (passo 3 da execução do
    plano), o que não foi feito porque o script regrava o `.env`.
  - `test_gravacao.py` (T3.3) passou a contar linhas pelo `hk` do teste: com `criar_processo`
    gravando com commit em outros testes, a contagem da tabela inteira deixava de ser estável.
  - T3.14 verificou o retorno 503 da rota de saúde com o cofre selado. T3.16 completou a varredura do conteúdo cifrado pela API em `intranet/api/tests/seguranca/test_cifra_banco.py`.

### Notas para as próximas tarefas

- Gravação (`lupa_pipeline.dominio.gravacao`): `gravar_hub(session, tabela, chave, origem)`
  recebe o dicionário com as colunas da chave de negócio (normaliza `numero_cnj`, `sha256`,
  `token_sha256`, `chave`) e devolve o `hk`; `chave_do_hub` calcula sem gravar;
  `gravar_link(session, tabela, {coluna_hk: hk}, origem)` devolve o `hk` do link;
  `gravar_satelite(session, tabela, hk_pai, atributos, origem)` exige todas as colunas de
  negócio e devolve se inseriu. Satélites com coluna cifrada pedem o processo ativo no contexto
  de cifra (`ativar_processo` ou `criar_chave_processo`). Links não historizados
  (`link_evento_auditoria`, `link_chamada_modelo`) são `insert` direto, como em
  `auditoria/registrador.py`. Nada de `UPDATE` ou `DELETE`.
- Leitura (`lupa_pipeline.dominio.visoes`): uma classe `Visao*` por view (`VisaoProcesso`,
  `VisaoArquivo`, `VisaoPagina`, `VisaoFato`...); `id` é o hex do `hk`. Ao reler uma view
  depois de gravar na mesma transação, use `atual(select(...))` (o mapa de identidade guardaria a
  linha antiga). As colunas de cada view estão em `migrations/esquema_v0001.py`
  (`VISOES_POR_HUB`, `VISOES_DE_HISTORICO`).
- Tabelas em `lupa_pipeline.dominio.tabelas` (objetos `Table`, com `info` de tipo, chave, pai,
  subchave multiativa e `sempre_insere`). Mudar enum jurídico na fase 4 muda os CHECKs da mesma
  revisão `v0001` (gerados de `checar_enum`).
- Testes: `engine_teste` é um database `lupa_teste_sessao_<pid>` migrado; `banco_vazio(sufixo)`
  cria outro database vazio. Em `apoio_comum`: `criar_processo(sessao, classe=..., criador=...)`
  (hub, dados, estado `criado` e DEK), `criar_pagina(sessao, hk_processo, texto)` (arquivo,
  links, extração e saneamento cifrados), `semear_usuario`, `UsuarioTeste(hk, id, nome, papel,
  segredo)` e `eventos_do_banco(engine, usuario_id=<hex>, ...)` sobre `v_auditoria`. Na intranet,
  `criar_usuario_teste(engine, papel, mfa=..., troca_senha=...)` e `logar` como antes, sem
  gabinete. Contagens em teste filtram pelo `hk` do próprio teste: `criar_processo` com commit
  deixa linhas no banco da sessão.
- Provisórios até a suíte voltar (D23): `pipeline/tests/conftest.py` e
  `intranet/api/tests/conftest.py` carregam só `apoio_comum` (`apoio_ingestao` volta em T3.7 a
  T3.9, com `criar_assessor`); o `app_teste` da intranet monta só as rotas de acesso, sem
  `create_app` nem middlewares (volta em T3.14, que também devolve `/auditoria` e
  `/processos/{id}` ao teste de troca de senha obrigatória).
- Quebrados à espera das próximas tarefas (não importam ou não funcionam sobre o modelo novo):
  `dominio/{esquemas,repositorios,correcoes}.py` (T3.10), toda a `ingestao/` exceto `storage.py`
  (T3.7 a T3.10; `recepcao.py` e `worker.py` ainda usam `chave_objeto` com gabinete),
  `seguranca/descarte.py` (T3.13), `intranet/api/src/lupa_intranet/api/` (`app.py`, rotas e
  middleware; T3.6 e T3.11 a T3.14; `request.state.processo` agora é o `hk_processo`),
  `auditoria/{consulta,rotas}.py` e o resto da auditoria (T3.11; `AcaoAuditoria` ainda tem
  `ADMIN_ACESSO_CONTEUDO`, `IDENTIDADE_LIDA` e `CHAVE_ROTACIONADA`), `agente/` (T3.12),
  scripts de `pipeline/scripts/` e `intranet/api/scripts/` além dos de instalação (T3.15) e os
  testes deles, inclusive o restante de `pipeline/tests/dominio/test_banco.py`.
- O Vault de desenvolvimento precisa de `bash scripts/vault_inicializar.sh` para ganhar a chave
  `lupa` e a política nova; o banco de desenvolvimento continua na 0.1 (nenhuma migração rodou
  nele).
- [x] **T3.6** Processos: cadastro com classe, lista, responsáveis, sem `materia`, `sigiloso` e 403. D12, D15 (`ClasseProcessual`, `StatusProcesso`). RF-PRO-01 a 04.
  - `api/rotas/processos.py` reescrito sobre `v_processo`, `v_arquivo`, `v_responsavel` e
    `v_usuario`: `POST /processos` com `classe` do enum `ClasseProcessual` (corpo sem `materia`,
    `sigiloso` e `gabinete_id`; campo extra dá 422) grava hub, dados, estado `criado` e DEK;
    número repetido dá 409 com `processo_id` do existente; o assessor que cadastra vira o
    responsável inicial (o trigger `processo_responsavel_inicial` da 0.1 passou à aplicação). A
    lista é a mesma para todos, com classe, resumo da ingestão (só `processo_id`, `estado` e
    `criado_em` de `v_arquivo`, sem decifrar nada) e responsáveis vigentes; `meus=true` filtra
    pela vigência. Responsáveis mudam por linha nova de `sat_processo_responsavel_vigencia`, só
    pelo desembargador, serializados por `pg_advisory_xact_lock` (o `FOR UPDATE` da 0.1 exige
    `UPDATE`, que `lupa_app` não tem). Ids em hex (D12); o número CNJ volta com máscara por
    `dominio.cnj.formatar_numero_cnj` (o hub guarda só os 20 dígitos).
  - Ajustes fora de `processos.py` necessários à rota: `api/middleware.py` grava o evento
    automático com `hk_usuario` e `hk_processo` (saem `gabinete_id`, `definir_contexto` e o
    `admin_acesso_conteudo`); o `app_teste` da intranet passou a montar as rotas de processos e
    a auditoria automática; `apoio_comum.criar_processo_teste(engine, autor)` grava com commit.
  - Testes reescritos: `intranet/api/tests/api/test_processos.py` (5),
    `test_processos_lista.py` (14) e `test_responsaveis.py` (2); novo
    `pipeline/tests/dominio/test_cnj.py` (4). Saíram com a funcionalidade: isolamento por
    gabinete, administrador e o teste da migração `0010` dos responsáveis
    (`test_migracao_preserva_responsavel_dos_processos_existentes`).
  - Comandos: `docker compose run --rm --no-deps api python -m pytest -c
    intranet/api/pyproject.toml intranet/api/tests/api/test_processos.py
    intranet/api/tests/api/test_processos_lista.py intranet/api/tests/api/test_responsaveis.py
    --no-cov -q` e `docker compose run --rm --no-deps worker python -m pytest -c
    pipeline/pyproject.toml pipeline/tests/dominio/test_cnj.py --no-cov -q` (código montado em
    `/app`).
  - Vermelho: os testes novos não importam sobre a rota da 0.1 (`pode`, `ProcessoTabela`); com a
    rota nova e cinco mutações (sem responsável inicial, 409 sem `processo_id`, corpo com
    `extra="ignore"`, transferência sem linha `vigente = false`, evento automático sem
    `hk_processo`): `8 failed, 13 passed`. Verde, cada arquivo sozinho: `5`, `14`, `2` e `4
    passed`; `intranet/api/tests/acesso` e `test_registrador.py` continuam `61 passed`. `ruff
    check`, `ruff format --check` e `mypy` nos arquivos da tarefa: ok.
- [x] **T3.7** Recepção e estado da ingestão em satélites de `hub_arquivo`. A3. D9. RF-ING-01, 02, 06.
  - Upload, estado e auditoria são confirmados juntos. A consulta de estado funciona sem abrir
    a DEK. A trava por processo também cobre o descarte e envios simultâneos.
  - Vermelho observado no upload (405), na triagem de tipo inválido e na leitura de estado sem
    DEK. Em contêineres avulsos com o código montado e PostgreSQL/MinIO reais,
    `python -m pytest -c pipeline/pyproject.toml pipeline/tests/ingestao/test_recepcao.py
    pipeline/tests/ingestao/test_repositorio.py --no-cov -q` passou em 18 casos. Na API,
    `python -m pytest -c intranet/api/pyproject.toml intranet/api/tests/ingestao/test_rotas.py
    --no-cov -q` passou em 9 casos, inclusive rollback se a auditoria falhar. As regressões de
    cadastro e listagem passaram em 19 casos. O teste da trava em duas conexões passou.
- [x] **T3.8** Worker sem Redis e RQ; remoção de `fila.py`, `redis` e `rq`. A4. D10. RF-ING-07, RES-07.
  - O worker mantém o advisory lock na mesma conexão usada por A5 e confirma a tentativa antes
    de processar. O segundo worker sai com código 1. Os quatro arquivos de dependências foram
    regenerados com `uv`. O Compose com o perfil `e2e` lista os nove serviços de D22.
  - O teste de recuo do relógio reproduziu um arquivo recebido que voltava à frente da fila
    mesmo depois do processamento. A revisão inicial ordena o instante de carga no PostgreSQL
    por pai e subchave quando o relógio recua.
  - Na imagem worker, `python -m pytest -c pipeline/pyproject.toml --no-cov -q
    pipeline/tests/ingestao/test_fila_banco.py pipeline/tests/dominio/test_gravacao.py
    pipeline/tests/dominio/test_migracao_0001.py pipeline/tests/unit/test_config.py`.
    Vermelho em quatro testes de configuração, dois da fila e um de ordenação. Verde em 46 casos.
- [x] **T3.9** Páginas, diagnóstico, lotes e peças em satélites (conteúdo jurídico ainda da 0.1). A5 passos 1 a 7. RF-ING-03.
  - O teste de A5 reproduziu a abertura de ZIP no processo do worker. Agora o filho isolado aplica os limites de inventário e expõe os membros temporários com modo 0600. `pytest pipeline/tests/ingestao/test_{sandbox,inventario,worker,processamento}.py --no-cov -q` passou nos 68 casos executados. O limite de escrita foi verificado em subprocessos com tetos de 0 e 4096 bytes.
  - Os testes que importavam os jobs de Redis falhavam na coleta. Na imagem do worker, test_worker.py passou nas recusas de PDF e ZIP e no limite real de memória. test_processamento.py, test_worker_extracao.py e test_observabilidade.py passaram nos 10 casos de lotes, cache entre DEKs, retomada e logs.
- [x] **T3.10** Evidências, fatos, achados e anotações em hubs, links e satélites; remoção de `reu`, `reu_identidade` e da pseudonimização. A5 passos 8 a 11, A11, A12. RF-FAT-01, RF-FAT-03, RF-PEC-02, RF-DOS-06.
  - A suíte que usava as tabelas da 0.1 falhou na coleta. Três testes de domínio no PostgreSQL e os testes de rotas de fatos e peças passaram. Conferem escopo, vigência, id estável, reprocessamento e anotação em fato e achado. A view v_achado_historico preserva a consulta às versões anteriores aprovada pelo usuário.
- [x] **T3.11** Auditoria como link não historizado, cadeia única, consulta, relatório de uso com custo. A15. D8, D26. RF-AUD-01 a 05.
  - `test_eventos_reais.py` reproduziu três falhas: a busca de texto no chat não emitia evento, o objeto de uma tentativa negada guardava o valor livre da URL e o log de acesso do Uvicorn expunha caminho e parâmetros. Após a correção, a busca identifica o processo, a tentativa registra o hash do identificador inválido e o log mantém IP, método, versão e status. A varredura também procurou nomes de arquivo, trechos, consulta, anotação, resposta e credenciais sintéticas. A bateria de auditoria, rotas de processo e chat passou nos 70 testes.
  - `python -m pytest intranet/api/tests/auditoria/test_{cadeia,consulta,custo}.py --no-cov`:
    o assessor recebia 404 e a tabela aceitava TRUNCATE. Após montar as rotas e proteger a
    cadeia, 35 testes passaram. O relatório consulta chamadas e tokens pela view.
    `test_carga.py` passou com um milhão de eventos e mediana inferior a 200 ms.
- [x] **T3.12** Conversa, mensagens, chamada ao modelo e processo em revisão. A16. D26. RF-CHA-06, 07, 08.
  - O POST do chat devolvia 404. Com as rotas e satélites em uso, o teste autenticado
    `tests/api/test_chat_limites.py` confirma que a segunda pergunta mantém a conversa e o
    contador de chamadas. `tests/api/test_revisao.py` cobre dois motivos de bloqueio, a
    recusa do assessor e a liberação pelo desembargador no estado anterior.
  - A auditoria guarda os hashes e tokens de cada chamada. O histórico decifra as mensagens
    e as citações da conversa do usuário. A bateria compartilhada com T4.12 passou em 63 casos.
- [x] **T3.13** Descarte. A13. RF-PRO-05.
  - `python -m pytest intranet/api/tests/seguranca/test_descarte.py --no-cov`
    contra PostgreSQL e MinIO. Vermelho: a rota devolvia 404. Verde: os três testes passaram,
    incluindo 403 para assessor, eliminação da DEK e repetição após falha no storage.
- [x] **T3.14** Rotas da API com ids em texto; remoção de `/gabinetes*`. D12, D27.
  - A coleta anterior ainda importava as tabelas da 0.1. Com create_app real, 12 testes de saúde, os 8 de fatos, peças, diagnóstico e visualizador e os 4 de auditoria e sessão passaram. Os esquemas também passaram nos 89 casos de hash público e estado de ingestão.
- [x] **T3.15** Scripts sem gabinete e administrador (`e2e_*`, `limpar_dev`, `calibrar`, `ponta_a_ponta`, `criar_usuario_banco`).
  - A calibração concorrente com o worker produziu a transição inválida de falho para quarentena. A trava da fila eliminou o processamento duplicado. A medição antes perdia um achado ao comparar três recorrentes com a mesma regra.
  - `pytest pipeline/tests/ingestao/test_calibracao.py pipeline/tests/sinteticos/test_comparacao_achados.py --no-cov -q` cobre a concorrência e o relatório. Nos três empacotamentos, a medição encontrou todos os eventos e os três achados esperados, com os mesmos valores e folhas.
  - `pytest intranet/api/tests/auditoria/test_limpar_dev.py intranet/api/tests/acesso/test_banco_acesso.py --no-cov -q` verificou o descarte seletivo e a criação de usuários. Os três scripts E2E semearam a stack usada nas dez capturas, com três processos cíveis marcados pela origem `scripts.e2e`.
- [x] **T3.16** Suíte completa verde nos dois pacotes. D23.
  - Na instalação 0.2 com serviços reais, `python -m pytest -c pipeline/pyproject.toml pipeline/tests` passou nos 697 testes (95,87%). `python -m pytest -c intranet/api/pyproject.toml intranet/api/tests` passou nos 262 testes (98,24%). A cifra em repouso foi conferida no banco e no storage. Os dois testes de modelo externo e o teste de carga usam marcadores próprios. A falha histórica da 0.1 permanece registrada em T1.7.

## Fase 4 — Conteúdo cível

- [x] **T4.1** Enums cíveis (`TipoPeca`, `TipoFato`, `OrigemPeca`, `Polo`, `QualidadeParte`, `MetodoClassificacao`). D15.
  - Os dois testes do vocabulário falharam com os tipos criminais da 0.1. Na imagem do worker,
    `python -m pytest pipeline/tests/dominio/test_enums_civeis.py pipeline/tests/dominio/test_esquemas.py --no-cov -q`
    passou nos 19 testes, incluindo o vínculo de fatos e achados ao sujeito por hash.
- [x] **T4.2** Sintéticos das cinco classes, com templates e gabarito. RNF-04, RNF-05.
  - O gerador anterior dependia de `Materia.CRIMINAL` e não aceitava a classe cível. No primeiro
    ciclo de regressão, duas páginas com colunas desiguais tiveram leitura invertida e o teste
    do texto fora da página leu somente a área visível. No worker,
    `python -m pytest pipeline/tests/sinteticos pipeline/tests/ingestao/test_extracao.py --no-cov -q`
    passou nos 104 casos dos sintéticos e nos oito da extração. Cada classe teve PDF e gabarito
    relido com qualificação, evidências literais, peças e resultados cabíveis.
  - A regressão `test_duas_colunas_sao_lidas_coluna_por_coluna` colocou o rodapé antes da coluna
    direita. O corte XY passou a conferir o vão entre a faixa e a linha anterior. Os 26 testes
    de páginas, colunas sintéticas e CLI passaram juntos no worker.
- [x] **T4.3** Classificação e fronteiras de peças cíveis. RF-PEC-01.
  - O caso cível substituiu as antigas expectativas de denúncia e defesa. test_tipos_civeis.py cobriu os tipos de peça. test_indice.py e test_fronteiras.py conferiram a segmentação, o título, a origem e a data com gabarito sintético.
- [x] **T4.4** Partes. A6 passos 1 e 2. RF-FAT-04.
  - Os modelos anteriores esperavam réu e pseudônimo. Os testes de qualificação e a integração em test_eventos_banco.py conferiram nome literal, polo, qualidade, evidência e persistência da identidade com DEK do processo.
- [x] **T4.5** Extratores de fatos cíveis. A6 passos 3 a 8. D17. RF-FAT-01, RF-FAT-02.
  - A comparação inicial encontrou divergências em OAB e procuração. Os 19 testes de test_eventos.py passaram com valores canônicos, offsets no texto original, bloqueio de trecho suspeito e preservação de marcos conflitantes.
- [x] **T4.6** Catálogo por classe e dados do CPC (`prazos_recursos.yaml`, `preparo.yaml`, `cabimento_art1015.yaml`). D16. RF-VAL-01.
  - As cinco consultas por classe falharam no catálogo por matéria da 0.1. No worker,
    `python -m pytest pipeline/tests/validacoes/test_catalogo_civel.py --no-cov -q` passou nos cinco casos da tabela 3.1.
- [x] **T4.7** Tempestividade. A7. RF-VAL-02.
  - A regra vazia falhou ao calcular o vencimento. O teste do decreto 5.123/2026 também acusou
    a ausência do feriado transferido para 30/10. No worker, `python -m pytest pipeline/tests/validacoes/test_tempestividade.py --no-cov -q`
    passou nos oito casos de prazo, feriado, suspensão, falta e conflito de fatos.
  - Regressão de recesso em 2030/31: o resultado anterior vencia em 26/12/2030. Com a repetição
    anual do art. 220, o vencimento passou a 27/01/2031. A suíte do catálogo passou nos 61 casos.
- [x] **T4.8** Preparo. A8. RF-VAL-03.
  - A regra vazia falhou ao avaliar comprovante, dispensa e gratuidade. No worker,
    `python -m pytest pipeline/tests/validacoes/test_preparo.py --no-cov -q` passou nos dez casos.
- [x] **T4.9** Representação. A9. RF-VAL-04.
  - A regra vazia falhou ao reconhecer o mandato. No worker,
    `python -m pytest pipeline/tests/validacoes/test_representacao.py --no-cov -q` passou nos dez casos, incluindo cadeias e ciclos.
- [x] **T4.10** Cabimento do agravo. A10. RF-VAL-05.
  - A regra vazia falhou ao identificar o inciso da decisão agravada. No worker,
    `python -m pytest pipeline/tests/validacoes/test_cabimento.py --no-cov -q` passou nos cinco casos.
- [x] **T4.11** Linha de comando das validações e `fatos_exemplo.json`. RF-VAL-06.
  - A CLI da 0.1 recusou `--classe apelacao_civel`. O worker executou
    `python -m lupa_pipeline.validacoes --fatos pipeline/tests/validacoes/fatos_exemplo.json --classe apelacao_civel --referencia 2026-10-20`.
    A saída reproduziu integralmente `achados_exemplo.json` e `python -m pytest pipeline/tests/validacoes --no-cov -q` passou nos 60 testes, incluindo a ida e volta pelo Data Vault.
- [x] **T4.12** Agente cível: prompt, recusa, ferramenta de cálculo, contexto sem pseudônimos, dossiê com partes. RF-CHA-01 a 05, RF-DOS-01 a 04.
  - A política anterior deixou passar dois pedidos de valoração cível no corpus de 30
    perguntas vedadas. O corpus cível passou nos critérios de 100% de recusa e até 10% de
    falsos positivos nas 30 permitidas. O prompt versão 2 usa nomes e polos do processo.
  - O dossiê liga cada parte e cada fato usado pelo achado à evidência de página. A bateria
    de agente, rotas de revisão e limites passou em 63 testes. Ruff e mypy passaram nos
    módulos e testes alterados.
- [x] **T4.13** Ponta a ponta de cada classe contra o gabarito; reprocessamento preserva correção. RF-ING-04, RF-ING-08, RNF-01, RNF-02.
  - RF-ING-08 passou por dez reinícios do worker com PostgreSQL e PDF sintético. Antes, a fila continuava vazia após mudar o catálogo. Agora o teste observa o sandbox, a classificação, os extratores e as validações e confirma que só as etapas dependentes se repetem. A evidência da correção, a anotação e a autoria sobreviveram às quatro mudanças. `pytest pipeline/tests/ingestao/test_reprocessamento.py pipeline/tests/ingestao/test_fila_banco.py --no-cov`: 3 passaram.
  - O teste passou da coleta interrompida por Redis a seis fluxos aprovados pela API, MinIO e worker PostgreSQL. Cada classe foi comparada com o gabarito folha a folha, inclusive peças, partes, valores, sujeitos e resultados. A apelação também passou em PDF liso. A correção foi relida após reprocessar e validada no catálogo.

## Fase 5 — Interface

- [x] **T5.1** Permissões e menu com dois papéis; remoção da tela de gabinetes. RF-ACE-03.
  - `npx vitest run src/lib/permissoes.test.ts src/lib/visualizacao.test.ts` expôs o terceiro papel no menu. Após a alteração, 7 testes passaram.
- [x] **T5.2** Tipos, API e rótulos cíveis; ids em texto. D12.
  - `npx vitest run src/lib/processos/processos.test.ts` passou nos 8 casos, incluindo as cinco classes, tipos de peça e valores de fatos.
- [x] **T5.3** Telas de processos: cadastro com classe, lista, dossiê com partes, validações, visualizador. RF-DOS-01 a 05.
  - As capturas mostraram referências em JSON e dois marcos com a mesma data remetiam à primeira folha. O teste de RF-VAL-01 em `correcao.test.ts` distingue a folha de cada marco do vencimento calculado. Os valores do cálculo, as fontes, os rótulos cíveis e a máscara CNJ estão legíveis no dossiê e nas validações.
  - RF-FAT-03 e RF-CHA-06. O formulário enviava a correção sem evidência e aceitava perguntas depois do teto. Após a correção, os quatro casos em `src/lib/processos/correcao.test.ts` e `src/lib/chat/limite.test.ts` passaram.
  - `npx vitest run src/lib/processos/cadastro.test.ts` confirmou pelo formulário o envio do número CNJ com a classe selecionada. O dossiê abre a página de cada fonte e as versões do fato conservam o mesmo identificador.
- [x] **T5.4** Telas de usuários e auditoria. RF-ACE-04, RF-AUD-04, RF-AUD-05.
  - `npx vitest run src/lib/auditoria/auditoria.test.ts src/lib/componentes/componentes.test.ts` passou nos 17 casos. Antes da mudança, os filtros rejeitavam ids hexadecimais e a mensagem de quebra não exibia a sequência.
- [x] **T5.5** `docker build --target verificacao intranet/web` verde.
  - `docker build --target verificacao intranet/web` terminou com código 0. Vitest passou nos 66 testes, Svelte Check não encontrou erros ou avisos e ESLint e Prettier passaram.

## Fase 6 — Regressão

- [x] **T6.1** Corpus de injeção e suíte do agente sobre os sintéticos cíveis. RF-ING-05, RF-CHA-05, RNF-03.
  - A suíte anterior referenciava tabelas e peças criminais. No worker, `pytest pipeline/tests/ingestao/test_injecao_corpus.py --no-cov -q` passou nos dois testes, com dez variantes, recall mínimo de 90% e até 5% de páginas limpas sinalizadas.
  - Na API, `pytest intranet/api/tests/agente/test_injecao_agente.py --no-cov -q` passou nos 11 testes. Dois autos com nove vetores passaram por ingestão, ferramentas, chat e dossiê. Nos 16 ataques roteirizados, nenhum achado foi criado ou suprimido, nenhum dado de outro processo foi exposto e nenhuma ferramenta embutida executou. Uma resposta legítima com citação literal foi aceita.
- [x] **T6.2** E2E e capturas adaptados. RNF-09.
  - `bash intranet/web/scripts/e2e.sh` passou nos 35 testes de navegador em 3 min 24 s. O fluxo percorreu os dois papéis, PDF de 500 MB, dossiê, destaque da página, correção com histórico, chat, auditoria e exportação de custo. A varredura de dez telas em cada tema registrou zero violações de acessibilidade graves ou críticas.
  - `bash intranet/web/scripts/capturas.sh` passou nos dez cenários de acesso e captura. As 11 imagens em `docs/imagens/` mostram autos sintéticos da classe apelação cível. O chat usa o cliente roteirizado. Cada script cria seu projeto Compose com PostgreSQL, MinIO e Vault e remove seus próprios volumes ao sair.
- [x] **T6.3** Cabeçalhos do proxy e saída de rede do worker. RF-SEG-03, RF-SEG-04.
  - verificar_cabecalhos.py --exigir passou nas quatro rotas HTTPS no proxy real. No worker, PostgreSQL aceitou a conexão interna e o kernel devolveu ENETUNREACH para TCP externo. verificar.sh executa a prova de isolamento.
- [x] **T6.4** `scripts/verificar.sh` completo verde.
  - `LUPA_EXIGIR_CABECALHOS=1 LUPA_VERIFICAR_E2E=1 bash scripts/verificar.sh` terminou com código 0 em uma instalação temporária da 0.2, com PostgreSQL, MinIO e Vault reais. As duas suítes passaram sem pulos (697 e 262), assim como os seis casos de ingestão, o corpus, o agente, o build do front, os cabeçalhos de quatro rotas, o isolamento do worker e os 35 cenários Playwright. O controle de integração falhou como esperado ao desligar cada dependência e ao simular erro no build.

## Fase 7 — Documentação e versão

- [x] **T7.1** `docs/arquitetura.md` e `docs/sistema/*.md`. RF-DOC-03.
  - A documentação descreve a conexão que detém a fila, a evidência na página, o sujeito do achado,
    o histórico e o descarte. A conferência de links e âncoras locais incluiu os nove documentos
    de arquitetura e sistema. Os exemplos de CLI usam o gabarito verificado em T4.11.
- [x] **T7.2** Guias do assessor e do desembargador. RF-DOC-01.
  - Os guias descrevem os dois papéis, trazem a conta de prazo de 03/08 a 24/08/2026, a fonte
    das citações, os limites do chat e o uso da auditoria. Links internos e destinos das capturas
    foram conferidos contra os arquivos da suíte de telas.
- [x] **T7.3** `docs/conformidade/CONFORMIDADE.md` e `docs/operacao/operacao.md`. RF-DOC-02.
  - O manual foi conferido contra os comandos de bootstrap, saúde, descarte e relatório. A minuta
    explicita o envio de dados identificáveis, inclusive sigilosos, os acessos do gabinete e a
    perda de conteúdo sem backup. Foram consultadas as fontes oficiais do CNJ, da LGPD e da ANPD.
    A revisão jurídica e o aceite são de responsabilidade humana.
- [x] **T7.4** ADRs 0013 a 0016 e `docs/decisoes/registro.md`.
  - O índice de ADRs liga as decisões substituídas às vigentes. O histórico registra a view
    adicional de versões do achado e a preservação de T1.7 com verificação de responsáveis na 0.2.
- [x] **T7.5** `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `docs/README.md`, `CHANGELOG.md` e versão `0.2.0`.
  - A leitura de TOML/JSON inicialmente encontrou cinco valores de versão 0.1.0. Os dois
    manifestos Python, o front e seus metadados de lock passaram na verificação de 0.2.0 e a
    API publicada por `app.openapi()` informou 0.2.0. Os quatro locks Python foram regenerados
    pelos comandos do alvo `make lock`, preservando os pins e hashes. A varredura conferiu
    108 referências locais em 23 documentos. Doze testes de saúde da API passaram.

## Fase 8 — Cadastro pelo arquivo

Execução do [plano de cadastro pelo arquivo](plano_cadastro_pelo_arquivo.md).

- [x] **T8.1** Ampliar os tipos de fato e preservar o criador no histórico de classe. RF-PRO-06, RF-FAT-01.
  - `pytest pipeline/tests/dominio/test_migracao_0002.py --no-cov` no worker com PostgreSQL. A asserção dos seis novos tipos falhou antes da revisão. Com a migração, 1 teste passou, incluindo subida, duas correções, descida e nova subida.
- [x] **T8.2** Identificar número CNJ e classe no PDF ou ZIP em sandbox. RF-PRO-01, RF-ING-02, RF-ING-04.
  - `pytest pipeline/tests/ingestao/test_identificacao.py --no-cov` no worker. No vermelho, 18 falhas e 5 testes passaram. Os 23 casos iniciais passaram, inclusive a sonda de rede e ambiente executada no subprocesso. Outros três casos reproduziram falhas de associação do CNJ ao rótulo e passaram após a correção, totalizando 26.
- [x] **T8.3** Criar ou localizar o processo pelo upload, tratar o complemento e retirar o cadastro manual. RF-PRO-01, RF-ING-01, RF-ING-02.
  - O primeiro teste de envio falhou com 405 em vez de 201. Na API, `pytest intranet/api/tests/api/test_cadastro_arquivo.py intranet/api/tests/auditoria/test_eventos_reais.py --no-cov` passou nos 15 casos com integração exigida. Dois envios simultâneos com o mesmo CNJ criaram um processo e dois arquivos.
- [x] **T8.4** Extrair, medir e exibir os fatos da capa com evidência nos autos sintéticos. RF-FAT-01, RF-FAT-03, RF-ING-08, RNF-02.
  - O gabarito tinha zero fatos na capa e o dossiê não tinha o campo `dados_capa`. Com as marcas de evidência e o extrator, `pytest pipeline/tests/sinteticos --no-cov` passou nos 106 testes. `test_capa.py` e `test_reprocessamento.py` conferem os offsets, a janela de páginas, a coexistência de fontes e a preservação da revisão humana.
  - `pytest pipeline/tests/ingestao/test_calibracao.py --no-cov` mediu o PDF liso, o PDF com índice e o ZIP. Com a semente 88, o recall dos eventos e das fronteiras foi de 100% nos três formatos e a precisão de datas atingiu a meta de 99%. Na API, `test_ponta_a_ponta.py` confronta as cinco classes com os gabaritos no PostgreSQL e no MinIO.
  - O PDF liso da semente de referência `semente_01`, regenerado com a nova capa, terminou em 797,46 s para 198 páginas. O banco registrou os seis tipos da capa. A medição encontrou 18 de 18 eventos, 8 de 8 datas (100% de precisão e recall), 44 de 44 fronteiras e tipos de peça e zero evidências divergentes do trecho literal.
  - O teste de injeção do dossiê marcou os novos valores da capa como texto livre. Após exigir correspondência de cada valor com o gabarito, o fato vigente, a página, o intervalo e o hash da evidência, `pytest intranet/api/tests/agente/test_injecao_agente.py -k dossie_do_processo_sintetico --no-cov` passou com PostgreSQL e MinIO. A varredura de texto livre continua a cobrir os demais campos.
- [x] **T8.5** Corrigir a classe, preservar a autoria e recalcular os achados. RF-PRO-06.
  - `pytest intranet/api/tests/api/test_classe.py --no-cov` respondeu 404 antes da rota. Os três casos passaram com a nova rota, inclusive os dois papéis, repetição sem nova linha e recusa após descarte. A bateria com as regressões de lista, responsáveis, abertura e upload passou nos 28 testes.
- [x] **T8.6** Enviar os autos pela interface, completar a identificação e conferir a ficha no cabeçalho. RF-PRO-01, RF-PRO-06, RF-FAT-04.
  - Os quatro casos de `cadastro.test.ts` falharam antes da implementação e passaram com o envio pelo mesmo `File` e o cabeçalho com evidências. `docker build --target verificacao intranet/web` passou em lint, formatação, tipagem e 75 testes.
  - `bash intranet/web/scripts/e2e.sh` passou nos 36 testes em Chromium, incluindo complemento, cadastro automático, anexo, duplicata e correção de classe. Na repetição com a imagem final, os 36 testes passaram em 3,7 min. O envio de 500 MB levou 13,7 s e o maior intervalo entre quadros foi de 17 ms. O axe percorreu dez telas em cada tema com zero violações graves ou críticas.
- [x] **T8.7** Atualizar arquitetura, decisão, guia, capturas e documentação técnica. RF-DOC-01, RF-DOC-03.
  - `bash intranet/web/scripts/capturas.sh --grep 'cadastro pelo arquivo e cabeçalho do processo' --no-deps` gerou as duas imagens do guia em uma stack sintética. A revisão visual conferiu o seletor de arquivo, o botão de correção de classe, as partes com polo e os seis campos com links. A conferência encontrou os 102 destinos de links locais nos 15 documentos alterados.

### Verificação integrada da fase 8

- `docker compose up -d --build --wait` subiu os sete serviços de desenvolvimento. A aplicação de `alembic upgrade head` no contêiner da API e a consulta `alembic current` confirmaram `0002 (head)`.
- No `scripts/verificar.sh`, Ruff, formatação e mypy estrito passaram nos dois pacotes. A pipeline passou nos 728 testes com 95,69% de cobertura, e a API passou nos 272 selecionados com 98,25%. A configuração padrão da API exclui três testes marcados como `carga` ou `llm`.
- `LUPA_EXIGIR_CABECALHOS=1 bash scripts/verificar.sh` terminou com código 0. Passaram os seis testes de ingestão ponta a ponta, o build do front, os cabeçalhos de quatro rotas e o isolamento de rede do worker. O corpus detectou 16 de 16 injeções textuais, com zero falsos positivos. Nos 16 cenários do agente com cliente roteirizado, houve zero vazamentos e zero instruções embutidas executadas. A suíte Playwright rodou separadamente pelo comando de T8.6.

## Fase 9 — Remoção do Vault e da cifra

Execução do [plano de remoção do Vault](plano_remocao_vault.md).

- [x] **T9.1** Escrever o teste vermelho de armazenamento sem cofre e criar a migration `v0003` com teste. RF-SEG-01. D5.
  - `pytest pipeline/tests/dominio/test_migracao_0003.py pipeline/tests/seguranca/test_sem_cofre.py --no-cov` no worker. No vermelho, contra o código anterior, 11 falhas e nenhum pulado (revisão `0003` inexistente, `hash_nome` ausente, módulos de cifra presentes, coluna sem processo ativo recusada). Com a revisão e o código sem cifra, 11 testes passaram com `LUPA_EXIGIR_INTEGRACAO=1`.
- [x] **T9.2** Gravar e ler conteúdo sem cifra: tipos de coluna, `hash_diff`, `chave_nome` e storage sem envelope. RF-SEG-01. D3, D7.
  - Os testes de `test_sem_cofre.py` sobre `hash_nome`, `hash_diff`, storage em memória e colunas em claro passaram. `test_chaves.py`, `test_recepcao.py`, `test_processamento.py` e `test_storage.py` passaram a fixar o conteúdo em claro (D3, D7).
- [x] **T9.3** Retirar o contexto de DEK e o cofre da pipeline e da intranet; saúde sem cofre e descarte com o id do processo. RF-SEG-01, RF-SEG-02. D4, D6.
  - Na API, `test_saude.py` (sem `cofre`, 503 quando o MinIO falha), `test_descarte.py` (`objeto_id` igual ao id do processo) e `test_rotas.py` passaram. Os cinco arquivos de teste da cifra saíram com o código (D1). A pipeline passou nos 702 testes com 95,25% de cobertura e a API nos 262 com 98,23%.
- [x] **T9.4** Retirar o Vault do compose, dos scripts, do `.env.example` e do E2E. RNF-07, RES-08. D1, D2.
  - `bash scripts/verificar.sh` terminou com código 0, sem o serviço `vault`: ingestão ponta a ponta (6), regressão de injeção (16 de 16, zero falso positivo), front, cabeçalhos em 4 rotas, isolamento do worker e 16 cenários do agente sem vazamento. `bash intranet/web/scripts/e2e.sh` passou nos 36 testes em Chromium, numa stack sem Vault.
- [x] **T9.5** Atualizar documentação, ADR 0018, registro de decisões, `CLAUDE.md` e `CHANGELOG.md`. RF-SEG-01, RES-08. D1 a D7.
  - A conferência de links locais nos 21 documentos alterados não achou link quebrado.

## Fase 10 — Front em Django

Execução do [plano do front em Django](plano_front_django.md). Um único PR para todas as tarefas
(fases 1 a 11 do plano). "Pronto quando", salvo indicação: suíte do pacote verde no contêiner
depois do rebuild, `ruff check`, `ruff format --check` e `mypy --strict` limpos; mudança em
`lupa_api` roda também a suíte da pipeline e a de `lupa_web`.

- [x] **T10.1** Renomear `lupa_intranet` para `lupa_api` e mover `limpar_dev.py`. RES-12. Fase 1; P1.
  - Vermelho: `pipeline/tests/unit/test_dependencias.py::test_pipeline_nao_importa_lupa_api_nem_lupa_web` falha (pacote ainda se chama `lupa_intranet` e `pipeline/scripts/limpar_dev.py` importa a API).
  - Verde: `git mv` do pacote, imports, `resources.files`, `pyproject.toml`, Dockerfile, scripts; `limpar_dev.py` e seu teste para `intranet/api/`.
  - Limpeza: nenhuma.
  - Comando: `docker compose exec worker python -m pytest -c pipeline/pyproject.toml
    pipeline/tests/unit/test_dependencias.py --no-cov -q`. Vermelho (pacote renomeado, com
    `pipeline/scripts/limpar_dev.py` importando `lupa_api`): `1 failed, 1 passed`. Verde (script
    em `intranet/api/scripts/`, teste em `intranet/api/tests/unit/test_limpar_dev.py`): `2 passed`.
  - Suítes com `LUPA_EXIGIR_INTEGRACAO=1`: pipeline `702 passed`, cobertura 95,25%; intranet/api
    `262 passed, 3 deselected`, cobertura 98,23%.
- [x] **T10.2** Gravar `record_source` `api.*` nas linhas novas e listar os dois prefixos na auditoria. RES-12. Fase 1; D9.
  - Vermelho: `intranet/api/tests/auditoria/test_registrador.py::test_evento_novo_grava_record_source_api` e `intranet/api/tests/auditoria/test_consulta.py::test_auditoria_lista_eventos_com_record_source_antigo_e_novo`.
  - Verde: constantes `ORIGEM` e filtros por `record_source`.
  - Limpeza: nenhuma.
  - Nenhuma consulta da API filtra por `record_source`; o segundo teste fixa que eventos
    `intranet.auditoria` e `api.auditoria` aparecem juntos na lista. `intranet.anotacao`
    (`api/rotas/achados.py`) também passa a `api.anotacao` (D9 cobre todo prefixo `intranet.*`):
    `intranet/api/tests/ingestao/test_validacoes_api.py::test_anotacao_nova_grava_record_source_api`,
    vermelho `1 failed` (`['intranet.anotacao'] == ['api.anotacao']`), verde `1 passed`.
  - Imports de `intranet/api/scripts/limpar_dev.py` e `e2e_preparar.py` reordenados (I001
    consequência do rename: `lupa_api` passou a primeiro partido).
  - Comando: `docker compose exec api python -m pytest -c intranet/api/pyproject.toml
    intranet/api/tests/auditoria/test_registrador.py::test_evento_novo_grava_record_source_api
    intranet/api/tests/auditoria/test_consulta.py::test_auditoria_lista_eventos_com_record_source_antigo_e_novo
    --no-cov -q`. Vermelho: `2 failed` (`'intranet.auditoria' != 'api.auditoria'`). Verde:
    `2 passed`.
  - Suítes com `LUPA_EXIGIR_INTEGRACAO=1`: pipeline `702 passed`, cobertura 95,25%; intranet/api
    `265 passed, 3 deselected`, cobertura 98,23%.
- [x] **T10.3** Criar o pacote `lupa_web` sem banco, a imagem e o serviço `front` Python. RES-12, RNF-08. Fase 2; D1, D4, D6, D12.
  - Vermelho: `intranet/web/tests/unit/test_configuracao.py::test_lupa_web_nao_configura_banco` e `intranet/web/tests/unit/test_dependencias.py::test_lupa_web_nao_importa_lupa_api_nem_lupa_pipeline`.
  - Verde: `pyproject.toml`, requirements por `make lock`, `configuracao.py`, `asgi.py`, `urls.py`, Dockerfile, serviço `front` no compose, etapa `web` em `scripts/verificar.sh`. O SvelteKit fica no repositório até T10.16, fora do compose.
  - Limpeza: nenhuma.
  - O Dockerfile Python substitui `intranet/web/Dockerfile` (contexto na raiz, como `api`); o
    serviço `front` passa a ser o Django na porta 8000, e o `reverse_proxy` do Caddyfile vai a
    `front:8000`. O SvelteKit (`src/`, `e2e/`, `package*.json`, `Caddyfile`) fica só como código
    a remover na T10.16; `intranet/web/scripts/e2e.sh` deixa de funcionar até a T10.15.
  - Django 5.2.1, httpx 0.28.1, WhiteNoise 6.8.2, segno 1.6.1, uvicorn 0.34.0; alvo `lock` do
    `Makefile` com as duas linhas de `intranet/web`. Com `DATABASES = {}` o Django põe o motor
    `django.db.backends.dummy` em `default`; o teste confere isso. `/saude` e uma página inicial
    mínima até a T10.6. Imagem `read_only`: caches de pytest, coverage, mypy e ruff em `/tmp`.
    `SECRET_KEY` de `LUPA_WEB_CHAVE_SECRETA`, aleatória por processo quando ausente.
  - Comando: `docker compose exec front python -m pytest -c intranet/web/pyproject.toml
    intranet/web/tests/unit/test_configuracao.py::test_lupa_web_nao_configura_banco
    intranet/web/tests/unit/test_dependencias.py::test_lupa_web_nao_importa_lupa_api_nem_lupa_pipeline
    --no-cov -q`. Vermelho: `ImportError: No module named 'lupa_web.configuracao'`. Verde:
    `2 passed`; suíte de `lupa_web` `9 passed`, cobertura 100%.
- [x] **T10.4** Cliente da API com repasse de cookie, IP e desvios 401/403/falha. RF-INT-03. Fase 2; A1, D3, D13.
  - Vermelho: `intranet/web/tests/unit/test_cliente_api.py::test_cookie_da_api_e_repassado_e_set_cookie_volta`, `::test_x_forwarded_for_e_repassado`, `::test_api_fora_do_ar_mostra_servico_indisponivel`.
  - Verde: `cliente_api.py`.
  - Limpeza: nenhuma.
  - `chamar()` usa um `httpx.AsyncClient` único, criado na primeira chamada e fechado no
    `lifespan.shutdown` do `asgi.py`, com pote de cookies que recusa tudo (o cookie de um usuário
    não vai no pedido de outro). Sem `X-Forwarded-For` vai o `REMOTE_ADDR`. Os desvios são
    exceções (`ApiIndisponivelError`, `SessaoExpiradaError`, `AcessoNegadoError`) tratadas pelo
    middleware `DesviosDaApi`, que também copia todo `Set-Cookie` da API, inclusive no 401. HTMX
    com 401: status 200 e `HX-Redirect: /login`. Páginas `erros/servico_indisponivel.html` e
    `erros/acesso_negado.html` mínimas até a T10.6. O log da falha tem método, caminho sem
    consulta e o tipo do erro. Testes extras: cookie não guardado entre pedidos, IP da conexão,
    401, HTMX, 403, prazos de D13; tela de teste em `tests/unit/rotas_de_teste.py`.
  - Comando: `docker compose exec front python -m pytest -c intranet/web/pyproject.toml
    intranet/web/tests/unit/test_cliente_api.py --no-cov -q`. Vermelho: `ImportError: cannot
    import name 'cliente_api' from 'lupa_web'`. Verde: `13 passed` (os três da tarefa: `4 passed`,
    com o 502 parametrizado em conexão recusada e prazo esgotado); suíte de `lupa_web`
    `22 passed`, cobertura 100%.
- [x] **T10.5** Proxy sem `/api` e CSP nova. RF-INT-01. Fase 3; D2, D10.
  - Vermelho: `intranet/web/tests/integracao/test_proxy.py::test_proxy_responde_404_para_api` e `intranet/api/tests/unit/test_verificar_cabecalhos.py::test_csp_sem_unsafe_hashes`.
  - Verde: `intranet/proxy/Caddyfile`, `verificar_cabecalhos.py`.
  - Limpeza: nenhuma.
  - Pronto quando: também `LUPA_EXIGIR_CABECALHOS=1 bash scripts/verificar.sh` verde.
  - Caddyfile: um só `reverse_proxy front:8000`; CSP com `style-src 'self'`.
    `verificar_cabecalhos.py`: `style-src` exato `'self'`, `unsafe-hashes` proibido em toda
    diretiva, rotas `/`, `/login`, `/saude`, `/api/saude` (`/inicio.js` era do SvelteKit). No
    teste, a constante `CSP` passa à nova e sai o caso do hash do anunciador (regra mudada por
    D10). Extra: `test_proxy.py::test_proxy_entrega_o_front`. `validar_caddyfile.sh`: ok.
  - Comando: `docker compose exec -T -e LUPA_EXIGIR_INTEGRACAO=1 front python -m pytest -c
    intranet/web/pyproject.toml intranet/web/tests/integracao/test_proxy.py --no-cov -q` e
    `docker compose exec api python -m pytest -c intranet/api/pyproject.toml
    intranet/api/tests/unit/test_verificar_cabecalhos.py --no-cov -q`. Vermelho: `1 failed`
    (`assert 200 == 404`) e `3 failed` (`test_csp_sem_unsafe_hashes`,
    `test_cabecalhos_do_proxy_passam`, `test_main_confere_cada_rota`). Verde: `2 passed` e
    `18 passed`.
  - `LUPA_EXIGIR_CABECALHOS=1 bash scripts/verificar.sh`: pipeline `702 passed` (95,25%), api
    `265 passed, 3 deselected` (98,23%), ponta a ponta `6 passed`, injeção `2 passed`, web
    `24 passed` (100%), cabeçalhos ok em 4 rotas, agente `11 passed`; E2E não rodou.
- [x] **T10.6** Login com TOTP, MFA com QR, troca de senha, logout e redirecionamento por sessão. RF-INT-02, RF-INT-03. Fase 4; A2, A3, D11.
  - Vermelho: `intranet/web/tests/telas/test_acesso.py::test_login_com_codigo_errado_mostra_recusa_generica`, `::test_configuracao_de_mfa_mostra_qr_em_svg`, `::test_sessao_expirada_redireciona_para_login`, `::test_pedido_htmx_com_sessao_expirada_recebe_hx_redirect`; `intranet/web/tests/telas/test_csrf.py::test_post_sem_csrf_e_recusado_sem_chamar_api`.
  - Verde: `telas/acesso.py`, `templates/base.html`, `templates/acesso/`, `componentes/`.
  - Limpeza: nenhuma.
  - `telas/sessao.py`: `tela_autenticada` consulta `GET /auth/sessao` antes da view e manda a
    `/trocar-senha` quando a troca está pendente (A1.7); `contexto_da_moldura` monta cabeçalho e
    menu por permissão. `/login` e `/login/codigo` (desafio, segredo e URI em campos ocultos; QR
    do `segno` em SVG inline sem `style`); recusa de senha ou código com uma só mensagem, 429 com o
    aviso de tentativas. `cliente_api`: `SessaoExpiradaError` guarda a resposta (o 401 do login e
    da senha atual não é sessão expirada), `detalhe_do_erro` (A1.8) e `redirecionar`. `/` com
    sessão vai a `/processos` (A3.2); a página inicial mínima sai, e `test_urls.py` e
    `test_proxy.py::test_proxy_entrega_o_front` passam a conferir `/login`. Confirmação sem
    JavaScript: `componentes/confirmacao.html` é uma página com formulário POST e "Cancelar".
    Logos e favicon copiados para `lupa_web/static/`. O painel "Início" do SvelteKit não foi
    reproduzido (fica para a paridade, T10.14).
  - Comando: `docker compose exec front python -m pytest -c intranet/web/pyproject.toml
    intranet/web/tests/telas --no-cov -q`. Vermelho: `22 failed` (rotas inexistentes, 404).
    Verde: `22 passed`; suíte de `lupa_web` com `LUPA_EXIGIR_INTEGRACAO=1` `51 passed`,
    cobertura 100%; ruff, format e mypy `--strict` limpos.
- [x] **T10.7** Lista de processos renderizada a partir da API. RF-INT-01, RF-INT-02. Fase 5.
  - Vermelho: `intranet/web/tests/telas/test_processos.py::test_lista_de_processos_vem_renderizada_da_api`.
  - Verde: `telas/processos.py`, `templates/processos/lista.html`.
  - Limpeza: nenhuma.
  - Filtros (busca, situação, responsável) num formulário GET, aplicados no servidor sobre a
    resposta de `GET /processos`; sem atualização automática (o SvelteKit repetia a cada 4 s com
    arquivo em processamento; a lista avisa para recarregar). `lupa_web/rotulos.py` com classes,
    situações, estados e motivos do SvelteKit (`lib/processos/rotulos.ts`) e datas no fuso de
    Brasília; teste em `tests/unit/test_rotulos.py`. Extras: filtros, lista vazia e filtro sem
    resultado.
  - Comando: `docker compose exec front python -m pytest -c intranet/web/pyproject.toml
    intranet/web/tests/telas/test_processos.py --no-cov -q`. Vermelho: `5 failed` (rota
    inexistente). Verde: `5 passed`; suíte de `lupa_web` com `LUPA_EXIGIR_INTEGRACAO=1`
    `64 passed`, cobertura 100%.
- [x] **T10.8** Cadastro por arquivo com progresso, complemento e estado da ingestão. RF-INT-04. Fase 5; A4, D8, D14.
  - Vermelho: `intranet/web/tests/telas/test_envio.py::test_pdf_sem_classe_pede_a_classe_e_reenvio_usa_o_mesmo_arquivo`, `::test_arquivo_acima_do_limite_e_recusado_sem_chamar_api`; `intranet/web/tests/telas/test_processo.py::test_estado_do_arquivo_para_de_atualizar_no_estado_final`; `intranet/web/tests/integracao/test_envio_api_real.py::test_envio_de_pdf_sintetico_cria_processo_pela_api`; `intranet/web/tests/unit/test_envios_pendentes.py::test_pendente_vencido_ou_de_outra_sessao_nao_e_recuperado`, `::test_pendente_e_apagado_apos_aceite_e_vencidos_no_envio_novo` (D16).
  - Verde: `telas/envio.py`, `telas/processo.py`, fragmentos, `static/js/htmx.min.js`, `static/js/envio.js`.
  - Limpeza: nenhuma.
  - `telas/envio.py`: `POST /processos/envio` (novo), `/processos/<id>/envio` (anexo) e
    `/processos/envio/complemento`; recusa no front sem chamar a API (sem arquivo, tipo, vazio,
    acima de `LUPA_WEB_TAMANHO_MAXIMO_ENVIO`, padrão 512 MiB); repasse em streaming (blocos de
    1 MiB, `application/octet-stream`, prazo longo); fragmentos com status 200 (o HTMX não troca
    4xx). `envios_pendentes.py` (D16): arquivo e metadados (nome, SHA-256 do cookie, momento e a
    identificação incompleta da API, para refazer o formulário) no volume; código de 32 bytes
    conferido por regex; complemento que a API ainda recusa sem `motivo` (número inválido) mantém
    o pendente; recusa com `motivo` o apaga. Upload só por `TemporaryFileUploadHandler` em
    `FILE_UPLOAD_TEMP_DIR` = volume. Volume `envios-pendentes` no compose; o Dockerfile cria
    `/var/lupa/envios-pendentes` com dono `lupa` (o volume novo herda o dono).
  - Estado (A4.9): `GET /processos/<id>/estado`, fragmento `processos/_estado.html` com
    `hx-trigger="every 5s"` só com arquivo fora de `ESTADOS_FINAIS`. Lista (paridade RF-INT-02):
    `processos/_tabela.html` com `every 4s` enquanto há processamento, como o SvelteKit; o pedido
    HTMX recebe só a tabela, e os filtros ficam fora do fragmento.
  - HTMX 2.0.4 de `https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js` (50 917 bytes, SHA-256
    `4gndpcgjVHnzFm3vx3UOHbzVpcGAi3eS/C5nM3aPtEc=`, igual ao publicado pelo jsDelivr; SHA-384
    `HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+`), `meta htmx-config`
    com `allowEval=false`, `includeIndicatorStyles=false`, `selfRequestsOnly=true`; `envio.js`
    com `htmx:xhr:progress`.
  - Logger `httpx`/`httpcore` em `WARNING` (a URL leva nome do arquivo e número CNJ):
    `test_cliente_api.py::test_log_do_httpx_nao_registra_a_consulta`. Cliente da API por loop de
    eventos (`::test_cliente_e_um_por_loop_de_eventos`, `::test_encerrar_fecha_o_cliente_do_proprio_loop`);
    `chamar` aceita cabeçalhos extras.
  - Integração: o teste entra como assessor novo (TOTP calculado no teste, troca de senha), envia
    um PDF mínimo sem identificação e completa com número CNJ válido aleatório. `verificar.sh`
    cria o assessor no contêiner `api` com o desembargador existente e passa usuário e senha por
    `LUPA_WEB_TESTE_USUARIO`/`LUPA_WEB_TESTE_SENHA`; sem eles e com `LUPA_EXIGIR_INTEGRACAO=1` o
    teste falha. O TOTP usa o relógio real (a API confere o código no tempo real).
  - Comando: `docker compose exec -e LUPA_EXIGIR_INTEGRACAO=1 -e LUPA_WEB_TESTE_USUARIO -e
    LUPA_WEB_TESTE_SENHA front python -m pytest -c intranet/web/pyproject.toml intranet/web/tests
    -q`. Vermelho: `15 failed, 88 passed, 1 skipped` e `ImportError: cannot import name
    'envios_pendentes'`. Verde: `109 passed`, cobertura 100%; ruff, format e mypy limpos.
  - `LUPA_EXIGIR_CABECALHOS=1 bash scripts/verificar.sh`: pipeline `702 passed` (95,25%), api
    `265 passed, 3 deselected` (98,23%), ponta a ponta `6 passed`, injeção `2 passed`, web
    `109 passed` (100%), cabeçalhos ok em 4 rotas, agente `11 passed`; E2E não rodou.
  - Ajuste (consequência de D16): sob ASGI o Django grava o corpo de pedido grande em temporário
    no diretório padrão (`/tmp`, tmpfs). Na partida do ASGI, `envios_pendentes.preparar_temporarios`
    cria `temporarios/` (modo 700) no volume e a torna o `tempfile.tempdir` do processo.
    Vermelho: `intranet/web/tests/unit/test_asgi.py::test_partida_poe_os_temporarios_no_volume_dos_pendentes`
    (`1 failed, 2 passed`). Verde: `3 passed`; suíte de `lupa_web` com `LUPA_EXIGIR_INTEGRACAO=1`
    `110 passed`, cobertura 100%. No contêiner: `/var/lupa/envios-pendentes/temporarios` com dono
    `lupa` e modo `drwx------`.
- [x] **T10.9** Processo: arquivos com diagnóstico e alertas, responsáveis, correção de classe e descarte. RF-INT-02. Fase 5.
  - Vermelho: casos `processo` de `intranet/web/tests/telas/test_paridade.py::test_cada_tela_responde_ao_papel_permitido`.
  - Verde: `telas/processo.py`, `templates/processos/processo.html`.
  - Limpeza: nenhuma.
  - Feita antes da T10.8 (o envio e o estado com `hx-trigger` ficam para ela). A tela lê
    `GET /processos/<id>`, `/arquivos` e `/responsaveis`; cada ação é um formulário POST que
    chama a API e volta com 303: `/classe` (papel com `anotar`), `/responsaveis` (só com
    `gerir_assessor` e `pode_gerir` da API, `?aviso=responsaveis` mostra a confirmação),
    `/descartar` (GET com `componentes/confirmacao.html`, POST descarta e vai à lista; papel com
    `ver_auditoria`, como a API). Página do arquivo `/processos/<id>/arquivos/<arquivo>` com
    relatório, diagnóstico (404 da API vira "Diagnóstico ainda não disponível.") e alertas
    (resumo, páginas com sinal, metadados suspeitos). 404 da API vira `erros/nao_encontrado.html`;
    4xx das ações volta à tela com a mensagem da API e o mesmo status (A1.8). Os dados da capa
    (ficha do dossiê) no cabeçalho ficam para a T10.10. Casos de `test_paridade.py`: processo
    (assessor e desembargador), arquivo, classe, responsáveis, confirmação e descarte; extras em
    `test_processo.py` (404, sem diagnóstico, 409, aviso, tamanhos e motivos) e
    `test_rotulos.py`.
  - Comando: `docker compose exec front python -m pytest -c intranet/web/pyproject.toml
    intranet/web/tests/telas/test_paridade.py intranet/web/tests/telas/test_processo.py --no-cov
    -q`. Vermelho: `11 failed, 11 passed` (rotas inexistentes; os 11 verdes são as funções puras
    `formatar_bytes` e `detalhe_do_estado`, escritas junto com a view). Verde: `22 passed`; suíte
    de `lupa_web` com `LUPA_EXIGIR_INTEGRACAO=1` `87 passed`, cobertura 100%.
- [x] **T10.10** Dossiê, peças, fatos, achados, anotações e visualizador com imagem repassada. RF-INT-02, RF-INT-05. Fase 6; A6.
  - Vermelho: `intranet/web/tests/telas/test_dossie.py::test_evidencia_do_dossie_abre_a_pagina_do_arquivo`; `intranet/web/tests/telas/test_visualizador.py::test_imagem_da_pagina_e_repassada_com_tipo_e_cache_da_api`; casos `dossie`, `validacoes` e `visualizador` de `test_paridade.py`.
  - Verde: `telas/dossie.py`, `telas/validacoes.py`, `telas/visualizador.py` e templates.
  - Limpeza: nenhuma.
  - Dossiê (`/processos/<id>/dossie`): ficha com partes, dados da capa (valor da causa em reais,
    data de distribuição), responsáveis e ingestão; linha do tempo; índice com reclassificação do
    tipo por formulário POST (`/pecas/<peca>/reclassificar`, papel com `anotar`; o SvelteKit não
    tinha) e `?resumos=1` (GET, `resumos=true` na API, texto marcado "gerado"); alertas; achados
    com as fontes. Partes e dados da capa também no cabeçalho do processo (o que a T10.9 deixou).
    Validações (`/processos/<id>/validacoes`): valores do achado com link para a evidência (data
    do marco, fato, página), fatos usados com "Confirmar" e "Corrigir" (`<details>`, sem
    JavaScript; fonte existente ou trecho novo conferido no front, valor no tipo do original),
    anotações por fato e por achado, histórico de achados e fatos substituídos; avisos por
    `?aviso=`. Visualizador (`/processos/<id>/visualizador`): `evidencia` ou `arquivo`/`pagina`,
    navegação e zoom (50% a 300%) por links, seletor de arquivo por formulário GET; destaque em
    SVG (`viewBox="0 0 1 1"`, `<rect>` com x/y/width/height em fração) sobre a imagem, posicionado
    por `static/css/visualizador.css` (classes `zoom-NN`), sem estilo inline. Imagem (A6):
    `/processos/<id>/arquivos/<arquivo>/paginas/<n>/imagem` repassa PNG, `Content-Type` e
    `Cache-Control` da API; outro status volta sem corpo; sem a consulta de sessão (401 vai ao
    login pelo middleware). `nao_encontrado` e `obter` passaram de `processo.py` a `sessao.py`.
    Extras em `test_dossie.py`, `test_visualizador.py` e `test_validacoes.py`.
  - Comando: `docker compose exec front python -m pytest -c intranet/web/pyproject.toml
    intranet/web/tests/telas --no-cov -q`. Vermelho: `17 failed, 24 passed` em `test_dossie.py`,
    `test_paridade.py` e `test_processo.py` e `ImportError: cannot import name 'visualizador'` em
    `test_visualizador.py`. Verde: suíte de `lupa_web` com `LUPA_EXIGIR_INTEGRACAO=1`
    `173 passed`, cobertura 100%; ruff, format e mypy `--strict` limpos.
  - Pelo proxy (httpx no contêiner `front`, assessor sintético novo, PDF sintético): processo,
    dossiê, validações e visualizador 200 sem estilo nem script inline; imagem 200 `image/png`,
    `private, max-age=3600`; página inexistente 404.
- [x] **T10.11** Chat com HTMX, histórico, teto, revisão e liberação. RF-INT-02, RF-INT-05. Fase 7; A5, D13.
  - Vermelho: `intranet/web/tests/telas/test_chat.py::test_resposta_conferida_aparece_em_bloco_rotulado_com_link_da_pagina`, `::test_resposta_sem_citacao_conferida_mostra_sem_evidencia`, `::test_aviso_de_teto_aparece_sem_bloco_de_ia`; caso `chat` de `test_paridade.py`.
  - Verde: `telas/chat.py`, `templates/chat/`, fragmentos.
  - Limpeza: nenhuma.
  - `/processos/<id>/chat`: GET lê `GET /chat` e `/revisao`; conversa atual (a última aberta),
    contador de descartes, encerramento por teto e conversas anteriores em `<details>`. A
    pergunta é um formulário `hx-post` com `hx-target="#conversa-atual"`, `hx-swap="beforeend"`,
    `hx-indicator` ("Aguardando resposta…", escondido por `static/css/chat.css` fora do pedido) e
    `hx-disabled-elt`; prazo longo (D13). O fragmento `chat/_resposta.html` traz a pergunta, a
    resposta e, por `hx-swap-oob`, o formulário limpo (travado com conversa encerrada ou processo
    em revisão) e o contador. Resposta do agente em bloco com "Conteúdo gerado por IA",
    desfecho ("Sem evidência: resposta não conferida nos autos.", recusa, descartada), citações
    com link `/visualizador?arquivo=…&pagina=…` e avisos; teto e recusa por revisão aparecem como
    aviso, sem bloco de IA. Recusa da API e prazo esgotado viram aviso no fragmento, com 200. POST
    sem HTMX faz a pergunta e volta à tela. Revisão: aviso com o motivo; o papel com
    `ver_auditoria` vê "Liberar revisão" (`/chat/liberar`: GET confirmação, POST
    `/liberar-revisao` e `?aviso=liberado`). Sem o contador de caracteres restantes do SvelteKit
    (exigiria JavaScript; o campo tem `maxlength`). O texto da pergunta não entra em log
    (`test_pergunta_vai_a_api_com_prazo_longo_e_nao_entra_no_log`).
  - Comando: `docker compose exec front python -m pytest -c intranet/web/pyproject.toml
    intranet/web/tests/telas/test_paridade.py intranet/web/tests/telas/test_chat.py --no-cov -q`.
    Vermelho: `4 failed, 14 passed` em `test_paridade.py` e `ImportError: cannot import name
    'chat'` em `test_chat.py`. Verde: suíte de `lupa_web` com `LUPA_EXIGIR_INTEGRACAO=1`
    `193 passed`, cobertura 100%; ruff, format e mypy `--strict` limpos.
  - Pelo proxy (assessor sintético novo): tela do chat 200 sem estilo nem script inline, com
    `hx-swap="beforeend"` e o indicador; POST HTMX com CSRF devolve o fragmento com
    `hx-swap-oob`; sem CSRF, 403. Nenhuma pergunta foi enviada ao modelo pelo proxy (o `api` do
    desenvolvimento usa o cliente `sdk`, real).
- [x] **T10.12** Auditoria (lista, exportação, verificação, relatório de uso) e gestão de assessores. RF-INT-02, RF-INT-03. Fase 8.
  - Vermelho: `intranet/web/tests/telas/test_paridade.py::test_assessor_recebe_acesso_negado_em_auditoria_e_usuarios`; casos `auditoria` e `usuarios` de `test_paridade.py`.
  - Verde: `telas/auditoria.py`, `telas/usuarios.py` e templates.
  - Limpeza: nenhuma.
  - `/auditoria`: tudo por GET. Filtros (ids conferidos no front, `datetime-local` em horário
    de Brasília convertido para UTC, início antes do fim) vão a `GET /auditoria` com `limite=50`;
    "Próxima página" leva o `cursor` (substitui o "Carregar mais" do SvelteKit). `?verificar=1`
    mostra a verificação da cadeia; `relatorio_tipo`/`relatorio_id` o relatório de uso (custo com
    2 a 4 casas). Os ids da tabela são links para o relatório. `/auditoria/exportar` e
    `/auditoria/relatorio-uso` repassam o arquivo da API com `Content-Type` e
    `Content-Disposition`; recusa volta com o status e a mensagem em texto. `/usuarios`: lista com
    ações por papel (`acoes_sobre` do SvelteKit), criação por POST que mostra a senha temporária
    uma vez na própria resposta (`Cache-Control: no-store`, nunca na URL; `componentes/
    senha_temporaria.html`), desativar com confirmação (`/usuarios/<id>/desativar`), reativar e
    resetar senha e MFA por POST (`/usuarios/<id>/<acao>`); depois da ação, `?aviso=&usuario=`
    com o id. Assessor: a API responde 403 e o front mostra "Acesso negado". `Caso` de
    `test_paridade.py` ganhou `resposta_api` e confere `Location` só quando há `destino`.
  - Comando: `docker compose exec front python -m pytest -c intranet/web/pyproject.toml
    intranet/web/tests/telas/test_paridade.py --no-cov -q`. Vermelho: `14 failed, 18 passed`.
    Verde: suíte de `lupa_web` com `LUPA_EXIGIR_INTEGRACAO=1` `232 passed`, cobertura 100%;
    ruff, format e mypy `--strict` limpos.
  - Pelo proxy (assessor sintético novo): `/auditoria`, `/usuarios` e `/auditoria/exportar`
    respondem 403 com "Acesso negado", sem estilo nem script inline. O fluxo do desembargador
    pelo proxy não foi conferido (sem credencial de desembargador de teste).
- [x] **T10.13** CSS e tema reproduzindo o layout atual. RF-INT-02. Fase 9; D7, D8.
  - Revisão manual: componente de apresentação; conferência visual tela a tela contra o SvelteKit, nos dois temas.
  - Verde: `static/css/`, `static/js/tema.js`.
  - `base.css` (tokens claro/escuro de `src/app.css`, elementos, `a.botao` com o visual dos
    botões e a moldura do `+layout.svelte`), `componentes.css` (aviso, cabeçalho, seletor de
    tema, menu, confirmação, senha temporária, envio e complemento) e uma folha por tela:
    `login.css` (`login.css` do SvelteKit e QR), `processos.css`, `processo.css` (processo e
    arquivo, com `CabecalhoProcesso`, `DadosCapa` e `Responsaveis`), `dossie.css`,
    `validacoes.css`, `auditoria.css`, `usuarios.css`; `chat.css` ganhou a tela e
    `MensagemChat`, `visualizador.css` os valores do `Visualizador.svelte`. Seletores que o Svelte
    escopava pelo componente levam a classe raiz (`.menu a`, `.mensagem .ia`, `.verificacao.ok`);
    o seletor de tema usa `.seletor-tema` (`.seletor` já é do visualizador). Fontes do sistema,
    como no SvelteKit; logos e favicon já locais.
  - `tema.js` (sem `defer`, no `<head>`, antes das folhas): lê `lupa.tema` do `localStorage`
    (padrão escuro, `data-tema="escuro"` no `<html>` como o `app.html`), aplica antes da pintura e
    liga os `select[data-seletor-tema]` de `componentes/seletor_tema.html`, no cabeçalho e no
    rodapé das páginas avulsas, como o SvelteKit. Sem JavaScript o tema fica no padrão.
  - Teste extra: `tests/unit/test_estaticos.py` (template sem `style`, `<style>`, script inline
    ou atributo de evento; cada `{% static %}` existe).
  - Comando: `docker compose exec front python -m pytest -c intranet/web/pyproject.toml
    intranet/web/tests/unit/test_estaticos.py --no-cov -q`: `76 passed`; suíte de `lupa_web` com
    `LUPA_EXIGIR_INTEGRACAO=1` `307 passed`, cobertura 100% (o envio real só no
    `verificar.sh`, que cria o assessor); ruff, format e mypy `--strict` limpos.
  - Conferência visual pendente do usuário: o painel do navegador recusou o certificado
    autoassinado de `https://localhost:8443`; a comparação foi por leitura, classe a classe e
    variável a variável, contra os `<style>` dos `.svelte`, `app.css` e `login.css`.
  - Conferência visual por capturas (feita na T10.15): `capturas.sh` com
    `LUPA_CAPTURAS_VISUAL` retratou as dezesseis telas em claro e escuro, a 1200 e a 375 px
    (64 imagens), comparadas às capturas do SvelteKit em `docs/imagens/` (versão anterior).
    Corrigido em commit próprio: "+ Novo processo" ao lado do título; Corrigir, Anotar,
    Reclassificar e Corrigir classe com o visual do botão secundário e fatos em linha; "Outro
    trecho" só com "Informar outro trecho" (`:has`); identificadores da auditoria em mono;
    tabelas que rolam dentro da página até 55rem (antes a página rolava de lado a 375 px).
    Ficou diferente: fatos das validações sem marcador de lista; botão "Enviar" habilitado sem
    arquivo; limite "512,0 MB" (era "512 MB"); ficha do dossiê com os dados da capa; ordem dos
    dados da capa e dos fatos como vêm da API; foco visível no campo autofocado do login.
- [x] **T10.14** Paridade de telas fechada. RF-INT-02. Fases 4 a 8.
  - Vermelho: `intranet/web/tests/telas/test_paridade.py::test_cada_tela_responde_ao_papel_permitido` com as onze telas e todas as ações.
  - Verde: o que faltar das tarefas anteriores.
  - Limpeza: extrair o que se repetir entre views.
  - Casos novos: login (GET e senha aceita, anônimo), código TOTP, troca de senha (GET e POST),
    sair, lista de processos (assessor; desembargador com filtro sem resultado), cadastro por
    arquivo e anexo (303 para o processo), estado dos arquivos, imagem da página e resumos do
    dossiê. Papel `anonimo` sem `GET /auth/sessao`; `corpo_api=None` dispensa a conferência do
    corpo (envio em `application/octet-stream`). O complemento do cadastro fica em
    `test_envio.py` (precisa de pendente no volume). Comparação rota a rota com
    `src/routes` e `src/lib`: as onze telas e as ações das fases 4 a 8 já existiam; nenhum código
    de view mudou, e a limpeza não achou repetição nova entre views.
  - Complemento (D17, decisão do usuário): o painel "Início" é reproduzido em `/`
    (`telas/inicio.py`, `templates/inicio.html`, `static/css/inicio.css` do `+page.svelte`):
    assessor com `GET /processos?meus=true`, desembargador com `GET /processos` e a equipe de
    `GET /usuarios`; indicadores (total, processando, concluídos, pendências/falha/quarentena),
    cinco recentes, atalhos por permissão, até três pontos de atenção e dados da sessão; falha da
    API vira aviso "Processos: …" e "—". O menu começa por "Início" (corrente só em `/`). Como no
    SvelteKit, o login e a troca de senha aceitos levam a `/` (A3.2 atualizado no plano); os
    testes de `test_acesso.py` e os destinos da paridade mudaram com a regra, e o teste da raiz
    que levava a `/processos` saiu. "+ Novo processo" é o `<summary>` de um `<details>` com o
    cadastro dentro, com o visual do botão do SvelteKit e o texto "Fechar cadastro" quando aberto,
    só por CSS. "Visualizar como assessor" removido: o Django nunca o teve (sem resquício em
    `lupa_web`); a remoção entra no `CHANGELOG.md` na T10.16.
  - Comando do complemento: `docker compose exec front python -m pytest -c
    intranet/web/pyproject.toml intranet/web/tests/telas --no-cov -q`. Vermelho: `11 failed,
    193 passed` (`test_inicio.py` 4, `test_processos.py` 1, destinos de `test_acesso.py` 2 e
    paridade 4). Verde: `test_inicio.py` `4 passed`, `test_paridade.py` `47 passed`; suíte de
    `lupa_web` `329 passed`, cobertura 100%; ruff, format e mypy `--strict` limpos;
    `LUPA_EXIGIR_CABECALHOS=1 bash scripts/verificar.sh` verde (pipeline 702, intranet 265, web 329; e2e fora).
  - Comando: `docker compose exec front python -m pytest -c intranet/web/pyproject.toml
    intranet/web/tests/telas/test_paridade.py --no-cov -q`. Vermelho: `10 failed, 35 passed`
    (API sem `/processos` nem imagem simuladas, papel anônimo inexistente, corpo binário).
    Verde: `45 passed` no arquivo; suíte de `lupa_web` com `LUPA_EXIGIR_INTEGRACAO=1`
    `321 passed` (com o envio real), cobertura 100%; ruff, format e mypy `--strict` limpos;
    `LUPA_EXIGIR_CABECALHOS=1 bash scripts/verificar.sh` verde (pipeline 702, intranet 265, web 321; e2e fora).
- [x] **T10.15** Suíte E2E em `pytest-playwright` e capturas dos guias. RF-INT-01, RNF-09. Fase 10; D5, D6.
  - Revisão manual: E2E fora do ciclo. `intranet/web/tests/e2e/test_seguranca.py::test_navegador_nao_faz_requisicao_para_api`, `test_fluxos.py` (login, processos, dossiê, chat, auditoria, assessores) e `test_capturas.py::test_gera_capturas_dos_guias`.
  - Verde: `intranet/web/e2e/Dockerfile`, serviço `e2e`, `intranet/web/scripts/e2e.sh`, `docs/guias/imagens/`.
  - Pronto quando: `bash intranet/web/scripts/e2e.sh` verde e capturas conferidas.
  - Suíte em `intranet/web/tests/e2e/` (marcador `e2e`, excluído por padrão): `apoio_e2e.py`
    (TOTP RFC 6238, contas, login pela tela), `conftest.py` (ordem dos arquivos e contas
    criadas uma vez), `test_fluxos.py` (login, primeiro acesso, troca, gestão de assessores,
    bloqueio), `test_processos.py` (lista, cadastro com complemento do número, capa, anexo,
    duplicata, envio de 500 MiB com progresso, dossiê, visualizador pelo teclado, evidências,
    correção e anotação), `test_chat_auditoria.py`, `test_acessibilidade.py` (axe-core WCAG 2.1
    A/AA nos dois temas, teclado, tema), `test_seguranca.py` (inclui
    `test_navegador_nao_faz_requisicao_para_api`, cabeçalhos, CSP e texto hostil) e
    `test_capturas.py` (`test_gera_capturas_dos_guias` e as telas em claro, escuro e 375 px).
    A suíte TypeScript de `intranet/web/e2e/` saiu. Imagem `intranet/web/e2e/Dockerfile` em
    `python:3.12-slim-bookworm` (o Playwright 1.49 não instala as dependências do Chromium no
    Debian 13), `requirements-dev.txt` de `lupa_web` com `pytest-playwright`, `playwright` 1.49.1
    e `axe-playwright-python` (só o `axe.min.js`, injetado por `page.evaluate`). `e2e.sh` roda tudo
    menos as capturas; `capturas.sh`, numa stack nova, grava em `docs/imagens/`.
  - Achados do E2E corrigidos com teste vermelho antes, em commits próprios: CSRF recusava todo
    formulário (`Origin: null` com `no-referrer`; D18 `same-origin`); `visualizador.js` (D8);
    aviso de sessão expirada no login; avisos de processo criado, anexado ou já enviado; aviso
    de revisão no chat sem recarregar (OOB); rótulos do SvelteKit em `legivel` e
    `texto_do_valor` e número CNJ com máscara no dossiê; anexo dava 500 (a API não devolve
    `processo_id`). O dígito do CNJ fica na API; "desembargador só cria assessor" segue em
    `intranet/api/tests/acesso/test_usuarios.py`.
  - O TOTP do E2E espera o relógio real (até 30 s entre logins da mesma conta): o servidor
    recusa passo repetido; exceção aceita por estar fora do ciclo.
  - Comando: `bash intranet/web/scripts/e2e.sh` e `bash intranet/web/scripts/capturas.sh`.
    Vermelho: `1 failed, 1 passed` (403 de CSRF no primeiro acesso). Verde: `35 passed` em 76 s
    (2 min 17 s com a stack); capturas `2 passed` em 54 s (2 min 6 s); suíte de `lupa_web`
    `348 passed`, cobertura 100%; `LUPA_EXIGIR_CABECALHOS=1 bash scripts/verificar.sh` verde
    (pipeline 702, intranet 266, integração 6, injeção 2, web 348, cabeçalhos ok; e2e fora).
- [x] **T10.16** Remover o SvelteKit e atualizar `verificar.sh`, `Makefile`, `CLAUDE.md`, documentação, ADRs 0006 e 0016 e `CHANGELOG.md`. RES-06, RNF-08. Fase 11.
  - Revisão manual: remoção e documentação. Testes do Vitest e Playwright em TypeScript saem neste commit, citando a tarefa.
  - Pronto quando: `bash scripts/verificar.sh` verde, sem referência a `lupa_intranet`, `npm` ou SvelteKit fora do histórico, e links locais conferidos.
  - Removidos de `intranet/web/`: `src/lib`, `src/routes`, `src/app.*`, `src/testes-setup.ts`,
    `static/` (os logos já estão em `lupa_web/static`), `.svelte-kit/`, `package*.json`, configs
    de Vite, Svelte, TS, ESLint e Prettier, `Caddyfile`, `.dockerignore`, `.gitignore` e
    `scripts/carimbo.mjs`/`externalizar-inicio.mjs`; `.gitignore` e `.dockerignore` da raiz sem as
    entradas de Node. `Makefile` com `lupa_web` em `test`, `lint`, `typecheck` e `format`.
  - `verificar.sh` cria um desembargador sintético de senha aleatória (só por variável) quando a
    stack não tem nenhum (`criar_desembargador_inicial`); com desembargador existente não faz nada.
  - `test_configuracao.py::test_lupa_web_nao_configura_banco` lê `connections.settings` (o Django
    só põe o motor `dummy` ao configurar as conexões). Vermelho rodando sozinho com `--no-cov`:
    `assert {} == {'default': 'django.db.backends.dummy'}`; verde: `1 passed`.
  - `CLAUDE.md` e `.claude/` (agentes e skills) não alterados pelo executor; ficam com o agente
    principal.
  - Comando: `LUPA_EXIGIR_CABECALHOS=1 bash scripts/verificar.sh` e `bash intranet/web/scripts/e2e.sh`.
    Verde: pipeline `702 passed` (95,25%), intranet `266 passed` (98,23%), integração 6, injeção 2,
    web `348 passed` (100%), cabeçalhos ok em 4 rotas, agente 11; E2E `35 passed` em 80 s.

## Fase 11 — Padrão visual

Execução do [plano do padrão visual](plano_padrao_visual.md). Um único PR da branch
`feat/padrao-visual`. "Pronto quando", salvo indicação: suíte de `lupa_web` verde no contêiner
`front` depois do rebuild, `ruff check`, `ruff format --check` e `mypy --strict` limpos.

- [x] **T11.1** Tokens em `tokens.css` com a paleta verde e o teste de contraste. RF-VIS-01, RF-VIS-02. Fase 1; P1, D1, D6.
  - Vermelho: `intranet/web/tests/unit/test_tokens.py::test_primaria_e_verde_do_padrao`, `::test_tema_escuro_redefine_todos_os_tokens_de_cor`, `::test_pares_de_texto_atingem_4_5_nos_dois_temas`, `::test_borda_foco_e_tarja_atingem_3_nos_dois_temas`.
  - Verde: `static/css/tokens.css` (claro e escuro, cores do selo e do badge), `base.css` passa a importá-lo e perde as declarações de token; `base.html` carrega `tokens.css`.
  - Limpeza: nenhuma.
  - Entregue: `tokens.css` com tema claro, escuro manual e escuro do sistema (fundo, superfícies,
    texto, borda e `--borda-campo`, primária, sucesso/atenção/perigo com fundo, aviso, foco,
    badge, raio, tarja, espaços); `base.css` sem tokens; `base.html` carrega `tokens.css` antes
    de `base.css` (por `<link>`, sem `@import` duplicado). Testes: `docker compose exec -T front
    python -m pytest -c intranet/web/pyproject.toml intranet/web/tests/unit/test_tokens.py`.
    Vermelho: 33 falhas (`tokens.css` ausente). Verde: 33 passed; unit e telas 378 passed,
    cobertura 100%.
- [x] **T11.2** Fontes Source servidas pelo front. RF-VIS-02. Fase 1; D3, D4.
  - Vermelho: `intranet/web/tests/e2e/test_seguranca.py::test_fontes_vem_da_propria_origem` falha (nenhum woff2 é carregado).
  - Verde: `static/fontes/` com os 5 woff2 das releases `adobe-fonts` e `LICENSE.md`; `@font-face` em `tokens.css`; tokens `--fonte-titulo`, `--fonte`, `--mono`. SHA-256 de cada arquivo anotado na tarefa.
  - Limpeza: nenhuma.
  - Entregue: o subconjunto latino não é publicado pronto nas releases; vão os woff2 da variante
    TTF de cada release, inteiros (total 460 KiB). `@font-face` com `font-display: swap` em
    `tokens.css`; h1 a h3 em `--fonte-titulo` 600; `code`, `kbd`, `pre`, `samp` em `--mono`.
    `LICENSE.md` reúne o `LICENSE.md` (OFL 1.1) dos três repositórios.

    | Arquivo | Origem | Bytes | SHA-256 |
    | --- | --- | --- | --- |
    | `SourceSerif4-Semibold.woff2` | source-serif 4.005R, `source-serif-4.005_WOFF2.zip`, `TTF/SourceSerif4-Semibold.ttf.woff2` | 80732 | `457a13ac92e977d82e376038a2daac7fdb5433610910bf5787bdf6c1c3781865` |
    | `SourceSans3-Regular.woff2` | source-sans 3.052R, `WOFF2-source-sans-3.052R.zip`, `TTF/SourceSans3-Regular.ttf.woff2` | 109632 | `53492fb3a0def77354f166a55d09b63a10855e91c206c7620a81cf56e97f8ec3` |
    | `SourceSans3-It.woff2` | idem, `TTF/SourceSans3-It.ttf.woff2` | 86452 | `4d80b3b801f4c457f1b4adbd3911d8501338e6d282141663770c38d3a2e97859` |
    | `SourceSans3-Semibold.woff2` | idem, `TTF/SourceSans3-Semibold.ttf.woff2` | 108900 | `47b9b661b9f395fe7f0d0e119637fba5c8dad97bde3df60066fd24229c0792f4` |
    | `SourceCodePro-Regular.woff2` | source-code-pro 2.042R-u/1.062R-i/1.026R-vf, `WOFF2-source-code-pro-2.042R-u_1.062R-i_1.026Rvf.zip`, `TTF/SourceCodePro-Regular.ttf.woff2` | 74052 | `714eee29b70d191f5bf4b3a06b68f2c50522b1303d31c7d44dcefdcc5f9defd0` |

    Testes: `bash intranet/web/scripts/e2e.sh -k fontes_vem_da_propria_origem` e, no `front`,
    `python -m pytest -c intranet/web/pyproject.toml intranet/web/tests/unit/test_estaticos.py`
    (casos novos `test_tokens_declaram_as_cinco_faces_source_com_swap` e
    `test_fontes_declaradas_existem_na_propria_origem`). Vermelho: E2E 1 failed (nenhum woff2
    pedido, `AssertionError: []`); unit 2 failed. Verde: E2E 3 passed (fontes, cabeçalhos, CSP);
    unit e telas 380 passed, cobertura 100%.
- [x] **T11.3** Catálogo de componentes e página `/padrao`. RF-VIS-03, RF-VIS-04, RF-VIS-05. Fase 1; D2, D7, D8.
  - Vermelho: `intranet/web/tests/telas/test_padrao.py::test_padrao_devolve_404_fora_do_desenvolvimento`, `::test_padrao_sem_sessao_vai_ao_login`, `::test_padrao_mostra_cada_componente_em_desenvolvimento`.
  - Verde: `telas/padrao.py`, rota em `urls.py`, `templates/padrao.html`; os 11 templates em `templates/componentes/` (`aviso.html` adaptado); estilos em `componentes.css` só com tokens.
  - Limpeza: nenhuma.
  - Revisão manual: aparência dos componentes; o usuário aprova o visual pelas capturas da `/padrao` (claro, escuro, 375 px) antes da T11.5.
  - Entregue: `telas/padrao.py` (404 por `Http404` antes de `tela_autenticada`), rota `padrao`,
    `padrao.html` com tipografia e cada componente em suas variantes; `botao`, `aviso`, `tabela`
    (região rolável com `tabindex`), `campo` (texto, senha, select, textarea, dica), `acao`
    (`<details>` com formulário), `paginacao`, `vazio`, `badge`, `cartao`, `progresso` e `selo`
    (tarja de `--tarja` no tom, texto do resultado); raiz de cada um com `data-componente`.
    `componentes.css` ganha os estilos, só com tokens, e usa peso 600 (a face carregada).
    Testes: `docker compose exec -T front python -m pytest -c intranet/web/pyproject.toml
    intranet/web/tests/telas/test_padrao.py`. Vermelho: 4 failed (sem sessão, catálogo, selo,
    badge); os 4 casos de 404 já passavam por falta da rota. Verde: 8 passed; unit e telas 410
    passed, cobertura 100%.
- [x] **T11.4** Teste de conformidade com lista de telas pendentes. RF-VIS-01, RF-VIS-04. Fase 1; D5.
  - Vermelho: `intranet/web/tests/unit/test_conformidade_templates.py::test_css_de_tela_nao_tem_cor_nem_fonte_literal` e `::test_templates_de_tela_usam_componentes` falham para `base.css` e `componentes.css`, que não estão na lista de pendentes.
  - Verde: os dois CSS só com `var(--…)`; a lista de pendentes começa com os grupos das fases 2 a 6.
  - Limpeza: nenhuma.
  - Entregue: `PENDENTES` com os grupos `acesso`, `processos`, `dossie`, `chat` e `gestao`
    (templates e CSS de cada fase); caso extra `test_pendentes_citam_arquivos_que_existem`.
    Testes: `docker compose exec -T front python -m pytest -c intranet/web/pyproject.toml
    intranet/web/tests/unit/test_conformidade_templates.py`. Vermelho: como a T11.1 já tirou os
    tokens de `base.css` e a T11.3 deixou `componentes.css` só com tokens, o vermelho foi tirado
    rodando o teste sobre a árvore de `ee33894` (antes da fase 11): CSS 1 failed, 42 ocorrências
    em `base.css`; o de templates já passava (`base.html` sem marcação própria). Verde: 3 passed;
    unit e telas 413 passed, cobertura 100%.
- [x] **T11.5** Telas de acesso no padrão (login, TOTP, troca de senha, erros, acesso negado). RF-VIS-04. Fase 2; P3.
  - Vermelho: grupo "acesso" sai da lista de pendentes e `test_conformidade_templates.py` falha.
  - Verde: templates de `acesso/`, `erros/` e `login.css` com componentes e tokens; testes de tela existentes continuam verdes.
  - Limpeza: nenhuma.
  - Entregue: login, código e troca de senha com `componentes/botao.html` (o botão ganha o
    parâmetro `formulario`, para o "Sair" da troca); `login.css` sem cor literal nem sombra, tarja
    superior em `--tarja` e `--primaria`, botão no verde primário, peso 700 virou 600. As
    páginas de erro já não tinham marcação própria. Testes: `docker compose exec -T front python
    -m pytest -c intranet/web/pyproject.toml intranet/web/tests/unit/test_conformidade_templates.py`.
    Vermelho: 2 failed (`acesso/_troca.html`, `login.css`). Verde: unit e telas 413 passed,
    cobertura 100%.
- [x] **T11.6** Início, processos, processo e envio no padrão; estado de ingestão no badge. RF-VIS-04. Fase 3; P3, D7.
  - Vermelho: `intranet/web/tests/telas/test_processos.py::test_estado_de_ingestao_aparece_no_badge`; grupo "processos" sai da lista de pendentes.
  - Verde: `inicio.html`, `processos/`, `componentes/envio.html`, `inicio.css`, `processos.css`, `processo.css`.
  - Limpeza: nenhuma.
  - Entregue: `componentes/tabela.html` aceita `corpo` (template das linhas), e as tabelas de
    processos, arquivos e alertas passam por ele (`_linhas_processos.html`,
    `_linhas_arquivos.html`, `_linhas_alertas.html`; colunas em `COLUNAS_*` das views);
    `componentes/badge.html` aceita `testid` e `estado`, e a situação da lista e o estado do arquivo
    vão no badge (o `.selo` de `processos.css` saiu); botões pelo `botao.html`, inclusive no
    `envio.html`; cores literais e sombras de `inicio.css` e `processos.css` trocadas por tokens,
    peso 700 virou 600. Testes: `docker compose exec -T front python -m pytest -c
    intranet/web/pyproject.toml intranet/web/tests/unit/test_conformidade_templates.py
    intranet/web/tests/telas/test_processos.py`. Vermelho: 3 failed (CSS, templates, badge).
    Verde: unit e telas 420 passed, cobertura 100%; ruff e mypy limpos.
- [x] **T11.7** Dossiê, validações e visualizador no padrão; resultados no selo. RF-VIS-03, RF-VIS-04. Fase 4; P2, P3, D7.
  - Vermelho: `intranet/web/tests/telas/test_validacoes.py::test_resultado_tempestivo_aparece_no_selo_de_sucesso` e `::test_atencao_e_falha_usam_selo_do_seu_tom`; grupo "dossiê" sai da lista de pendentes.
  - Verde: templates de dossiê, validações e visualizador; `dossie.css`, `validacoes.css`, `visualizador.css`.
  - Limpeza: nenhuma.
  - Entregue: resultado do achado no `selo.html` (novo parâmetro `testid`) nas validações e no
    dossiê, pelo `rotulos.TOM_DO_RESULTADO`: `conforme` em sucesso, `verificar` em atenção,
    `atencao` em falha (mantém os tons que cada resultado já tinha: verde, âmbar e vermelho);
    status de fato, "substituído", sinais da peça e status do evento no badge; índice de peças e
    histórico de achados pelo `tabela.html` com `corpo` (`_linhas_pecas.html`,
    `_linhas_historico.html`); botões pelo `botao.html`; `.selo`/`.resultado` próprios saíram de
    `dossie.css` e `validacoes.css`; `visualizador.css` com `--superficie-suave`, `--fundo` e
    `--atencao` (preenchimento com `fill-opacity`) no lugar das cores literais; peso 700 virou 600.
    Testes: `docker compose exec -T front python -m pytest -c intranet/web/pyproject.toml
    intranet/web/tests/unit/test_conformidade_templates.py intranet/web/tests/telas/test_validacoes.py`.
    Vermelho: 4 failed (CSS, templates e os dois do selo). Verde: unit e telas 426 passed,
    cobertura 100%; ruff e mypy limpos.
- [x] **T11.8** Chat no padrão. RF-VIS-04. Fase 5; P3.
  - Vermelho: grupo "chat" sai da lista de pendentes e o teste de conformidade falha.
  - Verde: templates de `chat/` e `chat.css`; rótulo de IA e citações (RF-INT-05) intactos nos testes existentes.
  - Limpeza: nenhuma.
  - Entregue: o aviso de mensagem do chat passa pelo `aviso.html` (novos parâmetros `testid` e
    `status`, que mantêm `data-testid="mensagem"` e `data-status`); "Perguntar" pelo `botao.html`
    com `desabilitado`; a classe `aviso-msg` (nota discreta, não um aviso) virou `observacao-msg`;
    peso 700 de `chat.css` virou 600. Rótulo de IA e citações sem mudança. Testes: `docker compose
    exec -T front python -m pytest -c intranet/web/pyproject.toml
    intranet/web/tests/unit/test_conformidade_templates.py`. Vermelho: 1 failed (templates de
    `chat/`; o CSS já não tinha cor literal). Verde: unit e telas 426 passed, cobertura 100%.
- [x] **T11.9** Auditoria e usuários no padrão; lista de pendentes eliminada. RF-VIS-01, RF-VIS-04. Fase 6; P1, P3, D5.
  - Vermelho: grupo "gestão" sai da lista de pendentes e o teste de conformidade falha.
  - Verde: templates de `auditoria/` e `usuarios/`, `auditoria.css`, `usuarios.css`; a lista de pendentes sai do teste.
  - Limpeza: remover regras CSS que ficaram sem uso.
  - Entregue: as tabelas de eventos, contagem, chamadas ao modelo e usuários passam pelo
    `tabela.html` com `corpo` (`auditoria/_linhas_*.html`, `usuarios/_linhas_usuarios.html`;
    colunas em `COLUNAS_*` das views); botões pelo `botao.html`, que ganha `rotulo_acessivel`
    (`aria-label` de "Reativar", "Resetar senha" e "Resetar autenticador"). `PENDENTES`,
    `_pendente` e `test_pendentes_citam_arquivos_que_existem` saíram do teste: a regra vale para
    todos os templates e CSS. Limpeza: a varredura de classes dos CSS contra templates, JS e
    views só achou classes montadas em tempo de execução (`selo-*`, `zoom-*`); nenhuma regra
    removida. Testes: `docker compose exec -T front python -m pytest -c
    intranet/web/pyproject.toml intranet/web/tests/unit/test_conformidade_templates.py`.
    Vermelho: 1 failed (templates de `auditoria/` e `usuarios/`). Verde: unit e telas 433
    passed, cobertura 100%; ruff e mypy limpos.
- [x] **T11.10** Axe com todas as regras, tabela a 375 px e capturas da `/padrao`; guias regerados. RF-VIS-04, RF-VIS-06, RNF-09. Fase 7; P4, D10.
  - Revisão manual (E2E): `intranet/web/tests/e2e/test_acessibilidade.py::test_axe_sem_violacoes_em_toda_tela` (sem filtro de tags, dois temas, inclui `/padrao`), `::test_tabela_larga_rola_sozinha_em_375px`, `test_capturas.py::test_capturas_do_padrao_nos_tres_formatos`; violações achadas corrigidas em commit próprio; `docs/imagens/` regerado por `capturas.sh`.
  - Pronto quando: `bash intranet/web/scripts/e2e.sh` verde e capturas conferidas pelo usuário.
  - Entregue: `varrer` sem `runOnly` e o teste renomeado para `test_axe_sem_violacoes_em_toda_tela`,
    que falha em qualquer violação (antes só sérias e críticas das tags WCAG A/AA) e inclui a
    `/padrao`; `test_tabela_larga_rola_sozinha_em_375px` (auditoria a 375 px: a página não rola de
    lado e a `.tabela-rolavel` rola); `test_capturas_do_padrao_nos_tres_formatos`. A `/padrao`
    roda no E2E pela D11 (`LUPA_AMBIENTE=desenvolvimento` só no `front`). Correções achadas: a
    regra `.cartao h3` da T11.3 vazava para o `h3` das telas (agora
    `.cartao[data-componente="cartao"] h3`); as legendas das tabelas do relatório de uso
    ("... por ação/versão") colidiam com `get_by_label("Por")` e viraram "Contagem de eventos" e
    "Chamadas ao modelo em cada versão". `docs/imagens/` regerado por `capturas.sh`; capturas de
    toda tela (claro/escuro, 1200 e 375 px) e da `/padrao` geradas fora do repositório. Testes:
    `bash intranet/web/scripts/e2e.sh`. Vermelho: a varredura nova já veio sem violação do axe;
    o vermelho foi 1 failed em `test_chat_auditoria.py::test_relatorio_por_usuario_traz_o_custo_estimado`
    (modo estrito do `get_by_label("Por")`). Verde: E2E 37 passed em 85 s; `capturas.sh` 3
    passed; unit e telas 433 passed, cobertura 100%. Pendente: conferência das capturas pelo
    usuário.
- [x] **T11.11** Documentação. RF-VIS-04. Fase 8.
  - Revisão manual: `docs/sistema/padrao-visual.md` (tokens, componentes com exemplo de `include`, SHA-256 das fontes), `docs/sistema/front.md`, `docs/README.md`, `CHANGELOG.md` em "Não publicado".
  - Pronto quando: `LUPA_EXIGIR_CABECALHOS=1 bash scripts/verificar.sh` verde.
  - Entregue: `docs/sistema/padrao-visual.md` (tokens, componentes e parâmetros com exemplo de
    `include`, badge e selo, `/padrao`, axe e capturas, SHA-256 das fontes), parágrafo em
    `docs/sistema/front.md`, linha em `docs/README.md` e entrada em `CHANGELOG.md` ("Não
    publicado"). Comando: `LUPA_EXIGIR_CABECALHOS=1 bash scripts/verificar.sh` e `bash
    intranet/web/scripts/e2e.sh`. Verde: pipeline 702 passed (95,25%), intranet 266 passed
    (98,23%), integração 6, injeção 2, web 436 passed (100%), cabeçalhos ok em 4 rotas, agente
    11; E2E 37 passed em 85 s.

## Fase 12 — Limpeza da pipeline

Execução do [plano da limpeza da pipeline](plano_limpeza_pipeline.md). Cada tarefa é uma fase do
plano, onde estão os arquivos, o agente, as dependências, o vermelho e o verde. T12.1 a T12.7
entraram pelos PRs #20 a #26, antes da regra de um PR por plano (decisão 63); da T12.8 em diante,
tudo vai na branch `refactor/limpeza-pipeline`, num único PR. A evidência das tarefas novas fica
no "Entregue" de cada fase.

- [x] **T12.1** `ingestao/texto.py` com `dobrar` único. RNF-08, RF-ING-03. Fase 1; P1, D1, D2.
  - Vermelho: `pipeline/tests/ingestao/test_texto.py::test_dobrar_preserva_o_comprimento_com_caractere_que_muda_de_tamanho` (falha na importação).
  - Verde: `texto.dobrar` com a regra de `datas.py`; `datas.py`, `deteccao.py`, `eventos/*`, `identificacao.py`, `lupa_api/agente/ferramentas/leitura.py` e `recusa.py` importam de `texto`; saem as duas cópias.
  - Limpeza: nenhuma.
  - Entregue: `texto.dobrar` e `_dobrar_caractere` (regra de `datas.py`); saem as cópias de
    `datas.py` e `deteccao.py`; 12 módulos e `test_saneamento.py` importam de `texto`. As duas
    regras coincidem nos casos conferidos (o NFD decompõe antes do `lower()`). Testes: `docker
    compose exec -T worker python -m pytest -c pipeline/pyproject.toml
    pipeline/tests/ingestao/test_texto.py --no-cov` e `bash scripts/verificar.sh`. Vermelho: 1
    failed (`assert '' == 'istanbul acao'`, com `dobrar` provisório). Verde: pipeline 703 passed
    (95,25%), intranet 266 passed (98,23%), integração 6, injeção 2; ruff e mypy limpos.
- [x] **T12.2** `levenshtein` e normalizações em `texto.py`. RNF-08. Fase 1; P3, D2.
  - Vermelho: `pipeline/tests/ingestao/test_texto.py::test_levenshtein_com_prefixo_e_sufixo_comuns`, `::test_colapsar_espacos_aplica_nfc`, `::test_maiusculas_sem_acento_remove_pontuacao`.
  - Verde: `texto.levenshtein` (versão de `medicao`), `colapsar_espacos`, `maiusculas_sem_acento`; `hibridas`, `sinais_fronteira` e `sinteticos/medicao` passam a importá-las; saem as cópias e os três `normalizar`/`_normalizar`.
  - Limpeza: nenhuma.
  - Entregue: as três funções em `texto.py`; saem `hibridas.levenshtein` e `_normalizar`,
    `medicao.levenshtein` e `normalizar` e `sinais_fronteira.normalizar`; `classificacao.py`,
    `scripts/medir_extracao.py`, `test_hibridas.py` e `test_medicao.py` importam de `texto`
    (só o import mudou nos testes). `colapsar_espacos` aplica NFC também na medição dos
    sintéticos. Testes: `docker compose exec -T worker python -m pytest -c
    pipeline/pyproject.toml pipeline/tests/ingestao/test_texto.py --no-cov` e `bash
    scripts/verificar.sh` (stack inteira, inclui o código da T12.1). Vermelho: 3 failed
    (`assert -1 == 1`, texto sem colapsar, texto sem maiúsculas, com funções provisórias).
    Verde: saída 0; pipeline 706 passed (95,24%), intranet 266 passed (98,23%), integração 6,
    injeção 2, web 436 passed (100%), cabeçalhos e isolamento ok, agente 11. Na T12.1 o script
    tinha parado na suíte web por falta do contêiner `proxy`; esta execução cobre as duas.
- [x] **T12.3** `PaginaTexto` guarda o texto dobrado e as datas. RF-FAT-01. Fase 2; P2, D3.
  - Vermelho: `pipeline/tests/ingestao/eventos/test_fatos.py::test_candidatos_iguais_com_texto_da_pagina_guardado` (compara com os candidatos dos sintéticos e conta uma dobragem por página).
  - Verde: `cached_property` `dobrado` e `datas` em `eventos/modelo.PaginaTexto`; `fatos`, `capa`, `base`, `recurso`, `preparo` e `decisao_agravada` leem delas; `capa._valor` recorta o dobrado.
  - Limpeza: `CONVERSORES_CAPA` no lugar dos ifs de `capa._valor`.
  - Entregue: `PaginaTexto.dobrado` e `PaginaTexto.datas` (`cached_property`); os seis
    extratores leem delas; `capa` com `CONVERSORES_CAPA` (`_valor_da_causa`,
    `_data_de_distribuicao`, `_literal` como padrão) sobre o recorte do dobrado. O teste ficou em
    `pipeline/tests/ingestao/test_eventos.py`, onde estão os testes dos extratores (não existe
    `tests/ingestao/eventos/`); os candidatos esperados são os que o código anterior produzia
    para uma petição de apelação sintética. Testes: `docker compose exec -T worker python -m
    pytest -c pipeline/pyproject.toml pipeline/tests/ingestao/test_eventos.py --no-cov -k
    guardado` e `bash scripts/verificar.sh` (stack inteira). Vermelho: 1 failed (`assert 5 ==
    1`, cinco dobragens da mesma página). Verde: saída 0; pipeline 707 passed (95,24%),
    intranet 266 passed (98,23%), integração 6, injeção 2, web 436 passed (100%), cabeçalhos e
    isolamento ok, agente 11.
- [x] **T12.4** Contagem única no calendário e `dias_uteis_entre`. RF-VAL-02. Fase 3; P6, D7.
  - Vermelho: `pipeline/tests/validacoes/test_calendario.py::test_dias_uteis_entre_registra_feriado_com_fonte`.
  - Verde: `_contar` e `dias_uteis_entre` em `calendario.py`; `contar_prazo_util`, `_prorrogar` e `fonte_em` sobre eles; sai `contar_prazo_corrido` com o teste dele, no mesmo commit (D9).
  - Limpeza: nenhuma.
  - Revisão: especialista-validacoes.
  - Entregue: o laço único é o gerador `_dias_seguintes`, usado por `contar_prazo_util` e pelo
    novo `dias_uteis_entre` (dias úteis em `(inicio, fim]` e os dias pulados); saem
    `contar_prazo_corrido` e `_prorrogar` (só ela usava) com
    `test_prazo_corrido_sem_feriado_vence_no_dia_nominal`. `fonte_em` fica para a T12.5, que
    funde feriados e fontes. Os testes novos são
    `test_dias_uteis_entre_registra_feriado_e_fim_de_semana` e
    `test_dias_uteis_entre_sem_intervalo_e_zero` (a fonte do feriado entra na T12.5).
    Especialista-validacoes: aprovado, mesmo vencimento e dias pulados, regra dos arts. 219 e
    224 do CPC sem mudança. Testes: `docker compose exec -T worker python -m pytest -c
    pipeline/pyproject.toml pipeline/tests/validacoes --no-cov` e `bash scripts/verificar.sh`
    (stack inteira). Vermelho: 2 failed (`assert -1 == 3`, `(-1, ()) == (0, ())`, com função
    provisória). Verde: saída 0; pipeline 708 passed (95,29%), intranet 266 passed (98,23%),
    integração 6, injeção 2, web 436 passed (100%), cabeçalhos e isolamento ok, agente 11.
- [x] **T12.5** `Calendario.feriados` com descrição e fonte; tempestividade pelo calendário. RF-VAL-02. Fase 3; P6, D7.
  - Vermelho: `pipeline/tests/validacoes/test_motor_e_regras.py::test_tempestividade_com_atraso_mantem_o_texto`.
  - Verde: `Feriado` e `Mapping[date, Feriado]` em `calendario.py` e `dados.montar_calendario`; sai `fontes`; `tempestividade.py` usa `dias_uteis_entre`.
  - Limpeza: nenhuma.
  - Revisão: especialista-validacoes.
  - Entregue: `calendario.FeriadoCalendario(descricao, fonte)` (o nome `Feriado` já é o modelo
    do YAML em `dados.py`); `Calendario.feriados: Mapping[date, FeriadoCalendario]`, sem
    `fontes`; `fonte_em` lê a fonte do feriado; `montar_calendario` monta com
    `f.fonte or arq.fonte`; `tempestividade.py` usa `dias_uteis_entre` e mantém `fonte_em` em
    cada dia descartado. Os testes com feriado em texto passam a usar `FeriadoCalendario`
    (mudança de tipo, mesma asserção). `test_tempestividade_com_atraso_mantem_o_texto` ficou
    em `test_tempestividade.py`, onde estão os testes da regra, e fixa a saída do código
    anterior (passa antes e depois); o vermelho é
    `test_calendario.py::test_calendario_guarda_descricao_e_fonte_de_cada_feriado`.
    Especialista-validacoes: aprovado, mesma explicação, atraso, dias não contados e fontes.
    Testes: `docker compose exec -T worker python -m pytest -c pipeline/pyproject.toml
    pipeline/tests/validacoes --no-cov` e `bash scripts/verificar.sh` (stack inteira).
    Vermelho: 1 failed (`isinstance('Dia do Servidor Público…', FeriadoCalendario)` falso).
    Verde: saída 0; pipeline 710 passed (95,28%), intranet 266 passed (98,23%), integração 6,
    injeção 2, web 436 passed (100%), cabeçalhos e isolamento ok, agente 11.
- [x] **T12.6** Tabela de dispensas própria e `Coleta.qualidade()`. RF-VAL-03, RF-VAL-04. Fase 4; P7, D8.
  - Vermelho: `pipeline/tests/validacoes/test_motor_e_regras.py::test_dispensa_por_qualidade_le_a_tabela_de_dispensas`.
  - Verde: `validacoes/dados/dispensas.yaml`, `TabelaDispensas` e `dispensas_padrao()` em `dados.py`; sai `dispensas` de `preparo.yaml`; `preparo` e `representacao` usam `coleta.qualidade()`; `VERSAO_CATALOGO` sobe.
  - Limpeza: nenhuma.
  - Revisão: especialista-validacoes.
  - Decisão nova (usuário, 21/11/2026): sem as dispensas, `preparo.yaml` ficaria vazio, e
    `eventos/partes.py` e a versão `fatos` do reprocessamento também o liam; o arquivo é
    renomeado para `dispensas.yaml`, `partes.py` lê dele e o reprocessamento passa a citar
    `dispensas=`, regravando fatos e achados uma vez. O plano (tabelas e D8) foi atualizado.
  - Entregue: `dispensas.yaml` 0.3.0 (`rotulo`, `preparo`, `mandato` por qualidade, mesmos
    valores); `Dispensa`, `TabelaDispensas` e `dispensas_padrao()`, saem `TabelaPreparo` e
    `preparo_padrao`; `Coleta.qualidade()`; `preparo.py` e `representacao.py` testam
    `dispensa.preparo`/`dispensa.mandato` e citam `dispensa.rotulo`; `VERSAO_CATALOGO` 0.3.0;
    `achados_exemplo.json` só troca `versao_catalogo` (rule D8, mesmo commit).
    Especialista-validacoes: aprovado, achados iguais salvo `versao_dados` e
    `versao_catalogo`. Testes: `docker compose exec -T worker python -m pytest -c
    pipeline/pyproject.toml pipeline/tests/validacoes --no-cov` e `bash scripts/verificar.sh`
    (stack inteira). Vermelho: erro de coleta (`cannot import name 'dispensas_padrao'`).
    Verde: saída 0; pipeline 711 passed (95,29%), intranet 266 passed (98,23%), integração 6,
    injeção 2, web 436 passed (100%), cabeçalhos e isolamento ok, agente 11.
- [x] **T12.7** Reprocessamento pela versão nova do catálogo. RF-ING-08. Fase 4; D8.
  - Vermelho: `pipeline/tests/ingestao/test_reprocessamento.py::test_nova_versao_do_catalogo_regrava_achados_com_o_mesmo_texto` (integração).
  - Verde: nenhuma mudança além da T12.6 se o mecanismo atual já regravar; senão, a menor correção em `reprocessamento.py`.
  - Limpeza: nenhuma.
  - Entregue: só o teste. O worker processa uma apelação sintética da Defensoria com
    `VERSAO_CATALOGO` 0.2.0 (em `apoio`, `motor` e `reprocessamento`) e reinicia com a versão
    atual; os achados passam a 0.3.0 com o mesmo resultado e explicação. Sem vermelho: o
    mecanismo da T12.6 já regrava, como a tarefa previa; o teste exige achados no primeiro
    processamento e versões distintas antes e depois. Testes: `docker compose run --rm -e
    LUPA_EXIGIR_INTEGRACAO=1 worker python -m pytest -c pipeline/pyproject.toml
    pipeline/tests/ingestao/test_reprocessamento.py --no-cov -k catalogo` (1 passed) e `bash
    scripts/verificar.sh` (stack inteira, saída 0): pipeline 712 passed (95,29%), intranet 266
    passed (98,23%), integração 6, injeção 2, web 436 passed (100%), cabeçalhos e isolamento
    ok, agente 11.
- [x] **T12.8** Conflito interrompe a regra. RF-FAT-02, RF-VAL-01. Fase 4; P7, D8.
  - Vermelho: `pipeline/tests/validacoes/test_motor_e_regras.py::test_conflito_interrompe_a_regra_e_vira_verificar`.
  - Verde: `FatoPendenteError` em `apoio.py`, levantada por `Coleta.unico`; o motor captura e devolve `coleta.verificar()`; saem as checagens `if coleta.conflitos` das regras e `Coleta.pendente`.
  - Limpeza: nenhuma.
  - Revisão: especialista-validacoes.
  - Decisão nova (usuário, 21/11/2026): só o conflito em fato opcional interrompe a regra; o
    obrigatório continua registrando e devolvendo `None`, para o "verificar" listar todas as
    faltas e divergências. A conversão fica no decorador `@regra` das quatro regras, não no
    motor, para as regras chamadas direto (testes e linha de comando) manterem o contrato. O
    plano (tabela, D8 e "Regra com conflito") foi atualizado.
  - Entregue: `FatoPendenteError(coleta)` e `regra` em `apoio.py`; `unico(...,
    obrigatorio=False)` em conflito levanta; `@regra` em `preparo`, `representacao`,
    `tempestividade` e `cabimento`; saem as três checagens de `preparo.py` e `Coleta.pendente`.
    Especialista-validacoes: aprovado, achados idênticos (só o preparo usa fato opcional).
    Testes: `docker compose exec -T worker python -m pytest -c pipeline/pyproject.toml
    pipeline/tests/validacoes --no-cov` e `bash scripts/verificar.sh` (stack inteira).
    Vermelho: erro de coleta (`cannot import name 'FatoPendenteError'`). Verde: saída 0;
    pipeline 713 passed (95,35%), intranet 266 passed (98,23%), integração 6, injeção 2, web
    436 passed (100%), cabeçalhos e isolamento ok, agente 11.
- [x] **T12.9** Peça procurada por regra, modelo memorizado, fim de `para_modelo` — RF-VAL-01, RF-VAL-05. [fase F9](plano_limpeza_pipeline.md)
- [ ] **T12.10** `Fato.valor` escalar com leitura do formato antigo — RF-FAT-01. [fase F10](plano_limpeza_pipeline.md)
- [ ] **T12.11** Outorgante da procuração como sujeito — RF-VAL-04. [fase F11](plano_limpeza_pipeline.md)
- [ ] **T12.12** Ids de fato e evidência pelo hub — RF-FAT-01. [fase F12](plano_limpeza_pipeline.md)
- [ ] **T12.13** Registro de extratores por espécie — RF-FAT-01. [fase F13](plano_limpeza_pipeline.md)
- [ ] **T12.14** Etapas em lista ordenada no worker — RF-ING-08. [fase F14](plano_limpeza_pipeline.md)
- [ ] **T12.15** Formatos por mime e nomes internos no diagnóstico — RF-ING-07. [fase F15](plano_limpeza_pipeline.md)
- [ ] **T12.16** Extração paralela sem gabinete — RF-ING-04, RF-ING-07. [fase F16](plano_limpeza_pipeline.md)
- [ ] **T12.17** Gravação de páginas em lote — RF-ING-03. [fase F17](plano_limpeza_pipeline.md)
- [ ] **T12.18** MinIO para arquivo e PDF aberto pelo caminho — RF-ING-04. [fase F18](plano_limpeza_pipeline.md)
- [ ] **T12.19** Leituras repetidas na fila e nos repositórios — RF-ING-07. [fase F19](plano_limpeza_pipeline.md)
- [ ] **T12.20** Remoção do código sem uso — RNF-08. [fase F20](plano_limpeza_pipeline.md)
- [ ] **T12.21** Duplicações menores da ingestão — RNF-08, RF-ING-03. [fase F21](plano_limpeza_pipeline.md)
- [ ] **T12.22** Sintéticos sem repetição — RNF-04. [fase F22](plano_limpeza_pipeline.md)
- [ ] **T12.23** Documentação — RNF-08. [fase F23](plano_limpeza_pipeline.md)
