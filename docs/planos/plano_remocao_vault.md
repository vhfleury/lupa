# Plano — remoção do Vault e da cifra da aplicação

15 de novembro de 2026 · Estado: **aprovado** · Atende a
[especificação da 0.2](../especificacao/0.2/especificacao.md): RF-SEG-01 (reescrito), RF-SEG-02
(removido), RNF-07, RES-08; decisões 40 a 45.

## O que muda

### Banco

| Objeto | Antes | Depois |
| --- | --- | --- |
| `sat_processo_chave` (tabela) | envelope da DEK (`chave_dados_cifrada TEXT`) por processo | removida |
| `v_processo.chave_dados_cifrada` (`TEXT`, view) | DEK cifrada mais recente | removida; a view é recriada sem a coluna |
| `lupa_descartar_processo(BYTEA)` (função) | `RETURNS TEXT`: apaga satélites e envelope e devolve SHA-256 do envelope | `RETURNS VOID`: apaga os satélites de conteúdo |
| colunas hoje `TextoCifrado`/`JsonCifrado` (`TEXT`, `sat_arquivo_dados.nome_original`, `sat_pagina_extracao.texto*`, `sat_pagina_saneamento.*`, `sat_evidencia_trecho.trecho`, `sat_fato_valor.valor`, `sat_achado_resultado.*`, `sat_parte_identidade.nome`, `sat_conversa_mensagem.texto`, `anotacao.texto`) | `lupa1:<base64>` | texto em claro (JSON serializado nas que eram `JsonCifrado`); o tipo SQL não muda |
| `hub_parte.chave_nome` (`BYTEA`) | HMAC-SHA-256 do nome com a DEK | SHA-256 do nome normalizado |
| `hash_diff` dos satélites com conteúdo (`BYTEA`) | HMAC-SHA-256 com a DEK | SHA-256 do JSON canônico, como nos demais |
| objetos no MinIO | envelope `LUPAOBJ` cifrado com a DEK | bytes originais |

### Arquivos

