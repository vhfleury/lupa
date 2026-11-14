# Plano da versão 0.2

13 de novembro de 2026 · Estado: **aprovado** · Atende a
[especificação da 0.2](../especificacao/0.2/especificacao.md) · Algoritmos e checklist de testes em
[plano_0.2_execucao.md](plano_0.2_execucao.md)

## O que muda

### Banco

O banco é recriado do zero. Convenções que valem para todas as linhas da tabela abaixo:

- `hk_*` é `BYTEA NOT NULL` com `CHECK (octet_length = 32)`.
- Todo hub tem `hk_<entidade>` (PK), a chave de negócio (única), `load_dts TIMESTAMPTZ NOT NULL
  DEFAULT clock_timestamp()` e `record_source TEXT NOT NULL`.
- Todo link tem `hk_<link>` (PK; o nome do link sem `link_`, como `hk_processo_arquivo`), os `hk_` dos hubs ligados (FK, únicos em conjunto, um índice por
  FK), `load_dts` e `record_source`.
- Todo satélite tem PK `(hk_<pai>, load_dts)`, FK para o pai, `hash_diff BYTEA NOT NULL` e
  `record_source`. Satélite multiativo acrescenta a coluna indicada à PK.
- `(C)` marca coluna cifrada com a DEK do processo (`TextoCifrado` ou `JsonCifrado`).
- Toda tabela tem o trigger `<tabela>_imutavel`.
- `load_dts` vem sempre do banco (`clock_timestamp()`); a aplicação não o informa. Instante de
  negócio injetado (relógio da requisição) fica em atributo próprio (`ultimo_acesso_em`,
  `expira_em`, `ocorrido_em`).
- Coluna de enum é `TEXT` com `CHECK ... IN (...)` gerado dos enums do domínio.

