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
- [ ] **T2.3** Remover o perfil de produção: `docker-compose.prod.yml`, `instalar_piloto.sh`, `conferir_piloto.py`, `preparar_repositorio.md`, `vault/producao/` e os modos `acme` e `fornecido` do proxy. D25. RES-11.

## Fase 3 — Data Vault e gabinete único

- [ ] **T3.1** `dominio/chaves.py`. A1. D4, D5. RES-02.
- [ ] **T3.2** `dominio/tabelas.py` no Data Vault, `migrations/esquema_v0001.py`, `versions/v0001_data_vault.py` e `test_migracao_0001`; remoção das revisões `v0001` a `v0012`. D3, D6, D7, D8, D9, D18. RES-02, RES-03, RES-13.
- [ ] **T3.3** `dominio/gravacao.py` e `dominio/visoes.py`; teste de imutabilidade sob `lupa_app`. A2. D6, D13. RES-13.
- [ ] **T3.4** Enum `PapelUsuario` com dois papéis; `acesso/` sobre hubs e satélites; `criar_desembargador.py`. A14. D11. RF-ACE-01 a 05.
- [ ] **T3.5** Cofre com chave única, DEK em `sat_processo_chave`, caminho de objeto novo; cifra dos satélites. D14. RF-SEG-01, RF-SEG-02, RES-08.
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