| Arquivo | Ação |
| --- | --- |
| `pipeline/src/lupa_pipeline/migrations/versions/v0003_remocao_cofre.py` | criar: `upgrade` (D5) e `downgrade` |
| `pipeline/tests/dominio/test_migracao_0003.py` | criar: sobe e desce com `migrar` |
| `pipeline/src/lupa_pipeline/seguranca/cofre.py`, `contexto.py`, `chaves.py`, `envelope.py`, `tipos.py` | remover |
| `pipeline/src/lupa_pipeline/seguranca/descarte.py` | `descartar` sem retorno de chave (D6) |
| `pipeline/src/lupa_pipeline/dominio/tipos.py` | criar: `JsonTexto`, JSON serializado em `TEXT` (D3) |
| `pipeline/src/lupa_pipeline/dominio/tabelas.py` | `TextoCifrado` vira `Text` e `JsonCifrado` vira `JsonTexto` (D3); saem `sat_processo_chave` e `satelite_cifrado` |
| `pipeline/src/lupa_pipeline/dominio/visoes.py` | idem nas visões; sai `VisaoProcesso.chave_dados_cifrada` |
| `pipeline/src/lupa_pipeline/dominio/chaves.py` | sai `hmac_processo` e o parâmetro `dek` de `hash_diff`; entra `hash_nome` (SHA-256) |
| `pipeline/src/lupa_pipeline/dominio/gravacao.py` | `hash_diff` sem DEK |
| `pipeline/src/lupa_pipeline/ingestao/eventos/etapa.py` | `chave_nome` por `hash_nome` |
| `pipeline/src/lupa_pipeline/ingestao/storage.py` | sai `StorageCifrado`; `criar_storage` devolve o armazenamento direto |
| `pipeline/src/lupa_pipeline/ingestao/cache.py`, `calibracao.py`, `worker.py`, `repositorio_pecas.py` | sem ativar DEK nem recifrar páginas reaproveitadas |
| `pipeline/src/lupa_pipeline/sinteticos/gerador.py` | sem contexto de cifra |
| `pipeline/src/lupa_pipeline/config.py` | saem `cofre_backend` e `vault_*` |
| `pipeline/scripts/limpar_dev.py` | sem cofre |
| `intranet/api/src/lupa_intranet/api/cifra.py` | remover |
| `intranet/api/src/lupa_intranet/api/app.py` | sem criar cofre nem contexto de cifra por requisição |
| `intranet/api/src/lupa_intranet/api/saude.py`, `rotas/saude.py` | sai `verificar_cofre` e o campo `cofre` (D4) |
| `intranet/api/src/lupa_intranet/acesso/autorizacao.py`, `api/rotas/ingestao.py`, `api/rotas/processos.py`, `agente/repositorio.py` | saem as chamadas a `ativar_processo` |
| `intranet/api/src/lupa_intranet/api/rotas/descarte.py` | `objeto_id` do evento = id do processo (D6) |
| `intranet/api/scripts/e2e_processos.py` | sem cofre |
| `pipeline/tests/seguranca/test_cofre.py`, `test_envelope.py`, `test_cifra_satelites.py`, `test_dado_em_claro_recusado.py`, `intranet/api/tests/seguranca/test_cifra_banco.py` | remover junto com o código que fixam (D1) |
| `pipeline/tests/seguranca/test_sem_cofre.py` | criar: critérios de RF-SEG-01 |
| `pipeline/tests/apoio/apoio_comum.py`, `intranet/api/tests/conftest.py`, `pipeline/tests/dominio/test_chaves.py`, `test_migracao_0001.py`, `pipeline/tests/ingestao/test_processamento.py`, `test_recepcao.py`, `intranet/api/tests/acesso/test_autorizacao.py`, `api/test_saude.py`, `ingestao/test_rotas.py`, `seguranca/test_descarte.py` | tirar cofre em memória e DEK das fixtures; asserções de saúde e descarte seguem D4 e D6 |
| `docker-compose.yml` | sai o serviço `vault`, o volume `vault-dados`, `LUPA_VAULT_ENDERECO` e o `depends_on` de `api` e `worker` |
| `vault/` (`lupa.hcl`, `politicas/lupa.hcl`), `scripts/vault_inicializar.sh` | remover |
| `intranet/web/scripts/preparar-e2e.sh` | sem subir nem destravar o Vault |
| `.env.example` | saem `LUPA_COFRE_BACKEND` e `LUPA_VAULT_*` |
| `.gitignore`, `.dockerignore` | mantêm `.vault-dev`, que continua na máquina com as chaves de unseal da instalação anterior |
| `docs/sistema/criptografia.md` | remover; descarte vai para `docs/sistema/modelo-de-dados.md` |
| `docs/sistema/modelo-de-dados.md`, `ingestao.md`, `agente.md`, `auditoria.md`, `docs/arquitetura.md` | sem cofre e sem cifra |
| `docs/runbooks/destravar-vault.md` | remover; sai do `docs/runbooks/README.md` |
| `docs/operacao/operacao.md`, `README.md`, `CONTRIBUTING.md`, `docs/guias/guia-assessor.md`, `.claude/agents/tdd.md` | sem Vault |
| `CLAUDE.md` | "Segredos só por `.env`"; regra "Coluna nova com conteúdo de autos ... é cifrada" sai |
| `docs/adr/0018-remocao-do-cofre-e-da-cifra.md`, `docs/adr/README.md` | ADR novo que substitui 0007, 0011 e 0012 |
| `docs/decisoes/registro.md` | decisões 40 a 45, substituindo a decisão 8 |
| `docs/planos/tarefas_0.2.md` | fase 9 com as tarefas deste plano |
| `CHANGELOG.md` | `Não publicado`: Vault removido; reinstalação recria o banco |
| `docs/README.md` | link deste plano |

### O que não muda

- Senhas (hash) e segredo TOTP de `sat_usuario_credencial`, que não passavam pelo Vault.
- Tipos SQL das colunas de conteúdo (`TEXT`), hubs, links e demais views.
- O descarte continua apagando os satélites de conteúdo e os objetos no MinIO, com limpeza
  pendente retomável.
- MinIO, proxy HTTPS e cabeçalhos (RF-SEG-03), saída de rede (RF-SEG-04).
- Migrations `v0001` e `v0002`.

## Problemas

- **P1.** O Vault começa selado a cada reinício; até o unseal manual, a API devolve 500 em toda
  rota que cria ou lê processo.
- **P2.** A cifra amarra cada leitura e gravação a uma DEK ativa (`contexto_cifra`,
  `ativar_processo`), espalhada por rotas, worker, cache e fixtures.
- **P3.** Dados já gravados só se leem com o Vault; sem ele, ficam ilegíveis.

## Decisões

- **D1.** Remover Vault e toda a cifra da aplicação, no banco e nos objetos (decisão 40). Testes
  que fixam a cifra saem no mesmo commit do código.
- **D2.** Sem migração de dados: na instalação, apagar os volumes de banco, MinIO e Vault e
  reenviar os processos (decisão 42). Sem rotação de chave (decisão 43).
- **D3.** Colunas de conteúdo voltam a `Text`; as de JSON usam um `TypeDecorator` simples de
  serialização em `TEXT`, sem cifra, para não mudar o tipo SQL.
