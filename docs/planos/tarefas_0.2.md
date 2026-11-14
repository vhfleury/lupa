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
    Correção depende de decisão do usuário.
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
  - Não feito: o teste da saúde com cofre selado (RF-SEG-02) depende de `create_app` (T3.14); a
    varredura pela API (`intranet/api/tests/seguranca/test_cifra_banco.py`) também.

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
- [ ] **T3.6** Processos: cadastro com classe, lista, responsáveis, sem `materia`, `sigiloso` e 403. D12, D15 (`ClasseProcessual`, `StatusProcesso`). RF-PRO-01 a 04.
- [ ] **T3.7** Recepção e estado da ingestão em satélites de `hub_arquivo`. A3. D9. RF-ING-01, 02, 06.
- [ ] **T3.8** Worker sem Redis e RQ; remoção de `fila.py`, `redis` e `rq`. A4. D10. RF-ING-07, RES-07.
- [ ] **T3.9** Páginas, diagnóstico, lotes e peças em satélites (conteúdo jurídico ainda da 0.1). A5 passos 1 a 7. RF-ING-03.
- [ ] **T3.10** Evidências, fatos, achados e anotações em hubs, links e satélites; remoção de `reu`, `reu_identidade` e da pseudonimização. A5 passos 8 a 11, A11, A12. RF-FAT-01, RF-FAT-03, RF-PEC-02, RF-DOS-06.
- [ ] **T3.11** Auditoria como link não historizado, cadeia única, consulta, relatório de uso com custo. A15. D8, D26. RF-AUD-01 a 05.
- [ ] **T3.12** Conversa, mensagens, chamada ao modelo e processo em revisão. A16. D26. RF-CHA-06, 07, 08.
- [ ] **T3.13** Descarte. A13. RF-PRO-05.
- [ ] **T3.14** Rotas da API com ids em texto; remoção de `/gabinetes*`. D12, D27.
- [ ] **T3.15** Scripts sem gabinete e administrador (`e2e_*`, `limpar_dev`, `calibrar`, `ponta_a_ponta`, `criar_usuario_banco`).
- [ ] **T3.16** Suíte completa verde nos dois pacotes. D23.

## Fase 4 — Conteúdo cível

- [ ] **T4.1** Enums cíveis (`TipoPeca`, `TipoFato`, `OrigemPeca`, `Polo`, `QualidadeParte`, `MetodoClassificacao`). D15.
- [ ] **T4.2** Sintéticos das cinco classes, com templates e gabarito. RNF-04, RNF-05.
- [ ] **T4.3** Classificação e fronteiras de peças cíveis. RF-PEC-01.
- [ ] **T4.4** Partes. A6 passos 1 e 2. RF-FAT-04.
- [ ] **T4.5** Extratores de fatos cíveis. A6 passos 3 a 8. D17. RF-FAT-01, RF-FAT-02.
- [ ] **T4.6** Catálogo por classe e dados do CPC (`prazos_recursos.yaml`, `preparo.yaml`, `cabimento_art1015.yaml`). D16. RF-VAL-01.
- [ ] **T4.7** Tempestividade. A7. RF-VAL-02.
- [ ] **T4.8** Preparo. A8. RF-VAL-03.
- [ ] **T4.9** Representação. A9. RF-VAL-04.
- [ ] **T4.10** Cabimento do agravo. A10. RF-VAL-05.
- [ ] **T4.11** Linha de comando das validações e `fatos_exemplo.json`. RF-VAL-06.
- [ ] **T4.12** Agente cível: prompt, recusa, ferramenta de cálculo, contexto sem pseudônimos, dossiê com partes. RF-CHA-01 a 05, RF-DOS-01 a 04.
- [ ] **T4.13** Ponta a ponta de cada classe contra o gabarito; reprocessamento preserva correção. RF-ING-04, RF-ING-08, RNF-01, RNF-02.

## Fase 5 — Interface

- [ ] **T5.1** Permissões e menu com dois papéis; remoção da tela de gabinetes. RF-ACE-03.
- [ ] **T5.2** Tipos, API e rótulos cíveis; ids em texto. D12.
- [ ] **T5.3** Telas de processos: cadastro com classe, lista, dossiê com partes, validações, visualizador. RF-DOS-01 a 05.
- [ ] **T5.4** Telas de usuários e auditoria. RF-ACE-04, RF-AUD-04, RF-AUD-05.
- [ ] **T5.5** `docker build --target verificacao intranet/web` verde.

## Fase 6 — Regressão

- [ ] **T6.1** Corpus de injeção e suíte do agente sobre os sintéticos cíveis. RF-ING-05, RF-CHA-05, RNF-03.
- [ ] **T6.2** E2E e capturas adaptados. RNF-09.
- [ ] **T6.3** Cabeçalhos do proxy e saída de rede do worker. RF-SEG-03, RF-SEG-04.
- [ ] **T6.4** `scripts/verificar.sh` completo verde.

## Fase 7 — Documentação e versão

- [ ] **T7.1** `docs/arquitetura.md` e `docs/sistema/*.md`. RF-DOC-03.
- [ ] **T7.2** Guias do assessor e do desembargador. RF-DOC-01.
- [ ] **T7.3** `docs/conformidade/CONFORMIDADE.md` e `docs/operacao/operacao.md`. RF-DOC-02.
- [ ] **T7.4** ADRs 0013 a 0016 e `docs/decisoes/registro.md`.
- [ ] **T7.5** `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `docs/README.md`, `CHANGELOG.md` e versão `0.2.0`.