| Objeto | Depois |
| --- | --- |
| `hub_usuario` | chave: `nome_usuario TEXT` |
| `hub_processo` | chave: `numero_cnj TEXT` (20 dígitos) |
| `hub_arquivo` | chave: `numero_cnj TEXT`, `sha256 TEXT` |
| `hub_pagina` | chave: `numero_cnj TEXT`, `sha256 TEXT`, `numero INTEGER` |
| `hub_peca` | chave: `numero_cnj TEXT`, `sha256 TEXT`, `pagina_inicial INTEGER` |
| `hub_evidencia` | chave: `numero_cnj TEXT`, `sha256 TEXT`, `numero INTEGER`, `inicio INTEGER`, `fim INTEGER`; `CHECK (inicio >= 0 AND fim > inicio)` |
| `hub_fato` | chave: `numero_cnj TEXT`, `tipo TEXT` (enum `TipoFato`), `sujeito TEXT` (hex de `hk_parte` ou vazio), `hk_evidencia_origem BYTEA`; trigger `fato_exige_evidencia` |
| `hub_achado` | chave: `numero_cnj TEXT`, `validacao TEXT`, `sujeito TEXT` |
| `hub_parte` | chave: `numero_cnj TEXT`, `chave_nome BYTEA` (HMAC do nome normalizado, D5) |
| `hub_conversa` | chave: `conversa_id UUID` |
| `hub_sessao` | chave: `token_sha256 TEXT` |
| `hub_desafio_mfa` | chave: `token_sha256 TEXT` |
| `hub_chave_login` | chave: `chave TEXT` (SHA-256 do nome digitado) |
| `link_processo_arquivo` | `hk_processo`, `hk_arquivo` |
| `link_arquivo_pagina` | `hk_arquivo`, `hk_pagina` |
| `link_arquivo_peca` | `hk_arquivo`, `hk_peca` |
| `link_pagina_evidencia` | `hk_pagina`, `hk_evidencia` |
| `link_processo_fato` | `hk_processo`, `hk_fato` |
| `link_fato_evidencia` | `hk_fato`, `hk_evidencia` |
| `link_processo_achado` | `hk_processo`, `hk_achado` |
| `link_achado_fato` | `hk_achado`, `hk_fato` |
| `link_processo_parte` | `hk_processo`, `hk_parte` |
| `link_processo_responsavel` | `hk_processo`, `hk_usuario` |
| `link_processo_conversa` | `hk_processo`, `hk_conversa`, `hk_usuario` |
| `link_sessao_usuario` | `hk_sessao`, `hk_usuario` |
| `link_desafio_mfa_usuario` | `hk_desafio_mfa`, `hk_usuario` |
| `link_chamada_modelo` (não historizado) | `hk_chamada` (PK), `hk_processo`, `hk_conversa` (nulo), `modelo TEXT`, `versao_prompt TEXT`, `hash_prompt_sistema TEXT`, `hash_entrada TEXT`, `hash_saida TEXT`, `tokens_entrada INTEGER`, `tokens_saida INTEGER`, `latencia_ms INTEGER`, `ferramentas TEXT[]`, `resultado TEXT` (enum); índice `(hk_processo, load_dts)` |
| `link_evento_auditoria` (não historizado) | `hk_evento` (PK), `sequencia BIGINT UNIQUE`, `ocorrido_em TIMESTAMPTZ`, `hk_usuario` (nulo), `hk_processo` (nulo), `acao TEXT`, `objeto_tipo TEXT`, `objeto_id TEXT`, `ip TEXT`, `localizacao TEXT`, `resultado TEXT`, `versao_modelo TEXT`, `versao_prompt TEXT`, `hash_anterior TEXT`, `hash_evento TEXT NOT NULL`; índices `(ocorrido_em)`, `(hk_usuario, ocorrido_em)`, `(hk_processo, ocorrido_em)`, `(acao, ocorrido_em)`, `(ip, ocorrido_em)` |
| `sat_usuario_cadastro` | `papel TEXT` (enum), `ativo BOOLEAN` |
| `sat_usuario_credencial` | `senha_hash TEXT`, `troca_senha_obrigatoria BOOLEAN`, `mfa_segredo TEXT`, `mfa_confirmado BOOLEAN`, `mfa_ultimo_passo BIGINT` |
| `sat_processo_dados` | `classe TEXT` (enum `ClasseProcessual`), `hk_usuario` (criador) |
| `sat_processo_estado` | `status TEXT` (enum `StatusProcesso`) |
| `sat_processo_chave` | `chave_dados_cifrada TEXT NOT NULL` |
| `sat_processo_revisao` | `situacao TEXT` (`aberta`, `liberada`), `motivo TEXT`, `status_anterior TEXT`, `hk_usuario` (nulo) |
| `sat_arquivo_dados` | `tamanho_bytes INTEGER CHECK (> 0)`, `nome_original TEXT (C)`, `mime TEXT`, `chave_storage TEXT`, `hk_usuario` |
| `sat_arquivo_ingestao` | `estado TEXT` (enum `EstadoJob`), `motivo_quarentena TEXT` (enum), `motivo_falha TEXT` (enum), `tentativas INTEGER`, `total_paginas INTEGER`, `manifesto JSONB`, `relatorio JSONB`, `versao_extrator TEXT`; `CHECK ((estado = 'quarentena') = (motivo_quarentena IS NOT NULL))`; índice `(estado, load_dts)` |
| `sat_arquivo_lote` (multiativo: `numero`) | `numero INTEGER`, `estado TEXT` (enum `EstadoLote`), `resultado JSONB` |
| `sat_arquivo_diagnostico` | `cenario TEXT` (enum), `total_paginas INTEGER CHECK (>= 0)`, `tem_indice BOOLEAN`, `sinais JSONB`, `fronteiras_origem JSONB`, `metadados_descartados JSONB` |
| `sat_pagina_extracao` | `tipo TEXT` (enum), `texto TEXT (C)`, `hash_texto TEXT`, `texto_nativo TEXT (C)`, `texto_ocr TEXT (C)`, `coordenadas JSONB`, `sinais JSONB`, `extracao JSONB`, `versao_extrator TEXT`, `origem_arquivo TEXT`, `pagina_origem INTEGER` |
| `sat_pagina_saneamento` | `texto_normalizado TEXT (C)`, `flags JSONB`, `trechos_ocultos JSONB (C)`, `trechos_suspeitos JSONB (C)` |
| `sat_pagina_fronteira` | `sinais_fronteira JSONB` |
| `sat_peca_classificacao` | `tipo TEXT` (enum `TipoPeca`), `pagina_final INTEGER`, `confianca DOUBLE PRECISION CHECK (BETWEEN 0 AND 1)`, `metodo TEXT` (`regra`, `manual`), `origem TEXT` (enum), `data DATE`, `tipo_data TEXT` (`assinatura`, `protocolo`, `juntada`), `hk_evidencia_data` (nulo), `flags JSONB`, `classificacao JSONB`, `vigente BOOLEAN`, `hk_usuario` (nulo) |
| `sat_evidencia_trecho` | `trecho TEXT (C)`, `hash_trecho TEXT`, `bbox JSONB` |
| `sat_fato_valor` | `valor JSONB (C)`, `extraido_por TEXT`, `versao_extrator TEXT`, `confianca DOUBLE PRECISION CHECK (BETWEEN 0 AND 1)`, `status TEXT` (enum `StatusFato`), `hk_usuario` (nulo) |
| `sat_fato_anotacao` (multiativo) | `texto TEXT (C)`, `hk_usuario`; rótulo de cifra `anotacao.texto`, o mesmo de `sat_achado_anotacao`, para `v_anotacao` decifrar as duas |
| `sat_fato_evidencia_vigencia` (satélite de `link_fato_evidencia`) | `vigente BOOLEAN` |
| `sat_achado_resultado` | `versao_catalogo TEXT`, `resultado TEXT` (enum), `fatos_usados BYTEA[]`, `valores JSONB (C)`, `explicacao TEXT (C)` |
| `sat_achado_anotacao` (multiativo) | `texto TEXT (C)`, `hk_usuario` |
| `sat_parte_identidade` | `nome TEXT (C)`, `polo TEXT` (enum `Polo`), `qualidade TEXT` (enum `QualidadeParte`), `hk_evidencia` |
| `sat_processo_responsavel_vigencia` (satélite de `link_processo_responsavel`) | `vigente BOOLEAN` |
| `sat_conversa_estado` | `encerrada BOOLEAN`, `motivo_encerramento TEXT`, `tokens_entrada BIGINT`, `tokens_saida BIGINT`, `paginas_originais INTEGER`, `citacoes_descartadas INTEGER` |
| `sat_conversa_mensagem` (multiativo: `sequencia`) | `sequencia INTEGER`, `papel TEXT` (enum), `status TEXT` (enum), `texto TEXT (C)`, `citacoes JSONB`, `avisos JSONB` |
| `sat_sessao_estado` | `papel TEXT` (enum `PapelUsuario`), `expira_em TIMESTAMPTZ`, `ultimo_acesso_em TIMESTAMPTZ`, `revogada BOOLEAN`, `ip_criacao TEXT` |
| `sat_desafio_mfa_estado` | `papel TEXT` (enum `PapelUsuario`), `expira_em TIMESTAMPTZ`, `consumido BOOLEAN` |
| `sat_chave_login_falha` (multiativo) | sem atributo além dos técnicos; `load_dts` é o instante da falha |
| `sat_chave_login_bloqueio` | `bloqueado_ate TIMESTAMPTZ` (nulo: um login certo zerou as falhas) |
| Views `v_usuario`, `v_processo`, `v_arquivo`, `v_pagina`, `v_peca`, `v_evidencia`, `v_fato`, `v_achado`, `v_parte`, `v_conversa`, `v_sessao`, `v_desafio_mfa`, `v_bloqueio_login` | uma linha por hub com a linha mais recente de cada satélite; `id TEXT` é o hex do `hk`; `v_processo` traz `em_revisao BOOLEAN`; `v_peca` e `v_fato` trazem `vigente` e os `id` do pai (`v_fato.vigente`: o fato tem ao menos uma evidência com vigência corrente verdadeira); `v_bloqueio_login` traz `bloqueado_ate`, `zerado_em` e `falhas TIMESTAMPTZ[]` (instantes das falhas depois do último zeramento) |
| Views `v_peca_historico`, `v_fato_historico` | todas as linhas do satélite, com `load_dts` e autor |
| View `v_mensagem` | linhas de `sat_conversa_mensagem` por conversa, em ordem de `sequencia` |
| View `v_anotacao` | união de `sat_fato_anotacao` e `sat_achado_anotacao`, com `alvo_tipo`, `alvo_id`, autor e data |
| View `v_responsavel` | pares processo–usuário com `vigente` |
| View `v_fila_ingestao` | arquivos cujo estado corrente é `recebido`, `validado` ou `em_extracao`, do mais antigo para o mais novo |
| View `v_auditoria` | `link_evento_auditoria` com `nome_usuario` e `numero_cnj` |
| Função `lupa_bloquear_alteracao() RETURNS trigger` | recusa `UPDATE`; recusa `DELETE` salvo com `lupa.descarte = 'on'` na transação |
| Função `lupa_fato_exige_evidencia() RETURNS trigger` | `CONSTRAINT TRIGGER` adiado em `hub_fato`: exige linha em `link_fato_evidencia` |
| Função `lupa_descartar_processo(p_hk_processo BYTEA) RETURNS TEXT` | `SECURITY DEFINER`; algoritmo A13; devolve o SHA-256 da DEK cifrada apagada |
| Papel `lupa_app` | `SELECT` e `INSERT` nas tabelas; `SELECT` nas views; `EXECUTE` em `lupa_descartar_processo`; sem `UPDATE`, `DELETE` nem `TRUNCATE` |