- **D4.** RF-SEG-02 removido: a saúde verifica API, banco e MinIO (decisão 41).
- **D5.** Migration `v0003`: `DROP VIEW v_processo`, recria sem `chave_dados_cifrada`;
  `DROP FUNCTION lupa_descartar_processo` e recria `RETURNS VOID` sem o envelope; `DROP TABLE
  sat_processo_chave`; privilégios para `lupa_app` como antes. `downgrade` recria a tabela vazia,
  a função `RETURNS TEXT` e a view da `v0002`.
- **D6.** Evento de descarte com `objeto_id` = id do processo (decisão 45).
- **D7.** `hub_parte.chave_nome` = SHA-256 do nome normalizado (decisão 44); `hash_diff` sempre
  SHA-256.

## Fases

1. Especificação e decisões: RF-SEG-01, RF-SEG-02, RNF-07, RES-08, decisões 40 a 45 (já
   alteradas, aguardando aprovação).
2. Teste vermelho de RF-SEG-01 (`test_sem_cofre.py`). RF-SEG-01.
3. Migration `v0003` e teste. D5. RF-SEG-01.
4. Domínio sem cifra: tipos, `hash_diff`, `chave_nome`, storage. D3, D7. RF-SEG-01.
5. Remoção do contexto de DEK da pipeline e da intranet; saúde e descarte. D4, D6. RF-SEG-01,
   RF-SEG-02.
6. Remoção do Vault da infraestrutura: compose, `vault/`, scripts, `.env.example`, E2E. D1, D2.
   RNF-07, RES-08.
7. Documentação, ADR 0018, registro, `CLAUDE.md`, `CHANGELOG.md`. D1 a D7.

## Passo a passo do algoritmo

### A1 — Gravação de um satélite com conteúdo

1. Entrada: tabela, `hk` do pai, atributos. Ação: serializar os atributos de JSON em texto.
   Saída: valores prontos para `TEXT`.
2. Ação: `hash_diff` = SHA-256 do JSON canônico dos atributos. Saída: `hash_diff`.
3. Se o `hash_diff` é igual ao da linha mais recente: parar sem gravar.
4. Ação: inserir a linha nova no satélite. Saída: linha gravada.

### A2 — Leitura de um satélite com conteúdo

1. Entrada: linha da view. Ação: devolver o `TEXT` como está; nas colunas de JSON, desserializar.
   Saída: valor.
2. Se o JSON é inválido: erro de integridade com o nome da coluna, sem o conteúdo.

### A3 — Identificação da parte

1. Entrada: nome extraído. Ação: normalizar como hoje. Saída: nome normalizado.
2. Ação: `chave_nome` = SHA-256 do nome normalizado. Saída: 32 bytes.
3. Ação: `hk_parte` = hash de (`numero_cnj`, `chave_nome`). Saída: chave do hub.

### A4 — Objeto no MinIO

1. Entrada: chave `processo/<hex>/...` e bytes. Ação: gravar os bytes sem envelope. Saída: objeto.
2. Leitura: devolver os bytes gravados.

### A5 — Descarte

1. Entrada: `hk_processo` travado. Ação: `lupa_descartar_processo` apaga os satélites de conteúdo.
2. Ação: gravar `sat_processo_estado` = `descartado` e o evento de auditoria com `objeto_id` = id
   do processo, na mesma transação. Saída: commit.
3. Ação: apagar originais e PNGs em cache no MinIO. Saída: contagem.
4. Se a etapa 3 falha: gravar evento de limpeza pendente; retomável pelo mesmo endpoint.

### A6 — Saúde

1. Ação: verificar API, banco e MinIO. Saída: `{"api", "banco", "minio"}`.
2. Se algum falha: 503 com o estado de cada um.

## Testes

- [ ] `test_sem_cofre.py`: processo criado e lido sem cofre; texto e original em claro no banco e
      no MinIO (RF-SEG-01, integração).
- [ ] `test_migracao_0003.py`: sobe e desce; `sat_processo_chave` some e volta.
- [ ] `test_chaves.py`: `hash_nome` determinístico; `hash_diff` sem DEK.
- [ ] `test_descarte.py`: evento com `objeto_id` = id do processo; objetos apagados.
- [ ] `test_saude.py`: sem campo `cofre`; 503 quando banco ou MinIO falha.
- [ ] Suítes completas de `pipeline` e `intranet` com cobertura ≥ 90%; `bash
      scripts/verificar.sh`; `bash intranet/web/scripts/e2e.sh`.

## Execução

1. Commit e PR citando as tarefas da fase 9.
2. `docker compose down`, `docker volume rm` dos volumes de banco, MinIO e `vault-dados`, e
   `docker compose up -d --build --wait`.
3. `docker compose exec api alembic -c pipeline/src/lupa_pipeline/migrations/alembic.ini upgrade
   head`; reenviar os processos pela interface.