Removidos da 0.1: as 26 tabelas (`gabinete`, `usuario`, `processo`, `processo_responsavel`,
`arquivo`, `pagina`, `peca`, `evidencia`, `fato`, `fato_evidencia`, `reu`, `reu_identidade`,
`achado`, `anotacao`, `evento_auditoria`, `sessao`, `desafio_mfa`, `falha_login`,
`bloqueio_login`, `job_ingestao`, `lote_ingestao`, `diagnostico_arquivo`, `conversa`, `mensagem`,
`chamada_modelo`, `revisao_processo`), todas as políticas `<tabela>_por_gabinete`, a função
`lupa_bloquear_update`, a função `lupa_descartar_processo` antiga, os triggers
`fato_exige_evidencia` e `fato_evidencia_nao_orfa` antigos e as revisões `v0001` a `v0012`.

### Arquivos

`→` é mover com ajuste de imports (`lupa.` vira `lupa_pipeline.` ou `lupa_intranet.`).

| Arquivo | Ação |
| --- | --- |
| `src/lupa/config.py`, `src/lupa/logging.py` | → `pipeline/src/lupa_pipeline/`; saem as chaves de Redis, métricas, backup, GeoIP fica |
| `src/lupa/dominio/enums.py` | → pipeline; reescreve `TipoPeca`, `TipoFato`, `OrigemPeca`, `PapelUsuario`, `StatusProcesso`, `MetodoClassificacao`; cria `ClasseProcessual`, `Polo`, `QualidadeParte`; remove `Materia` (D15) |
| `src/lupa/dominio/tabelas.py` | → pipeline; reescrito com as tabelas do Data Vault |
| `src/lupa/dominio/esquemas.py`, `repositorios.py`, `correcoes.py` | → pipeline; reescritos sobre views e satélites |
| `src/lupa/dominio/sessao.py` | → pipeline; fica só `assumir_papel_aplicacao` |
| `src/lupa/dominio/cnj.py` | → pipeline |
| `pipeline/src/lupa_pipeline/dominio/chaves.py` | cria: `chave_hash`, `hash_diff`, `hmac_processo` (A1) |
| `pipeline/src/lupa_pipeline/dominio/gravacao.py` | cria: `gravar_hub`, `gravar_link`, `gravar_satelite` (A2) |
| `pipeline/src/lupa_pipeline/dominio/visoes.py` | cria: mapeamento somente leitura das views |
| `src/lupa/seguranca/*` | → pipeline; `chaves.py` e `cofre.py` passam a uma chave única; sai a chave de identidades; `descarte.py` chama a função nova |
| `src/lupa/migrations/` (11 revisões, 9 `esquema_v*.py`) | remove |
| `pipeline/src/lupa_pipeline/migrations/{alembic.ini,env.py,ambiente.py,script.py.mako}` | → de `src/lupa/migrations/` |
| `pipeline/src/lupa_pipeline/migrations/versions/v0001_data_vault.py`, `migrations/esquema_v0001.py` | cria |
| `alembic.ini` (raiz) | remove |
| `src/lupa/ingestao/fila.py`, `metricas.py` | remove |
| `src/lupa/ingestao/worker.py` | → pipeline; laço próprio sem RQ (A4) |
| `src/lupa/ingestao/repositorio.py`, `repositorio_pecas.py`, `repositorio_eventos.py`, `estados.py`, `recepcao.py`, `storage.py`, `cache.py`, `quarentena.py` | → pipeline; reescritos sobre satélites; sem lease, fencing e `gabinete_id` |
| `src/lupa/ingestao/classificacao.py`, `fronteiras.py`, `indice.py`, `origem.py`, `data_peca.py`, `dados/classificacao.yaml`, `dados/titulos_peca.yaml`, `dados/fronteiras.yaml` | → pipeline; vocabulário cível |
| `src/lupa/ingestao/eventos/{denuncia,recebimento,decisao_prisao,reus}.py`, `dados/tipos_penais.yaml` | remove |
| `src/lupa/ingestao/eventos/{base,etapa,fatos,modelo,padroes,saida}.py`, `dados/eventos.yaml` | → pipeline; tipos de fato cíveis |
| `src/lupa/ingestao/eventos/{certidao,recurso,sentenca}.py` | → pipeline; reescritos para o cível |
| `pipeline/src/lupa_pipeline/ingestao/eventos/{partes,preparo,procuracao,decisao_agravada,marcos}.py` | cria (A6) |
| demais `src/lupa/ingestao/*` (sandbox, parser, OCR, sinais, roteador, saneamento, renderização, extração, diagnóstico, datas, calibração, inventário, qualidade, hibridas, imagem nativa, metadados, oculto, detecção, texto nativo, dados de saneamento) | → pipeline |
| `src/lupa/validacoes/criminal/`, `dados/prescricao_art109.yaml`, `dados/preventiva.yaml`, `templates/prescricao_*`, `templates/revisao_preventiva_*` | remove |
| `pipeline/src/lupa_pipeline/validacoes/civel/{tempestividade,preparo,representacao,cabimento}.py` | cria (A7 a A10) |
| `pipeline/src/lupa_pipeline/validacoes/dados/{prazos_recursos.yaml,preparo.yaml,cabimento_art1015.yaml}` | cria ou reescreve com o CPC |
| `pipeline/src/lupa_pipeline/validacoes/templates/{tempestividade_recurso,preparo_recurso,representacao_recurso,cabimento_agravo}_{conforme,atencao,verificar}.txt` | cria ou reescreve |
| `src/lupa/validacoes/{catalogo,motor,__main__,adaptador,apoio,calendario,dados,modelo,versao}.py`, `dados/feriados/`, `dados/suspensoes_prazo.yaml`, `templates/motor_erro.txt` | → pipeline; catálogo por classe em vez de matéria |
| `src/lupa/sinteticos/*.py` | → pipeline; roteiros e gabaritos das cinco classes; `identidades.py` gera partes |
| `src/lupa/sinteticos/templates/{denuncia,recebimento,decisao_prisao,revisao_prisao,termo_depoimento,certidao_intimacao_defesa,certidao_intimacao_mp,certidao_intimacao_reu}.txt` | remove |
| `pipeline/src/lupa_pipeline/sinteticos/templates/{peticao_inicial,contestacao,replica,decisao_interlocutoria,apelacao,agravo_instrumento,agravo_interno,embargos_declaracao,certidao_intimacao,procuracao,comprovante_preparo,parecer_mp}.txt` | cria |
| `src/lupa/sinteticos/templates/{sentenca,acordao,contrarrazoes,certidao_publicacao,juntada,laudo,enchimento,recurso}.txt` | → pipeline; texto cível; `recurso.txt` sai (substituído pelos quatro de recurso) |
| `src/lupa/api/*` | → `intranet/api/src/lupa_intranet/api/`; ids passam a texto (D12); sai a definição de gabinete por requisição |
| `src/lupa/api/rotas/saude.py`, `ingestao.py` | → intranet; sai `/metricas/servico` |
| `src/lupa/api/rotas/processos.py` | → intranet; classe obrigatória; saem `materia`, `sigiloso` e o 403 |
| `src/lupa/acesso/*` | → intranet; saem administrador e gabinetes; `instalacao.py` cria o desembargador (A14) |
| `src/lupa/auditoria/*` | → intranet; cadeia única (A15); sai o destaque do administrador |
| `src/lupa/agente/*` | → intranet; `contexto.py` sem pseudônimos; `ferramentas/calculo.py` com prazos do CPC; `dados/prompt_sistema.md` e `dados/recusa.yaml` cíveis; `dossie.py` com partes |
| `tests/{dominio,seguranca,ingestao,validacoes,sinteticos}/`, `tests/unit/{test_config,test_logging}.py` | → `pipeline/tests/`; reescritos junto com o módulo que testam |
| `tests/ingestao/{test_rotas,test_pecas_api,test_validacoes_api,test_visualizador}.py`, `tests/{acesso,agente,api,auditoria}/`, `tests/unit/test_verificar_cabecalhos.py` | → `intranet/api/tests/` |
| `tests/backup/`, `tests/api/test_metricas_servico.py`, `tests/ingestao/test_observabilidade.py`, `tests/seguranca/test_migracao_0010.py`, `tests/validacoes/{test_prescricao,test_preventiva}.py`, `tests/acesso/test_sessao_e_gabinetes.py` | remove com o código (regra do CLAUDE.md) |
| `tests/conftest.py` | divide em `pipeline/tests/apoio/` (fábricas e fixtures comuns) e um `conftest.py` por pacote |
| `pipeline/tests/dominio/test_migracao_0001.py` | cria: sobe e desce com `migrar` |
| `front/` | → `intranet/web/` |
| `intranet/web/src/routes/gabinetes/` | remove |
| `intranet/web/src/lib/{permissoes,tipos,api,sessao.svelte}.ts`, `lib/processos/{tipos,rotulos,envio}.ts`, `lib/auditoria/auditoria.ts`, `lib/componentes/{MenuLateral,FormNovoUsuario}.svelte`, `routes/processos/**`, `routes/usuarios/`, `routes/auditoria/` | altera: dois papéis, classe, partes, tipos cíveis, ids em texto |
| `intranet/web/e2e/testes/auditoria-admin.spec.ts` | renomeia para `auditoria.spec.ts`; demais specs e `capturas.spec.ts` adaptados |
| `proxy/` | → `intranet/proxy/`; ficam `Caddyfile` e `modos/interno.caddy`; saem `acme.caddy`, `fornecido.caddy`, `sem-certificado.pem` |
| `scripts/{gerar_autos,medir,medir_extracao,ponta_a_ponta,calibrar}.py` | → `pipeline/scripts/` |
| `scripts/{limpar_dev,criar_usuario_banco}.py` | → `intranet/api/scripts/` |
| `scripts/criar_admin.py` | → `intranet/api/scripts/criar_desembargador.py` |
| `scripts/{e2e_preparar,e2e_processos,e2e_semear_chat,verificar_cabecalhos}.py`, `scripts/validar_caddyfile.sh` | → `intranet/api/scripts/`; sem gabinete e administrador |
| `scripts/{backup,backup_comum,backup_conteiner,cron_backup,expurgar_backups,restaurar,instalar_piloto}.sh`, `scripts/conferir_piloto.py`, `scripts/preparar_repositorio.md` | remove |
| `scripts/verificar.sh`, `scripts/vault_inicializar.sh` | altera: dois pacotes; só modo de desenvolvimento do Vault; o script cria a chave `lupa` (D14) |
| `vault/politicas/lupa.hcl` | altera: só a chave `lupa`, sem apagar chave (D14) |
| `monitoramento/`, `vault/producao/`, `docker-compose.prod.yml` | remove |
| `pyproject.toml`, `requirements*.txt` (raiz) | remove |
| `pipeline/pyproject.toml`, `intranet/api/pyproject.toml` e os `requirements*.txt` de cada um (`make lock`) | cria; saem `redis`, `rq`, `prometheus-client`; versão `0.2.0` |
| `Dockerfile` (raiz) | → `pipeline/Dockerfile` |
| `intranet/api/Dockerfile` | cria: instala `lupa_pipeline` e `lupa_intranet`; contexto de build na raiz |
| `docker-compose.yml` | altera: saem `redis`, `backup`, `backup-agendado`, `prometheus`, `grafana` e seus volumes; `worker` com healthcheck no banco; caminhos novos |
| `Makefile`, `.env.example`, `.dockerignore`, `.gitignore` | altera: caminhos e variáveis |
| `.claude/agents/tdd.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `README.md`, `CHANGELOG.md` | altera: caminhos, comandos e escopo |
| `docs/arquitetura.md`, `docs/sistema/*.md`, `docs/guias/*.md`, `docs/conformidade/CONFORMIDADE.md`, `docs/operacao/operacao.md`, `docs/README.md` | reescreve para a 0.2 |
| `docs/operacao/backup.md` | remove |
| `docs/adr/0013-data-vault.md`, `0014-fila-no-banco.md`, `0015-gabinete-unico-sem-pseudonimizacao.md`, `0016-dois-pacotes.md` | cria; 0013 substitui 0001, 0014 substitui 0002 |
| `docs/planos/tarefas_0.2.md` | cria na fase de tarefas |

### O que não muda

- Sandbox de parsing, extração de páginas, OCR, roteador, sinais e saneamento contra injeção.
- Formato da cifra (`LUPAOBJ`, prefixo `lupa1:`), envelope e recusa de dado em claro; no campo
  `lupa1:` o cabeçalho e o AAD levam o `hk_processo` (32 bytes) no lugar do UUID (D12, D14).
- Motor de validações, calendário de dias úteis, formato do achado e templates de frase fixa.
- Conferência de citações, política de recusa, tetos e cliente roteirizado do agente.
- Encadeamento por hash da auditoria e formato do evento.
- Senha com Argon2, TOTP, duração de sessão (8 h) e inatividade (30 min).
- Caddy com os cabeçalhos de segurança; front como SPA estática.
- Caminho e verbo das rotas da API, salvo as removidas em D27.
- Redes `interna`, `ingestao`, `borda` e `cliente`; `worker` sem saída de rede.
- Python 3.12, FastAPI, SQLAlchemy, Alembic, SvelteKit 2, Svelte 5.

## Problemas

- **P1.** O código Python é um pacote só (`lupa`, em `src/`) e o front está em `front/`.
- **P2.** `api`, `acesso`, `auditoria` e `agente` importam `dominio`, `seguranca`, `ingestao` e
  `validacoes`; o sentido contrário não existe. Quatro testes de `tests/ingestao/` exercitam rotas
  da API.
- **P3.** As 26 tabelas são relacionais, com `gabinete_id`, RLS forçada e FKs compostas.
- **P4.** Sessão, job, lote, usuário, conversa e processo mudam por `UPDATE`; página e
  diagnóstico, por upsert.
- **P5.** A fila usa Redis e RQ, com lease, heartbeat, fencing token e varredor.
- **P6.** Enums, classificação de peças, extratores, validações, sintéticos, prompt e rótulos do
  front são criminais.
- **P7.** Papel administrador e gabinetes aparecem em `acesso`, rotas, front, E2E e scripts.
- **P8.** Réus são pseudonimizados (`reu`, `reu_identidade`, chave de identidades); processo
  sigiloso recebe 403.
- **P9.** Monitoramento, backup e perfil de produção ocupam compose, scripts, testes e docs.
- **P10.** O descarte apaga linhas de 13 tabelas por uma função do banco.
- **P11.** A API e o front identificam objetos por UUID.
- **P12.** A documentação descreve a 0.1.
- **P13.** `pyproject.toml`, `Dockerfile`, compose, `Makefile` e `verificar.sh` assumem `src/`,
  `tests/` e `front/`.

## Decisões

- **D1.** Árvore: `pipeline/{src/lupa_pipeline,tests,scripts}`, `intranet/api/{src/lupa_intranet,
  tests,scripts}`, `intranet/web/` (com `e2e/`), `intranet/proxy/`. Na raiz ficam
  `docker-compose.yml`, `Makefile`, `vault/`, `scripts/verificar.sh` e
  `scripts/vault_inicializar.sh`.
- **D2.** `lupa_intranet` depende de `lupa_pipeline`; `lupa_pipeline` não importa `lupa_intranet`.
  Um teste varre os imports e falha se o sentido inverter.
- **D3.** Nomes: `hub_`, `link_`, `sat_<pai>_<assunto>`, `v_<entidade>`; colunas técnicas em
  inglês, atributos em português.
- **D4.** Chave por hash: SHA-256 das partes da chave de negócio, normalizadas e unidas por `|`
  (A1), calculada no Python.
- **D5.** `hash_diff` é SHA-256 do conteúdo canônico; em satélite com coluna `(C)` e em
  `hub_parte.chave_nome`, HMAC-SHA-256 com a DEK do processo, para não expor texto por
  dicionário.
- **D6.** Só inserção: mudança de estado é linha nova, gravada apenas quando o `hash_diff` difere
  do corrente (A2). O trigger `lupa_bloquear_alteracao` recusa o resto. O descarte é a exceção
  (A13).
- **D7.** Autoria (`hk_usuario` em satélite) é atributo com FK, não link. Links ficam para as
  relações da RES-03.
- **D8.** Evento de auditoria e chamada ao modelo são links não historizados, com os atributos na
  própria linha.
- **D9.** Não há hub de job: o estado da ingestão é satélite de `hub_arquivo`.
- **D10.** Fila: um worker, que lê `v_fila_ingestao` a cada `LUPA_FILA_INTERVALO_S` (padrão 2 s) e
  segura um advisory lock do PostgreSQL; segundo worker encerra ao não obter o lock (A4).
- **D11.** `ultimo_acesso_em` da sessão só ganha linha nova quando o último registro tem 60 s ou
  mais.
- **D12.** O identificador público de cada objeto é o hex do `hk` (64 caracteres), em rotas, JSON
  e front.
- **D13.** A API lê só as views e grava só por `lupa_pipeline.dominio.gravacao` e pelos
  repositórios. O histórico de achados usa `v_achado_historico`, complemento aprovado em 14/11/2026.
- **D14.** Cofre com uma chave Transit, `lupa`; DEK por processo em `sat_processo_chave`. Objetos
  em `processo/<hex do hk_processo>/<sha256>`. Anotação passa a ser cifrada.
- **D15.** Enums: `ClasseProcessual` (`apelacao_civel`, `agravo_instrumento`,
  `embargos_declaracao`, `agravo_interno`, `acao_originaria`); `TipoPeca` (3.2 da especificação);
  `OrigemPeca` (`juizo`, `mp`, `parte`, `terceiro`, `desconhecida`); `TipoFato`
  (`data_decisao_recorrida`, `data_intimacao`, `tipo_recurso`, `data_interposicao`,
  `qualidade_recorrente`, `comprovante_preparo`, `gratuidade_pedido`, `gratuidade_decisao`,
  `advogado_subscritor`, `procuracao`, `hipotese_decisao_agravada`, `data_ajuizamento`,
  `data_citacao`, `data_contestacao`, `data_acordao`); `Polo` (`ativo`, `passivo`, `terceiro`);
  `QualidadeParte` (`fazenda_publica`, `ministerio_publico`, `defensoria_publica`, `particular`);
  `PapelUsuario` (`assessor`, `desembargador`); `StatusProcesso` sem `bloqueado`;
  `MetodoClassificacao` sem `llm`.
- **D16.** Validações: `tempestividade_recurso`, `preparo_recurso`, `representacao_recurso`,
  `cabimento_agravo`. O recurso conferido é o do tipo da classe do processo, um achado por
  recorrente. O catálogo mapeia classe para validações conforme a tabela 3.1 da especificação.
- **D17.** O diretório `ingestao/eventos/` mantém o nome.
- **D18.** Uma revisão Alembic, `v0001_data_vault`, com `esquema_v0001.py`.
- **D19.** Fábricas e fixtures comuns ficam em `pipeline/tests/apoio/`, no `pythonpath` do pytest
  dos dois pacotes.
- **D20.** Cobertura mínima de 90% medida por pacote (`--cov=lupa_pipeline`,
  `--cov=lupa_intranet`).
- **D21.** Testes de `pipeline/` rodam na imagem do `worker`; os de `intranet/api/`, na da `api`.
  A imagem do `worker` copia `pipeline/`; a da `api` copia `pipeline/` e `intranet/api/`, com
  `/app` como diretório de trabalho.
- **D22.** Serviços do compose: `api`, `front`, `proxy`, `worker`, `db`, `minio`, `minio-init`,
  `vault`, `e2e`. Volumes: `db-dados`, `minio-dados`, `vault-dados`.
- **D23.** Na fase 3 a suíte completa fica vermelha entre tarefas; cada tarefa fecha com o seu
  arquivo de teste verde (`--no-cov`) e a fase fecha com a suíte completa verde.
- **D24.** Um commit por tarefa em `feat/versao-0.2`; um PR para `develop` no fim.
- **D25.** Sem servidor do piloto: saem o perfil de produção, a instalação e a conferência do
  piloto e os modos de certificado `acme` e `fornecido`.
- **D26.** Mantidos da 0.1: localização por IP (`geoip2`), custo estimado (`precos.yaml`),
  processo em revisão (`sat_processo_revisao`), E2E e capturas.
- **D27.** Rotas removidas: `GET /gabinetes`, `POST /gabinetes`, `POST
  /gabinetes/{gabinete_id}/rotacionar-chave`, `GET /metricas` e `GET /metricas/servico`. A rotação
  da chave única passa a ser feita no Vault pelo responsável técnico.

## Fases

1. **Reestruturação** — move código, testes, front, proxy e scripts para `pipeline/` e
   `intranet/` sem mudar comportamento; suíte da 0.1 verde. P1, P2, P13; D1, D2, D19 a D22;
   RES-04, RES-05, RES-12, RNF-06, RNF-08.
2. **Remoções de infraestrutura** — tira monitoramento, backup e perfil de produção. P9; D25;
   RES-11.
3. **Data Vault e gabinete único** — banco novo, gravação só por inserção, fila no banco, dois
   papéis, sem pseudonimização nem sigilo, descarte novo, ids em texto. P3, P4, P5, P7, P8, P10,
   P11; D3 a D14, D18, D23, D26; RF-ACE, RF-PRO, RF-ING-01, 02, 06, 07, RF-AUD, RF-SEG, RF-CHA-06
   a 08, RES-01, 02, 03, 07, 08, 09, 13.
4. **Conteúdo cível** — enums, peças, partes, fatos, quatro validações, sintéticos e agente.
   P6; D15, D16, D17; RF-PEC, RF-FAT, RF-VAL, RF-ING-03, 04, 05, 08, RF-CHA-01 a 05, RNF-01 a 05.
5. **Interface** — telas com dois papéis, classe, partes e tipos cíveis. P6, P7, P11; D12;
   RF-DOS, RES-06.
6. **Regressão** — corpus de injeção, suíte do agente, E2E e capturas sobre os sintéticos cíveis.
   RNF-03, RNF-04, RNF-09.
7. **Documentação e versão** — documentos de sistema, guias, conformidade, ADRs, `CHANGELOG.md`
   e versão `0.2.0`. P12; RF-DOC.

## Execução

Na máquina de desenvolvimento, pelo agente.

1. Commit da última tarefa e PR de `feat/versao-0.2` para `develop`.
2. Com confirmação do usuário no momento, executar `docker compose down --remove-orphans` e
   remover os volumes `lupa_db-dados`, `lupa_minio-dados`, `lupa_prometheus-dados` e
   `lupa_grafana-dados`. Preservar `lupa_vault-dados`.
3. Construir as imagens, subir `db`, `minio`, `minio-init` e `vault` e executar
   `bash scripts/vault_inicializar.sh`. Com `docker compose run --rm -T api`, executar
   `alembic -c pipeline/src/lupa_pipeline/migrations/alembic.ini upgrade head`,
   `python intranet/api/scripts/criar_usuario_banco.py` e
   `python intranet/api/scripts/criar_desembargador.py`. Subir os serviços com
   `docker compose up -d --wait`.

Depois disso o usuário envia os processos de `dados/` pela interface.
