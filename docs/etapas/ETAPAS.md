# Lupa — Etapas da primeira versão

Este histórico reúne os 19 relatórios de execução citados pelo código e pelos manuais, as limitações e pendências por etapa e o balanço de conformidade. Os demais 78 relatórios estão no histórico do Git (commit `58e9774`). As revisões independentes estão no commit `54219a2`, na pasta `docs/etapas/`.

Cada etapa reúne as entregas do executor e os riscos e observações do revisor. Os itens fora do escopo vêm das seções “O que ficou de fora”, “Fora do escopo”, “Limitações” e “Pendente” dos relatórios. Alguns foram resolvidos em etapas seguintes. As medições e os comandos correspondem ao momento de cada registro. O [balanço de conformidade](#conformidade-geral) acompanha as entregas até a 8.2 e identifica as [divergências entre registros](#divergencias).

As referências a “revisão N, §M” remetem às revisões históricas. As decisões também estão no [registro de decisões](../decisoes/registro.md). As ações ainda abertas para o piloto e as questões para o advogado estavam nas pendências do piloto (removido; ver histórico do Git).

<a id="etapas-e-pendencias"></a>

## Índice por etapa

| Etapa | Registros |
| --- | --- |
| [0 — Esqueleto do projeto](#etapa-0) | Escopo e revisão |
| [1 — Esquemas de dados](#etapa-1) | Escopo e revisão |
| [2 — Motor de validações](#etapa-2) | Três validações do piloto e revisão |
| [3 — Autenticação, papéis e auditoria](#etapa-3) | Implementação, decisões, pendências, testes de carga e revisão |
| [4A — Fundações da ingestão](#etapa-4a) | 4A.1 a 4A.10 e revisão da 4A.1 |
| [4B — Autos sintéticos](#etapa-4b) | 4B.1 a 4B.5, 4B.8 a 4B.10 e revisão |
| [4C — Diagnóstico e páginas](#etapa-4c) | [4C.1](#etapa-4c-1), [4C.2](#etapa-4c-2), [4C.3](#etapa-4c-3), [4C.4](#etapa-4c-4), [4C.5](#etapa-4c-5), [4C.6](#etapa-4c-6), [4C.7](#etapa-4c-7), [4C.8](#etapa-4c-8), [4C.9](#etapa-4c-9), [4C.10](#etapa-4c-10) e revisão |
| [4D — Saneamento](#etapa-4d) | [4D.1](#etapa-4d-1), [4D.2](#etapa-4d-2), [4D.6](#etapa-4d-6), [4D.7](#etapa-4d-7) e [4D.10](#etapa-4d-10) |
| [4E — Fronteiras e índice](#etapa-4e) | [4E.1](#etapa-4e-1), [4E.2](#etapa-4e-2), [4E.9](#etapa-4e-9), [4E.10](#etapa-4e-10) e revisão |
| [4F — Eventos e ponta a ponta](#etapa-4f) | [4F.1](#etapa-4f-1) a [4F.10](#etapa-4f-10). Ponta a ponta na [4F.9](#etapa-4f-9) e calibração na [4F.10](#etapa-4f-10) |
| [5 — Agente e chat](#etapa-5) | 5.1 a 5.10 e balanço com o início da interface |
| [6 — Interface web](#etapa-6) | 6.1 a 6.10 e balanço da interface |
| [7 — Criptografia, backup e guias](#etapa-7) | [7.1](#etapa-7-1) a [7.10](#etapa-7-10), com relatórios de cifra de colunas ([7.5](#etapa-7-5)) e operação ([7.10](#etapa-7-10)) |
| [8 — Piloto](#etapa-8) | [8.1](#etapa-8-1) e [8.2](#etapa-8-2), com registro previsto para a [8.6](#etapa-8-6) |

<a id="etapa-0"></a>

## Etapa 0 — Esqueleto do projeto

### Escopo da entrega

- **Alembic não inicializado** (sem `alembic.ini`/`migrations/`): não há modelos até a Etapa 1. O alvo
  `make migrate` já chama `alembic upgrade head` e passará a funcionar quando a Etapa 1 criar `alembic.ini` e a pasta de migrações, como pediu a revisão.
- **Log de acesso do uvicorn** não está em JSON (sai no formato padrão do uvicorn; não contém corpo
  nem cabeçalhos e, segundo a revisão, ainda não expunha conteúdo sensível). Unificar com structlog fica para quando houver rotas com dados.
- Alvos do `Makefile` (`test`, `lint`, `typecheck`) rodam dentro do contêiner `api`; `format` roda
  no host porque altera arquivos do repositório.

### Revisão 0

**Riscos observados fora dos critérios**

- **MinIO deixou de ser mantido.** As imagens oficiais sumiram do Docker Hub e do Quay, o repositório aparece como arquivado em 2026, e a última imagem publicada carrega CVE conhecida. O executor usou o fork `pgsty/minio` fixado por digest, que é uma escolha razoável de curto prazo, mas é dependência de terceiro sem garantia de manutenção. O código da aplicação só conversa com a API S3, então trocar o servidor é barato agora e caro depois. Decisão para o responsável técnico antes da Etapa 4 (ingestão), que é a primeira que grava objetos.
- **Portas 8000 e 8080 ocupadas na máquina do piloto.** Sem impacto no código; o `.env` local usa 18000.

<a id="etapa-1"></a>

## Etapa 1 — Esquemas de dados

### Escopo da entrega

- Lógica de administrador multi-gabinete na RLS (gabinete nulo): é tema da Etapa 3; hoje o
  administrador não vê nada sob `lupa_app`. `usuario` e `evento_auditoria` já têm RLS pela mesma
  política.
- A dependência FastAPI que abre transação e chama `definir_gabinete` por requisição: depende da
  autenticação (Etapa 3). O procedimento está documentado em `docs/sistema/modelo-de-dados.md`.
- Cifra de `reu_identidade` e chave por gabinete: só a referência (`gabinete.chave_criptografia_ref`).
- Nenhuma dependência nova foi necessária.

### Revisão 1

**Observações menores, sem bloqueio**

- `_salvar_evidencia` usa `on_conflict_do_nothing`. Se uma evidência com o mesmo id chegar com conteúdo diferente, a segunda é ignorada em silêncio. Aceitável agora; a ingestão (Etapa 4) deve garantir ids novos por extração.
- `Fato.valor` volta do banco como JSON, então datas chegam como string ISO. A Etapa 2 precisa converter na entrada do motor. Conferir na revisão da Etapa 2.
- `arquivo` ficou imutável por trigger, além de `achado`. Coerente com os requisitos, embora não fosse critério.

<a id="etapa-2"></a>

## Etapa 2 — Motor de validações

### As três validações do piloto

- Pronúncia, acórdão e causas suspensivas da prescrição (fora do escopo da v1; aparecem como
  limitação na explicação e em `valores.limitacoes`).
- Execução por réu (`por_reu`) existe no modelo, mas o motor roda sobre o modelo recebido;
  quem chama decide recortar por réu.
- `README.md` não foi alterado (arquivo da Etapa 0, fora da lista permitida).

### Revisão 2

**Trabalho pendente gerado por esta etapa**

1. **Adaptador validações ↔ domínio (pequeno, antes da Etapa 4).** O executor diz que basta trocar o import, mas não é exato: em `lupa.dominio.esquemas`, `id` é `UUID` e não `str`, `evidencias` é tupla, `Achado` exige `processo_id` e `id`, e `Fato.valor` volta do banco com datas como string ISO. É preciso uma função `para_modelo(fatos_dominio) -> ModeloProcesso` e outra `para_dominio(achado, processo_id) -> Achado`, com teste de ida e volta usando a fixture `fabrica_fato` do `tests/conftest.py`. Só então os esquemas locais de `modelo.py` podem ser removidos.
2. **Tempestividade quando a defesa recorre exige as duas intimações (réu e defensor).** Faltando uma, o resultado é `verificar`. É a leitura conservadora do art. 392 e está documentada, mas vai gerar muitos "verificar" em réu solto intimado só pelo defensor. O gabinete decide se mantém.
3. **Prescrição após a sentença usa a pena em abstrato.** Depois da sentença condenatória, a prescrição que importa costuma ser pela pena aplicada (retroativa e intercorrente). Como a pena em abstrato é maior ou igual à aplicada, o cálculo atual nunca gera alarme falso, mas pode deixar de apontar prescrição. A limitação está no guia; a validação pela pena aplicada é candidata à próxima rodada do catálogo.
4. **Calendários provisórios.** Sem portaria conferida para os feriados do TJGO, `tjgo.yaml` é provisório e está marcado "a confirmar". `nacionais.yaml` cobre só 2026. Antes do piloto com autos reais, o gabinete substitui ambos pelos calendários oficiais. As exceções de réu preso no recesso do art. 798-A exigem conferência manual até serem incorporadas.
5. **Súmula 310 do STF** (intimação na sexta) **e prazos especiais** ficam para conferência manual, como informa o guia. Entram como regras de dados quando o gabinete confirmar o texto.

<a id="etapa-3"></a>

## Etapa 3 — Autenticação, papéis e auditoria

20 de outubro de 2026 · agente executor

### 1. O que foi feito

| Onde | Conteúdo |
| --- | --- |
| `src/lupa/acesso/senhas.py` | argon2id com parâmetros fixos (t=3, m=64 MiB, p=4, hash 32, sal 16; perfil RFC 9106 baixa memória), `precisa_rehash`, política (12+, fora das 10 mil mais comuns, sem o nome de usuário, sem repetição trivial; sem exigir especiais), senha temporária |
| `src/lupa/acesso/dados/senhas_comuns.txt` | 10 mil senhas mais comuns (ver decisão 12) |
| `src/lupa/acesso/mfa.py` | segredo TOTP de 160 bits, URI `otpauth://` para o QR, verificação com janela de ±1 passo e recusa de passo já usado (replay) |
| `src/lupa/acesso/sessoes.py` | sessão em tabela (token de 256 bits; o banco guarda o SHA-256), 8 h absolutas, 30 min de inatividade, cookie `HttpOnly`/`Secure`/`SameSite=Strict`, desafio do 2º passo |
| `src/lupa/acesso/papeis.py` | enum `Permissao`, `Escopo` e a matriz como dados (`MATRIZ`), `pode`/`tem_permissao` |
| `src/lupa/acesso/autorizacao.py` | dependências `usuario_autenticado`, `usuario_autenticado_permitindo_troca`, `exige_papel`, `exige_gabinete`, `exige_processo` (404 + evento de tentativa); define `lupa.papel` e `lupa.gabinete_id` |
| `src/lupa/acesso/servico.py` | casos de uso: login em dois passos, rate limit, logout, troca e reset de senha/MFA, criar/desativar/reativar usuário, criar gabinete, criar administrador |
| `src/lupa/acesso/rotas.py` | os 12 endpoints da tarefa 8 |
| `src/lupa/acesso/erros.py`, `instalacao.py` | recusas previstas com status HTTP; criação do usuário de conexão e do admin |
| `src/lupa/auditoria/eventos.py` | `AcaoAuditoria` (as 26 ações), `ResultadoEvento`, `NovoEvento` (só campos fixos), serialização canônica e hash |
| `src/lupa/auditoria/registrador.py` | `registrar` (trava da cadeia + hash encadeado) e `verificar_cadeia` |
| `src/lupa/auditoria/geoip.py` | `ResolvedorLocalizacao`, `ResolvedorMaxMind` (`.mmdb`), `ResolvedorNulo`, IP interno → "rede interna" |
| `src/lupa/auditoria/consulta.py`, `rotas.py` | filtros, cursor, exportação CSV/JSON, relatório de uso; `GET /auditoria`, `/exportar`, `/verificar`, `/relatorio-uso` |
| `src/lupa/api/banco.py`, `middleware.py`, `rotas/processos.py`, `app.py` | sessão de banco por requisição sob `lupa_app`, middleware de auditoria automática (`auditar_rota`), rota `GET /processos/{id}` |
| `src/lupa/migrations/esquema_v0002.py` + `versions/v0002_acesso_auditoria.py` | revisão 0002 escrita à mão (`down_revision = "0001"`) |
| `src/lupa/dominio/` (acréscimos) | `SessaoTabela`, `DesafioMfaTabela`, `FalhaLoginTabela`, `BloqueioLoginTabela`; `usuario.mfa_ultimo_passo`; `evento_auditoria.sequencia` e índices; `EventoAuditoria.sequencia`; `definir_papel` |
| `src/lupa/config.py` (acréscimos) | `db_usuario_app`, `db_senha_app`, `geoip_caminho`, `url_banco_aplicacao()` |
| `scripts/criar_admin.py`, `scripts/criar_usuario_banco.py` | scripts finos que chamam `lupa.acesso.instalacao` |
| `docs/sistema/auditoria.md`, seção no `README.md`, `.env.example` | documentação |
| `tests/acesso/`, `tests/auditoria/`, `tests/api/test_processos.py`, `tests/api/test_banco.py`, `tests/conftest.py` (acréscimos) | 77 testes novos + 1 de carga |

Migração 0002: tabelas `sessao`, `desafio_mfa`, `falha_login`, `bloqueio_login`; coluna
`usuario.mfa_ultimo_passo`; `evento_auditoria.sequencia` (numerada para linhas existentes),
`UNIQUE (gabinete_id, sequencia) NULLS NOT DISTINCT`, seis índices compostos
(`ocorrido_em`; `usuario_id|gabinete_id|processo_id|acao|ip` + `ocorrido_em`); triggers
`evento_auditoria_append_only` (UPDATE/DELETE) e `evento_auditoria_sem_truncate`; funções
`lupa_localizar_usuario` e `lupa_travar_cadeia` (SECURITY DEFINER); políticas
`<tabela>_administrador` e `evento_auditoria_global_insercao`; grants. O downgrade volta à 0001
(testado por `test_downgrade_base_remove_e_upgrade_head_recria`), e
`test_migracao_coincide_com_tabelas` continua com diferença vazia. A migração foi aplicada ao
banco do compose (`alembic current` → `0002 (head)`).

### 2. Os cinco pontos herdados da Etapa 1

1. **Login sob RLS.** Função `lupa_localizar_usuario(nome)` (SECURITY DEFINER, `search_path`
   fixo, EXECUTE só para `lupa_app`) devolve apenas `id`, `gabinete_id` e `papel`. O login chama
   a função, define `lupa.papel`/`lupa.gabinete_id` com o resultado e só então lê a linha
   completa do usuário sob a RLS normal. Sem contexto, `SELECT * FROM usuario` continua vazio.
   Sessões e desafios guardam `gabinete_id` e `papel`, então as requisições seguintes definem o
   contexto antes de ler o usuário. Teste:
   `test_login_sob_rls_localiza_usuario_pela_funcao_e_nao_lista_os_demais`.
2. **Administrador.** Nova variável `lupa.papel` (`definir_papel` em `dominio/sessao.py`) e
   política permissiva `<tabela>_administrador` em todas as tabelas com RLS, liberando leitura
   e escrita quando `lupa.papel = 'administrador'`. Acesso do admin a rota de conteúdo gera
   `admin_acesso_conteudo` na cadeia do gabinete do processo. Testes:
   `test_politica_do_administrador_libera_todos_os_gabinetes`,
   `test_acesso_de_admin_a_rota_de_conteudo_gera_admin_acesso_conteudo`.
3. **Eventos globais.** Leitura: pela política do administrador. Escrita: política
   `evento_auditoria_global_insercao` (`FOR INSERT WITH CHECK (gabinete_id IS NULL)`), para que
   a falha de login de usuário inexistente seja gravada sem contexto. A trava da cadeia é a
   função `lupa_travar_cadeia` (SECURITY DEFINER), então o registrador não precisa enxergar os
   eventos para encadear. Teste: `test_eventos_sem_gabinete_formam_a_cadeia_global`.
4. **Membership do papel.** `garantir_usuario_conexao` cria (ou atualiza a senha de) um papel
   `LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE INHERIT` e faz `GRANT lupa_app`.
   `scripts/criar_usuario_banco.py` lê `LUPA_DB_USUARIO_APP`/`LUPA_DB_SENHA_APP`;
   `Settings.url_banco_aplicacao()` troca as credenciais de `LUPA_DATABASE_URL` por essas, e a
   API usa essa URL. O dono das tabelas fica para migrações e scripts. O compose não mudou:
   as variáveis chegam pelo `env_file: .env` (documentadas em `.env.example` e no README). Em
   produção, o dono das tabelas precisa ser superusuário ou ter BYPASSRLS, porque as tabelas
   têm `FORCE ROW LEVEL SECURITY` e as funções SECURITY DEFINER rodam como ele. Testes:
   `test_usuario_de_conexao_nao_e_superusuario_e_assume_lupa_app`,
   `test_lupa_app_nao_altera_auditoria_mesmo_com_contexto_de_admin`,
   `test_scripts_de_instalacao`.
5. **Grants para tabelas novas.** A 0002 faz grant explícito nas quatro tabelas novas e
   `ALTER DEFAULT PRIVILEGES IN SCHEMA public` para tabelas e sequências futuras criadas pelo
   dono das migrações. Também revoga `UPDATE, DELETE, TRUNCATE` de `evento_auditoria` para
   `lupa_app`. Teste: `test_tabelas_novas_tem_grant_para_lupa_app`.

### 3. Decisões que o plano não previa

1. **O banco guarda o SHA-256 do token de sessão,** não o token. Uma cópia do banco não permite
   sequestrar sessões.
2. **Segundo passo do login:** tabela `desafio_mfa` (token de 256 bits, 5 minutos, uso único).
   A sessão só é criada depois do TOTP.
3. **QR code:** a API devolve o segredo em texto e a URI `otpauth://`; quem desenha o QR é a
   interface. Nenhuma biblioteca de QR estava autorizada. A revisão confirmou esse desenho para a API.
4. **Rate limit:**
   - As tabelas `falha_login` e `bloqueio_login` guardam o SHA-256 do nome digitado, não o
     nome, porque às vezes a pessoa digita a senha no campo de usuário. Pelo mesmo motivo, o
     evento de falha de usuário inexistente não registra o nome digitado.
   - Falhas de TOTP também contam.
   - A 5ª falha ainda responde 401 (resposta idêntica) e grava `login_bloqueado`. A partir da
     6ª tentativa a resposta é 429 por 15 minutos.
   - Usuário inexistente, inativo ou com senha errada recebem resposta idêntica, contam
     igualmente para o bloqueio e passam por um argon2 fictício para igualar o tempo.
5. **Cadeia de auditoria:**
   - A coluna `sequencia` foi acrescentada com unicidade `(gabinete_id, sequencia) NULLS NOT
     DISTINCT`.
   - `lupa_travar_cadeia` toma um `pg_advisory_xact_lock` da cadeia, porque com a cadeia vazia
     não há linha para travar, e faz o `SELECT ... FOR UPDATE` do último evento, como pedido.
   - O hash cobre `id`, `sequencia`, `ocorrido_em`, os identificadores, `acao`, objeto, `ip`,
     `localizacao`, `resultado` e as versões, em JSON ordenado.
   - A verificação aponta o primeiro evento com problema de `hash`, `encadeamento` ou
     `sequencia`.
6. **Tabelas de apoio sem RLS:** `sessao`, `desafio_mfa`, `falha_login` e `bloqueio_login` não
   têm `gabinete_id` próprio de tenant e só guardam hashes e ids, por isso ficaram sem RLS.
   `test_rls_ativa_em_todas_as_tabelas_com_gabinete` continua valendo.
7. **Recusas previstas confirmam a transação.** `RecusaAcessoError` e `HTTPException` confirmam
   a transação da requisição, para não perder o evento da recusa (falha de login, 404 de outro
   gabinete, criação negada). Qualquer outra exceção desfaz tudo.
8. **Troca de senha:** mantém a sessão que trocou e revoga as demais, conforme o critério de
   aceite. Reset, desativação e reset de MFA revogam todas as sessões do alvo.
9. **Troca de senha pendente:** só `/auth/trocar-senha` responde; até o logout devolve 403.
10. **Administrador único:**
    - A API não cria administrador. Só o script cria, e só se não houver outro.
    - A unicidade é garantida pela aplicação, não por constraint no banco, porque os testes
      semeiam vários administradores.
    - O admin também nasce com troca de senha obrigatória.
11. **Rota mínima `GET /processos/{id}`,** necessária para os critérios do 404 e do
    `admin_acesso_conteudo`. É a primeira rota marcada com `@auditar_rota(..., conteudo=True)`.
    O middleware lê a marca do endpoint e grava `processo_aberto`/`pagina_vista`/`busca` (e
    `admin_acesso_conteudo`) em transação própria depois da resposta.
12. **Lista de senhas comuns:** as 10.000 primeiras linhas do `common-passwords.txt.gz` do
    Django 6.0.5, já presente na máquina (licença BSD, lista de Royce Williams ordenada por
    frequência). Nada foi baixado.
13. **Consulta da auditoria:** ordenação decrescente (`ocorrido_em DESC, id DESC`), com cursor
    opaco. A exportação vai em ordem cronológica, com teto de 100 mil eventos.
14. **`geoip2` 5.3.0 traz `aiohttp` e `requests`** como dependências transitivas (cliente do web
    service da MaxMind). Só o leitor offline é usado.
15. **Teste de carga fora da suíte padrão:** `addopts` ganhou `-m 'not carga'`; rode com
    `pytest -m carga --no-cov`.
16. **Arquivos de outras etapas alterados (só acréscimos):**
    - Etapa 0: `config.py`, `api/app.py`, `api/middleware.py`.
    - Etapa 1: `dominio/tabelas.py`, `dominio/sessao.py`, `dominio/esquemas.py`
      (`EventoAuditoria.sequencia`, padrão 1).
    - `tests/conftest.py`.
    - Compartilhados: `pyproject.toml`, `requirements*.in`, `requirements*.txt`, `README.md`,
      `.env.example`.

### 4. Convivência com a Etapa 2 (registro obrigatório)

**Estado dos arquivos compartilhados quando cheguei:**
- `pyproject.toml` já tinha `pyyaml==6.0.2` e `types-PyYAML`, e `requirements.in` já tinha
  `pyyaml`.
- `requirements*.txt` tinham sido gerados no Windows: incluíam `tzdata` (via psycopg) e
  `colorama` (via pytest).

**O que fiz nesses arquivos:**
- `pyproject.toml` e `requirements.in`: reli cada um logo antes de editar e só acrescentei as
  três dependências, o marcador `carga` e o `-m 'not carga'`.
- Regenerei `requirements.txt` e `requirements-dev.txt` com o comando do cabeçalho
  (`pip-compile --allow-unsafe --generate-hashes --strip-extras`), num contêiner
  `python:3.12-slim` descartável.
- O pip-compile no Linux removeu `tzdata` e `colorama`. Reinseri os blocos originais, com os
  mesmos hashes, para manter a regra de só acrescentar. Fora isso, as únicas mudanças são as
  dependências novas e as transitivas delas.

**Incidente, precisa de conferência da Etapa 2.**
- O que aconteceu: para rodar `ruff format` e `ruff --fix`, copiei `src/lupa` e `tests` do
  contêiner de volta para o diretório do projeto, por volta das 19:59:07 e de novo às 19:59:44.
  O contêiner tinha a cópia de `src` da imagem construída por volta das 19:57.
- Efeito 1: arquivos da Etapa 2 alterados no host entre o build e essas cópias podem ter
  voltado à versão do build. Vi `src/lupa/validacoes/modelo.py` ser reescrito depois pela
  própria Etapa 2, às 20:00:16.
- Efeito 2: `ruff format` reformatou arquivos em `src/lupa/validacoes/` (`adaptador.py`,
  `apoio.py`, `__main__.py`, `criminal/*`) e possivelmente em `tests/validacoes/`. São mudanças
  só de formatação.
- Depois disso não copiei mais nada do contêiner para o host.
- Na execução final de `verificar.sh` os testes de validação passam (ver seção 7). Mesmo assim,
  peço que a Etapa 2 confira se alguma alteração dela entre 19:57 e 19:59 se perdeu.

Não toquei em `docs/sistema/validacoes.md` nem em `docs/exemplos/**`.

### 5. O que ficou de fora e por quê

- **Base GeoLite2 (pendência de Victor):** exige conta gratuita na MaxMind e aceite da licença. Sem a base, a localização aproximada por IP fica `desconhecida`. O README explica como obter e instalar a base. Os testes usam um leitor falso.
- **Rotas que ainda não existem:** upload, páginas, busca, chat, anotação, validação e chamada
  ao modelo pertencem a etapas futuras. As ações estão no enum, e o middleware e `auditar`
  estão prontos para elas.
- **Rate limit por IP** e confiança em `X-Forwarded-For`: não estavam pedidos. O README
  documenta o uso de `--proxy-headers` atrás de proxy.
- **Constraint de banco para o administrador único:** ver decisão 10.
- **Vault:** os segredos continuam no `.env`.
- **`docker-compose.yml`:** não mudou; as variáveis novas entram pelo `.env`. Para ativar o
  usuário sem superusuário no ambiente local, acrescente `LUPA_DB_USUARIO_APP` e
  `LUPA_DB_SENHA_APP` ao seu `.env`, rode `scripts/criar_usuario_banco.py` e depois
  `docker compose up -d api`.

### 6. Teste de carga

`docker compose exec api python -m pytest -m carga --no-cov -s`:

```
teste_carga  eventos=1000000 segundos_carga=67.2 mediana_ms=3.0 maximo_ms=13.3
1 passed, 211 deselected in 63.41s
```

- Carga: 1 milhão de eventos por `COPY`, distribuídos em 40 gabinetes e 1.000 usuários ao longo
  de um ano, num banco próprio.
- Consulta: filtrada por usuário e por intervalo de 90 dias, sob RLS de desembargador, página de
  50. Mediana de 3,0 ms e máximo de 13,3 ms em 10 execuções (meta: < 200 ms).
- Tempo total: cerca de 65 s, por isso o teste é marcado `integracao` e `carga` e fica fora da
  suíte padrão.

### 7. Lint, tipagem e testes

A imagem foi reconstruída para incluir as dependências novas (`docker compose up -d --build
--wait`).

```
$ docker compose exec api bash scripts/verificar.sh
== ruff check ==            All checks passed!
== ruff format --check ==   87 files already formatted
== mypy --strict ==         Success: no issues found in 87 source files
== pytest ==                210 passed, 1 skipped, 1 deselected
                            Required test coverage of 90% reached. Total coverage: 98.68%
```

Durante a verificação, `test_cinco_falhas_bloqueiam...` falhou uma vez em quatro execuções.
A causa: o helper dos testes ordenava os eventos por `ocorrido_em`, que vem do relógio da
aplicação, e o relógio da VM do Docker pode recuar. O helper passou a ordenar por `sequencia`,
que é a ordem verdadeira da cadeia. Depois disso, 6 execuções seguidas da suíte passaram.

Cobertura dos pacotes da etapa:
- `acesso`: 97–100% por módulo.
- `auditoria`: 100%.
- `api`: 97–100%.

### 8. Critérios de aceite

| Critério | Status | Evidência |
| --- | --- | --- |
| Senha certa + TOTP errado não cria sessão | ok | `test_login_com_senha_certa_e_totp_errado_nao_cria_sessao` |
| TOTP reutilizado na janela é rejeitado | ok | `test_codigo_totp_reutilizado_dentro_da_janela_e_rejeitado`, `test_totp_recusa_codigo_reutilizado` |
| 5 falhas bloqueiam e geram `login_bloqueado` | ok | `test_cinco_falhas_bloqueiam_e_geram_evento_login_bloqueado`, `test_bloqueio_expira_depois_de_quinze_minutos` |
| Assessor de A recebe 404 (não 403) no processo de B, tentativa registrada | ok | `test_assessor_do_gabinete_a_recebe_404_no_processo_do_gabinete_b_e_tentativa_e_registrada` |
| Desembargador não cria assessor em outro gabinete | ok | `test_desembargador_nao_consegue_criar_assessor_em_outro_gabinete` |
| `troca_senha_obrigatoria` só acessa a rota de troca | ok | `test_usuario_com_troca_senha_obrigatoria_so_acessa_rota_de_troca` |
| Troca de senha revoga as demais sessões | ok | `test_troca_de_senha_revoga_as_demais_sessoes` |
| UPDATE/DELETE em `evento_auditoria` falha no banco | ok | `test_update_ou_delete_em_evento_auditoria_falha_no_banco` (UPDATE, DELETE, TRUNCATE), `test_papel_da_aplicacao_nao_tem_privilegio_de_update` |
| Alterar evento no meio da cadeia → `/auditoria/verificar` aponta aquele evento | ok | `test_alterar_evento_no_meio_da_cadeia_faz_verificar_apontar_aquele_evento` |
| Registros concorrentes no mesmo gabinete → cadeia válida | ok | `test_dois_registros_concorrentes_no_mesmo_gabinete_produzem_cadeia_valida` (4 threads × 10) |
| Nenhum evento contém chave de `CAMPOS_PROIBIDOS` | ok | `test_nenhum_evento_contem_campo_proibido_nem_segredo` (importa `CAMPOS_PROIBIDOS` de `lupa.logging`, varre todos os eventos e também os valores) |
| Carga: 1 milhão de eventos, consulta por usuário e intervalo < 200 ms | ok | `test_um_milhao_de_eventos_consulta_por_usuario_e_intervalo_abaixo_de_200ms`: mediana 3,0 ms |
| Admin em rota de conteúdo gera `admin_acesso_conteudo` além do evento normal | ok | `test_acesso_de_admin_a_rota_de_conteudo_gera_admin_acesso_conteudo` |
| `docs/sistema/auditoria.md` em linguagem simples | ok | `docs/sistema/auditoria.md` |
| Cobertura ≥ 90% e `verificar.sh` passa | ok | seção 7 |

### Revisão 3

**Pendências para Victor**

- **Variáveis de produção.** `LUPA_DB_USUARIO_APP`, `LUPA_DB_SENHA_APP`, `LUPA_ADMIN_USUARIO` e `LUPA_ADMIN_SENHA` precisam de valores reais no ambiente do piloto; no dev já estão configuradas com valores fictícios.
- **Dependências transitivas.** `geoip2` trouxe `aiohttp` e `requests`. Aceitável, mas aumenta a superfície; vale reavaliar na Etapa 7 se a resolução por arquivo `.mmdb` pode usar só `maxminddb`.

**Observações menores**

- Rota `GET /processos/{id}` criada como mínimo para os testes de 404 e de acesso do admin; será substituída pelas rotas reais da Etapa 6.
- `requirements*.txt` regenerados no Linux; o executor reinseriu `tzdata` e `colorama` para manter instalação no Windows. Conferir na Etapa 4A se o `pip-compile` passa a rodar sempre no contêiner, para evitar esse vaivém.

<a id="etapa-4a"></a>

## Etapa 4A — Fundações da ingestão

<a id="etapa-4a-1"></a>

### 4A.1 — Adaptador validações ↔ domínio

**Pendência confirmada na revisão 4A.1**

A restrição de dependências deixou o `.venv` do host sem `pyotp`, `argon2-cffi` e `geoip2`, adicionados na Etapa 3. O `verificar.sh` só voltaria a passar inteiro no host após a instalação pela Etapa 3 ou a reinstalação pelo revisor. No contêiner, o rebuild já bastava.

<a id="etapa-4a-2"></a>

### 4A.2 — Esquemas da ingestão

- Preencher `DiagnosticoArquivo` com o cenário real é da 4C.1; aqui só entidade, tabela e
  repositório.
- Estados de `em_extracao` em diante existem e entram na matriz, mas nenhum código da 4A os usa.

<a id="etapa-4a-3"></a>

### 4A.3 — Fila e worker base

- Retentativa automática de jobs `falho` (falha por limite tende a repetir); a volta é manual
  (`falho -> recebido`).
- Morte por `SIGKILL` real: simulada por uma `BaseException` lançada depois do lote 1 (não é
  capturada como `Exception`, então nada é finalizado, como num kill).

<a id="etapa-4a-4"></a>

### 4A.4 — Sandbox de parsing

- Isolamento de rede no nível do kernel para o filho (ele compartilha a rede interna do worker,
  sem credenciais). Documentado em `docs/sistema/ingestao.md`; um contêiner de parser sem rede fica para
  quando a decifragem por processo (fase 2, `requisitos-v1.md` §6) exigir worker separado.
- seccomp e namespaces (exigiriam privilégios no contêiner).

<a id="etapa-4a-5"></a>

### 4A.5 — Cliente de object storage

- Criptografia do lado do servidor por processo (fase 2 dos requisitos).

<a id="etapa-4a-6"></a>

### 4A.6 — Recepção e lacre

- `processo.status` não muda para `em_ingestao` (fica para quando a extração existir).
- Antivírus e cifragem antes do parser (fase 2).

<a id="etapa-4a-7"></a>

### 4A.7 — Inventário de zip

- ZIP dentro de ZIP não é aberto (a entrada não é PDF, logo `tipo_invalido`).

<a id="etapa-4a-8"></a>

### 4A.8 — Quarentena e falhas

- A tela de quarentena (vai ler `motivo_quarentena` e `DESCRICOES`).

<a id="etapa-4a-9"></a>

### 4A.9 — Observabilidade da pipeline

- Servidor Prometheus e painel Grafana no compose: o painel mínimo é o endpoint de exposição.

<a id="etapa-4a-10"></a>

### 4A.10 — Ponta a ponta da fundação

- `scripts/verificar.ps1` não recebeu o passo extra (o fluxo oficial é no contêiner).

### Revisão 4A.1

**Observações**

- O executor relatou edições que "não ficaram gravadas" durante o trabalho e precisaram ser reaplicadas. O estado final foi conferido aqui. Causa provável: sincronização do OneDrive sobre a pasta do projeto enquanto dois agentes escrevem. Vale considerar mover o repositório para fora do OneDrive antes das etapas com muitos arquivos (4B gera PDFs grandes).

<a id="etapa-4b"></a>

## Etapa 4B — Autos sintéticos

<a id="etapa-4b-1"></a>

### 4B.1 — Esquema do gabarito

- Nada do escopo.

<a id="etapa-4b-2"></a>

### 4B.2 — Textos por tipo de peça

- Múltiplos réus e concurso de crimes (o gabarito suporta; o roteiro gera um réu e um crime).

<a id="etapa-4b-3"></a>

### 4B.3 — Renderização nativa

- Leiaute em duas colunas (fica para o teste de ordem de leitura da 4C.5).

<a id="etapa-4b-4"></a>

### 4B.4 — Renderização digitalizada

- **CER de OCR de referência por nível**: não há Tesseract no host nem na imagem (`which tesseract`
  vazio nos dois), e instalar pacote de sistema muda o `Dockerfile`, que não é desta etapa. O
  harness (4B.10) já mede CER por nível de degradação; a meta e a medição ficam para a 4C.6, que
  instala o Tesseract.

<a id="etapa-4b-5"></a>

### 4B.5 — Páginas híbridas, vazias e capas

- Tabela como imagem (a assinatura cobre o caso de bloco localizado em imagem).

<a id="etapa-4b-8"></a>

### 4B.8 — Injeções por vetor

- Unicode de direção (RTL) e cadeia entre documentos (vetores de risco baixo na tabela).

<a id="etapa-4b-9"></a>

### 4B.9 — Processos de referência

- Geração dentro do contêiner (rodou no host para gravar direto na pasta do host sem copiar do
  contêiner, como pedem as regras).

<a id="etapa-4b-10"></a>

### 4B.10 — Harness de medição

- Matriz de confusão de tipo de página (fica para a 4C.4, que precisa dela).

### Revisão 4B

**Pendência para Victor**

A pasta `.sinteticos/` tem 4,7 GB e está dentro do OneDrive, então vai sincronizar e consumir cota. Duas opções: excluir a pasta da sincronização nas configurações do OneDrive, ou definir `LUPA_SINTETICOS_DIR` para um caminho fora do OneDrive e regerar com `python scripts/gerar_autos.py referencia` (12 minutos). Sem decisão, fica como está.

<a id="etapa-4c"></a>

## Etapa 4C — Diagnóstico e páginas

<a id="etapa-4c-1"></a>

### 4C.1 — Diagnóstico do contêiner

#### O que foi feito

- `src/lupa/ingestao/diagnostico.py`: funções puras que classificam o arquivo em `zip_por_peca`, `pdf_com_bookmarks_e_indice`, `pdf_com_bookmarks`, `pdf_com_indice` ou `pdf_liso` a partir do manifesto (ZIP) ou da inspeção do PDF (sumário e texto das primeiras páginas, lidos no sandbox por `parser_pdf.inspecionar`).
- `parser_pdf.inspecionar` devolve também `toc`, `paginas_indice` e `indice`.
- O worker grava o `DiagnosticoArquivo` (`repositorio.salvar_diagnostico`) ao sair de `validado`.
- Rota de leitura auditada: `GET /processos/{id}/arquivos/{arquivo_id}/diagnostico` (`processo_aberto`, conteúdo; 404 para arquivo de outro processo ou sem diagnóstico).
- Migração 0004: CHECK de `cenario` aceita o novo valor.

#### Decisões não previstas

- **Novo valor `CenarioArquivo.PDF_COM_BOOKMARKS_E_INDICE`**: o gabarito 4B espera `pdf_com_bookmarks_e_indice` para o cenário com índice; sem o valor, o critério 30/30 era impossível.
- **ZIP com uma só entrada** é diagnosticado pelo PDF de dentro (sinal `zip_com_um_pdf`).
- **Correção em arquivo da 4A** (`parser_pdf.py`): página sem stream de conteúdo (folha em branco, presente em todos os processos de referência) fazia o PyMuPDF 1.25.1 lançar `AssertionError` em `read_contents()` e o PDF ia para quarentena como `corrompido`. Agora a página sem conteúdo é pulada. Teste: `test_pdf_com_pagina_sem_conteudo_nao_e_corrompido`.

#### Ficou de fora

- Diagnóstico do ZIP custa ~0,8 s por entrada (um filho do sandbox por PDF). Aceitável no piloto; agrupar entradas num filho fica para 4F.8 (cache/reprocessamento).

#### Comandos e saída

```
docker compose run --rm api python scripts/medir_extracao.py diagnostico
→ "acertos": 30, "total": 30
docker compose exec api bash scripts/verificar.sh   (ver 4C.10)
```

#### Critério

| Critério | Evidência |
|---|---|
| Três cenários dos dez processos diagnosticados corretamente | **30/30** (`diagnostico_esperado` do gabarito como referência) |
| Diagnóstico visível no processo | rota GET auditada; `test_rotas_de_diagnostico_e_relatorio_sao_auditadas_e_isoladas` |

Tempo de diagnóstico: PDF único 1,1 a 2,5 s (até 5.000 páginas); ZIP 45 s (51 entradas) a 725 s (878 entradas).

<a id="etapa-4c-2"></a>

### 4C.2 — Bookmarks e índice

#### O que foi feito

- `diagnostico.ler_indice`: lê as primeiras páginas consecutivas em que a maioria das linhas segue `Movimentação N - dd/mm/aaaa - título - fls. P` (também `evento`, `mov.`, `seq.`, `pág.`); a primeira precisa de duas linhas reconhecidas.
- `fronteiras_do_indice`, `fronteiras_do_sumario` (bookmarks de nível 1 com destino válido; data tirada do título) e `fronteiras_do_manifesto` (uma por entrada do ZIP, com `pagina_continua`).
- Gravadas em `diagnostico_arquivo.fronteiras_origem` (`{peca, titulo, data, arquivo, pagina, fonte}`).

#### Decisões não previstas

- Guardamos as duas fontes (índice e bookmarks) quando existem; a Etapa 4E confere uma contra a outra e contra o conteúdo.
- A página registrada é a física no arquivo (já com as páginas de índice); o deslocamento sai de `sinais.paginas_indice`.

#### Comandos e saída

`scripts/medir_extracao.py diagnostico` (campo `fronteiras_indice`, `fronteiras_bookmark`, `paginas_indice`, `fronteiras_manifesto`).

#### Critério

| Processo | Peças | Índice: páginas iguais | Índice: datas iguais | Bookmarks iguais | Páginas de índice | ZIP: inícios iguais |
|---|---|---|---|---|---|---|
| semente_01 | 51 | 51 | 51 | 51 | 2/2 | 51 |
| semente_02 | 84 | 84 | 84 | 84 | 3/3 | 84 |
| semente_03 | 79 | 79 | 79 | 79 | 2/2 | 79 |
| semente_04 | 120 | 120 | 120 | 120 | 3/3 | 120 |
| semente_05 | 172 | 172 | 172 | 172 | 5/5 | 172 |
| semente_06 | 240 | 240 | 240 | 240 | 6/6 | 240 |
| semente_07 | 286 | 286 | 286 | 286 | 8/8 | 286 |
| semente_08 | 384 | 384 | 384 | 384 | 10/10 | 384 |
| semente_09 | 531 | 531 | 531 | 531 | 14/14 | 531 |
| semente_10 | 878 | 878 | 878 | 878 | 22/22 | 878 |

**2.825/2.825 fronteiras** batem com `pecas[].pagina_inicial + deslocamento` no cenário `pdf_indice`. Testes: `test_fronteiras_do_indice_batem_com_as_pecas_do_gabarito`, `test_zip_por_peca_tem_uma_fronteira_por_entrada_em_numeracao_continua`.

<a id="etapa-4c-3"></a>

### 4C.3 — Sinais por página

#### O que foi feito

- `src/lupa/ingestao/sinais.py` (`medir_sinais`), executado no filho do sandbox (`extrator_paginas`): `caracteres_imprimiveis`, `caracteres_substituicao` (U+FFFD), `caracteres_invisiveis` (fonte < 4 pt, cor branca, fora da página), `cobertura_texto`, `area_imagem`, `area_imagem_opaca`, `imagens`, `palavras`, `fragmentacao`, `rotacao` declarada, `tinta` (pixels < 160 num pixmap cinza de 24 DPI) e `visualmente_vazia` (tinta < 0,05%).
- Gravados em `pagina.sinais` (JSONB, migração 0004).

#### Decisões não previstas

- **Área de imagem opaca separada da total**: carimbos (PNG com transparência) aparecem em 1.290 páginas nativas dos processos de referência com área até 2,7%, enquanto a assinatura digitalizada das híbridas ocupa 2,0 a 4,7%. Só a máscara de transparência separa os dois; imagem opaca é tratada como conteúdo digitalizado.
- **Texto invisível** (fora da página exige `clip=INFINITE_RECT` e sem `TEXT_MEDIABOX_CLIP`) entrou como sinal porque é o que permite levar a página de camada manipulada ao OCR (4C.7).

#### Comandos

`pytest tests/ingestao/test_paginas.py` (sinais reproduzíveis, carimbo vs. imagem opaca, invisíveis, rotação, página vazia).

#### Critério

| Critério | Evidência |
|---|---|
| Sinais gravados por página | `pagina.sinais` preenchido em todas as páginas (`test_pdf_sintetico_com_indice_vai_a_concluido...`) |
| Reproduzíveis | `test_rotacao_declarada_e_sinais_reproduziveis`; valores arredondados a 4 casas |

<a id="etapa-4c-4"></a>

### 4C.4 — Roteador de páginas

#### O que foi feito

- `src/lupa/ingestao/roteador.py`: `rotear(sinais) -> TipoPagina | None`, função pura; None é abstenção (OCR integral + texto nativo guardado + fusão).
- Limiares em `src/lupa/ingestao/dados/roteador.yaml` (`versao: "1"`, `fonte` descrita). Regras: `vazia` (sem tinta, sem imagem opaca, ≤ 3 caracteres); `ocr` (imagem opaca ≥ 85% e ≤ 20 caracteres); `nativa` (imagem opaca ≤ 0,5%, ≥ 20 caracteres, fragmentação ≤ 0,5, U+FFFD ≤ 2%, nenhum caractere invisível); o resto se abstém.

#### Decisões não previstas

- **Capa mapeada para `nativa`**, não `vazia`: o gabarito 4B marca a capa como `TipoPagina.NATIVA` (tem 400+ caracteres de camada de texto); rotear como vazia descartaria esse texto.
- **Digitalização em branco não é `vazia`**: na primeira calibração 53 páginas digitalizadas de contraste baixo saíram com tinta < limiar; agora `vazia` exige ausência de imagem opaca e a página vai ao OCR (que devolve `vazia` se não ler nada).

#### Comandos e saída

```
docker compose run --rm api python scripts/medir_extracao.py roteador
```

#### Matriz de confusão (dez processos, cenário `pdf_liso`, 15.647 folhas)

| Gabarito \ Roteador | nativa | ocr | vazia | abstenção | Total |
|---|---|---|---|---|---|
| nativa | **10.708** | 0 | 0 | 0 | 10.708 |
| capa | **10** | 0 | 0 | 0 | 10 |
| digitalizada | 0 | **3.426** | 0 | 0 | 3.426 |
| hibrida_corpo | 0 | 0 | 0 | **1.190** | 1.190 |
| hibrida_assinatura | 0 | 0 | 0 | **83** | 83 |
| vazia | 0 | 0 | **230** | 0 | 230 |

Corretos pelo mapeamento (nativa→nativa; digitalizada→ocr; híbrida→ocr ou abstenção; vazia→vazia; capa→nativa): **15.647/15.647**.

#### Critério

| Critério | Evidência |
|---|---|
| Matriz nos dez processos | tabela acima |
| Falso negativo perigoso (digitalizada ou híbrida roteada nativa) < 1% | **0 de 4.699 (0,00%)** |

Limitação: os processos de referência não têm imagens opacas decorativas (logotipo em JPEG); num PDF real elas levam a página nativa à abstenção. Custo: OCR a mais, nunca conteúdo perdido. A calibração com o Projudi (4F.10) mede isso.

<a id="etapa-4c-5"></a>

### 4C.5 — Texto nativo com coordenadas

#### O que foi feito

- `src/lupa/ingestao/texto_nativo.py`: blocos e linhas do PyMuPDF com caixas em pontos PDF (origem superior esquerda), ordem de leitura por corte XY com detecção de colunas (faixas consecutivas com mais de uma coluna são lidas coluna a coluna), linhas não horizontais (marca d'água) no fim. Texto = linhas terminadas por `\n`, como `get_text()`; cada bloco e linha guarda `inicio`/`fim` no texto.
- `hash_texto` = sha256 do texto (`calcular_hash`), preenchido pelo repositório na gravação.

#### Decisões não previstas

- A página com injeção `texto_branco` tem a linha oculta escrita por último no arquivo, mas posicionada acima do rodapé: a ordem de leitura a põe no lugar físico; o conjunto de linhas é igual ao `texto_camada`.

#### Comandos

`scripts/medir_extracao.py roteador` (campo `texto_nativo`); `pytest tests/ingestao/test_paginas.py`.

#### Critério

| Critério | Evidência |
|---|---|
| Texto nativo das páginas nativas bate com `texto_camada` | **10.718/10.718** iguais byte a byte (nativas + capas dos dez processos) |
| Offsets reproduzíveis | `test_texto_nativo_igual_a_camada_do_gabarito_com_offsets` (duas extrações iguais; offsets de linha conferidos) |
| Ordem de leitura em duas colunas | `test_duas_colunas_sao_lidas_coluna_por_coluna` (título, coluna esquerda, coluna direita, rodapé, com a coluna direita escrita antes no arquivo) |

<a id="etapa-4c-6"></a>

### 4C.6 — OCR

#### O que foi feito

- `Dockerfile` (imagem de runtime): `tesseract-ocr=5.5.0-1+b1`, `tesseract-ocr-por`, `-osd`, `-eng` `=1:4.1.0-2` (Debian trixie); o build confere `por.traineddata` sha256 `c4932b937207a9514b7514d518b931a99938c02a28a5a5a553f8599ed58b7deb`.
- `src/lupa/ingestao/ocr.py`: chama o binário (sem dependência Python nova) dentro do filho do sandbox; imagem PNG cinza por stdin, `tsv` por stdout, `OMP_THREAD_LIMIT=1`, tempo máximo de 90 s. Raster de 300 DPI; `--psm 0` (OSD) no mesmo raster; confiança ≥ 2 → rasteriza de novo girado. Caixas em pixels → pontos pela inversa da matriz de rasterização (inclui rotação e origem do recorte), registrada em `extracao.ocr.matriz_pixel_para_ponto`.
- Falha do Tesseract (`OcrIndisponivelError`) deixa a página sem resultado (job `parcial`).

#### Decisões não previstas

- OSD a 150 DPI dava confiança 1,9 numa página deitada (abaixo do limiar); passou a usar o raster de 300 DPI, sem custo extra de rasterização quando a página está de pé.
- `.sinteticos` entrou no `.dockerignore` (4,7 GB no contexto de build) e é montado só leitura no `api`.

#### Comandos e saída

```
docker compose run --rm api python scripts/medir_extracao.py ocr --por-nivel 6
```
Amostra estratificada: 6 páginas digitalizadas por nível em cada um dos dez processos (180 páginas, semente 20261020), OCR completo (OSD + TSV), CER contra `paginas[].texto` com espaços normalizados.

| Nível | Páginas | Caracteres | CER | Datas no gabarito | Encontradas literalmente | Taxa | s/página (1 filho) |
|---|---|---|---|---|---|---|---|
| leve (300 DPI) | 60 | 134.742 | **1,41%** | 317 | 298 | **94,0%** | 2,7 |
| media (200 DPI) | 60 | 146.351 | **2,80%** | 345 | 313 | **90,7%** | 3,5 |
| forte (150 DPI, contraste baixo) | 60 | 138.153 | **10,28%** | 359 | 291 | **81,1%** | 3,4 |

Medição completa (todas as páginas OCR dos dez processos) no [relatório 4C.10](#etapa-4c-10).

#### Metas (definidas a partir da medição; fecha a pendência 4B.4)

| Nível | CER máximo | Datas literais mínimas |
|---|---|---|
| leve | 3% | 90% |
| media | 5% | 85% |
| forte | 15% | 75% |

As metas cumprem-se na amostra. Datas não reconhecidas no nível forte são o risco relevante: a extração de fatos (4F.4) só aceita data que exista literalmente na página, então uma data mal lida vira fato ausente (vai ao assessor), não fato errado. A [medição posterior da 4F.9](#etapa-4f-9) registra as duas exceções observadas.

#### Critério

| Critério | Evidência |
|---|---|
| Tesseract por-BR em subprocesso dentro do sandbox | `extrator_paginas` → `ocr.executar_tesseract`; teste `test_lotes_reais_rodam_em_processos_filhos` e worker |
| Rotação detectada e corrigida | `test_pagina_deitada_tem_orientacao_detectada_e_corrigida` (texto a 90°, data lida, caixa sobre a palavra nativa) |
| Caixas raster → pontos com transformação registrada | `test_ocr_le_texto_e_datas_com_caixas_sobre_as_palavras_nativas`, `test_rasterizacao_registra_a_transformacao_de_volta` |
| CER por nível dentro da meta | tabela acima |

<a id="etapa-4c-7"></a>

### 4C.7 — Páginas híbridas

#### O que foi feito

- Abstenção do roteador (híbridas, nativas com imagem opaca, texto invisível, texto ilegível): o extrator guarda `texto_nativo` e `texto_ocr` e grava em `texto` a fusão (`hibridas.fundir`): toda linha nativa horizontal entra; linha do OCR coberta em ≥ 50% por linhas nativas é descartada (dedup geométrico); ordem por topo e esquerda.
- `hibridas.comparar`: para cada linha nativa com ≥ 8 caracteres, junta as palavras do OCR cujo centro cai na caixa da linha (folga de 2 pt); similaridade < 0,5 → linha divergente → `FlagPagina.TEXTO_DIVERGENTE` (novo valor do enum) e caixa em `extracao.divergencia.trechos`. A distância somada é o CER estimado da página.

#### Decisões não previstas

- Linhas não horizontais do nativo (marca d'água) ficam fora do texto fundido e fora da comparação; continuam em `texto_nativo`. Texto oculto girado fica para a 4D.1.
- Texto fora da página não entra no texto nativo (o PyMuPDF recorta), mas o sinal `caracteres_invisiveis` leva a página à abstenção; a marcação dele é da 4D.1.

#### Comandos

`pytest tests/ingestao/test_hibridas.py`.

#### Critério

| Critério | Evidência |
|---|---|
| Nativo e OCR guardados; fusão sem duplicar | `test_fusao_nao_duplica_o_que_as_duas_camadas_leram`; colunas `texto_nativo`/`texto_ocr` |
| Camada de texto manipulada gera a flag | `test_camada_de_texto_manipulada_gera_texto_divergente[texto_branco]`: página com instrução em branco, 1 pt → rota `abstencao`, flag `texto_divergente`; o mesmo no fluxo completo do worker (`test_pdf_sintetico_com_indice_vai_a_concluido...`) e na página 25 de `.sinteticos/injecao/injecao_texto_branco` (mesmo gerador) |
| Híbrida limpa não diverge | `test_pagina_hibrida_limpa_nao_diverge`; nas 1.273 híbridas dos dez processos, ver flags no [relatório 4C.10](#etapa-4c-10) |

<a id="etapa-4c-8"></a>

### 4C.8 — Paralelismo e desempenho

#### O que foi feito

- `src/lupa/ingestao/extracao.py`: `planejar` divide as fontes (PDF ou entradas do ZIP) em lotes de páginas consecutivas; cada lote roda num processo filho do sandbox (`extrator_paginas`), que abre o seu próprio documento. No pai, um `ThreadPoolExecutor` só espera os filhos (nenhum objeto PyMuPDF em thread). Resultados chegam na ordem de término e são gravados na hora.
- Tetos: lotes por job e lotes por gabinete (`LimitadorGabinete`, semáforo por gabinete compartilhado no processo worker). Configuração: `LUPA_EXTRACAO_PAGINAS_POR_LOTE=8`, `LUPA_EXTRACAO_LOTES_POR_JOB=4`, `LUPA_EXTRACAO_LOTES_POR_GABINETE=4`.
- **Justiça entre jobs: round-robin por fatias.** Depois de `LUPA_EXTRACAO_FATIA_PAGINAS=400` páginas o job grava o progresso, solta o lease sem contar tentativa (`repositorio.ceder_vez`) e volta ao fim da fila; o próximo job da fila (de qualquer gabinete) é atendido antes da fatia seguinte.

#### Decisões não previstas

- Round-robin em vez de fila com prioridade: não exige mudar o RQ nem saber o tamanho do job ao enfileirar, e o estado do job continua só no banco.
- O semáforo por gabinete vale por processo worker; com várias réplicas o teto passa a ser por réplica (registrado em `docs/sistema/ingestao.md`). Um semáforo no Redis fica para quando houver mais de um worker.
- O varredor também recupera jobs `validado`/`em_extracao` com lease vencido, e os que cederam a vez e ficaram 10 min sem heartbeat (mensagem perdida).

#### Comandos e saída

```
docker compose run --rm api python scripts/medir_extracao.py tempo
```
PDFs montados das folhas dos processos de referência; paralelismo padrão (4 lotes de 8 páginas), 12 CPUs disponíveis ao Docker.

| Tipo | Páginas | Tempo de parede | Por mil páginas |
|---|---|---|---|
| nativo | 1.000 | 39,5 s | **39,5 s** |
| digitalizado (OCR + OSD a 300 DPI) | 200 | 176,4 s | **881,9 s** |

#### Critério

| Critério | Evidência |
|---|---|
| Tempo por mil páginas nativo e digitalizado registrado | tabela acima |
| Um PDF enorme não ocupa toda a capacidade | `test_job_grande_cede_a_vez_e_job_pequeno_de_outro_gabinete_termina_antes` (20 páginas em fatias de 4; o job de 2 páginas de outro gabinete, enfileirado depois, conclui primeiro; `tentativas` fica 1) e `test_paralelismo_respeita_o_teto_do_gabinete` (pico de lotes simultâneos = teto) |

<a id="etapa-4c-9"></a>

### 4C.9 — Gravação de páginas

#### O que foi feito

- `repositorio.gravar_paginas`: upsert em `pagina` por `(arquivo_id, numero)` com o fencing token conferido; grava `tipo`, `texto`, `hash_texto`, `flags`, `sinais`, `coordenadas` (blocos/linhas com caixas e offsets), `extracao` (rota, versão do roteador, tempo, OCR, divergência), `texto_nativo`, `texto_ocr`, `versao_extrator`, `origem_arquivo`, `pagina_origem`.
- Idempotência: antes de cada execução, `paginas_prontas(arquivo, VERSAO_EXTRATOR)`; páginas já gravadas na versão corrente não são reextraídas. Mudar `extrator_paginas.VERSAO_EXTRATOR` (hoje `4c.1`) refaz todas, no mesmo id de linha.
- Estados: `validado → em_extracao → concluido | parcial | falho`; relatório gravado no job.
- **Item 2 da revisão 4A**: retry por motivo (`tempo_esgotado` e `erro_parser` voltam a `recebido` até 2 vezes, `LUPA_MAX_RETENTATIVAS`; `limite_memoria` e `limite_cpu` nunca; lotes falhos de validação são apagados para a nova tentativa) e `processo.status` (`em_ingestao` ao entrar na extração, `pronto` quando nenhum job está em andamento e algum terminou `concluido`/`parcial`).

#### Decisões não previstas

- A chave de idempotência é `(arquivo_id, versão)`; como o arquivo é único por `(processo, sha256)`, equivale a `(sha256, versão)` dentro do processo. Reaproveitar páginas do mesmo sha256 em outro processo é cache da 4F.8.
- `concluido` é final na máquina de estados; reprocessar um job concluído com nova versão exige reabrir o job (feito no teste por SQL). O gatilho de reprocessamento por versão é da 4F.8.
- A fixture `deps` dos testes da 4A passou a `extrair=False, max_retentativas=0` (comportamento da fundação); os testes 4C usam `deps_extracao`. Arquivo de outra etapa alterado: `tests/ingestao/conftest.py`, e o ponta a ponta (`test_ponta_a_ponta.py`) agora vai até `concluido`.

#### Comandos

`pytest tests/ingestao/test_worker_extracao.py`.

#### Critério

| Critério | Evidência |
|---|---|
| Página gravada com tipo, texto, hash, coordenadas, sinais e flags | `test_pdf_sintetico_com_indice_vai_a_concluido...` |
| Reprocessar não duplica | `test_reprocessar_nao_duplica_e_nova_versao_do_extrator_refaz`: segunda execução não chama nenhum filho; ids e hashes iguais |
| Versão nova reprocessa | mesmo teste: todas as páginas refeitas, `versao_extrator` novo, mesmas linhas (5) |
| `parcial` com páginas faltando | `test_lote_que_falha_deixa_job_parcial_com_paginas_faltando` |
| Retry por motivo | `test_falha_retentavel_volta_a_recebido_duas_vezes_e_depois_falha`, `test_falha_por_memoria_nunca_e_retentada` |
| `processo.status` | `pronto` verificado nos testes de conclusão e parcial |

<a id="etapa-4c-10"></a>

### 4C.10 — Relatório de qualidade por arquivo

#### O que foi feito

- `src/lupa/ingestao/qualidade.py`: `relatorio_qualidade` (páginas por tipo e rota, abstidas, faltando com lista e motivo, flags, CER estimado onde há nativo e OCR da mesma página, confiança média do OCR, rotações corrigidas, tempos de parede, soma por página e por mil páginas) e `para_saida_pipeline` (formato de `lupa.sinteticos.saida_pipeline`, só páginas).
- Gravado em `job_ingestao.relatorio` ao fim da extração (parcial entre fatias); exposto em `GET /processos/{id}/arquivos/{arquivo_id}/relatorio` (auditada como `processo_aberto`, sem conteúdo).
- `scripts/medir_extracao.py extrair <processo>` roda a mesma pipeline (sandbox, lotes paralelos, relatório) sem banco e grava `saida.json`, medido por `scripts/medir.py`.
- Itens herdados: `scripts/verificar.ps1` ganhou o passo ponta a ponta; avisos `DeprecationWarning` do swig/pymupdf (e `utcnow` do botocore) filtrados no `pyproject.toml`.

#### Decisões não previstas

- Os relatórios dos dez processos foram gerados pelo script (mesmas funções do worker) e não pelo upload no MinIO, para não carregar 1,9 GB no storage de desenvolvimento; o caminho com banco é coberto por `test_pdf_sintetico_com_indice_vai_a_concluido...` e pelo ponta a ponta.
- Paralelismo das medições: 8 lotes de 8 páginas (12 CPUs). O tempo com o padrão de produção (4 lotes) está no [relatório 4C.8](#etapa-4c-8).
- Só o cenário `pdf_liso` foi extraído por completo (as páginas são as mesmas nos três cenários; o diagnóstico dos três está em [4C.1](#etapa-4c-1)).

#### Comandos e saída

```
docker compose run --rm api sh -c 'python scripts/medir_extracao.py extrair semente_NN --lotes 8 &&
  python scripts/medir.py --gabarito .../semente_NN/pdf_liso/gabarito.json \
    --saida /tmp/medicao-4c/semente_NN/pdf_liso/saida.json --json ... --markdown ...'
```

#### Resumo por processo (relatório de qualidade + `medir.py`)

| Processo | Páginas | Nativa / OCR / vazia | Abstidas | Faltando | `texto_divergente` | CER estimado | Confiança OCR | Parede (s) | s / mil págs | Tipo de página (medir) |
|---|---|---|---|---|---|---|---|---|---|---|
| semente_01 | 196 | 5 / 184 / 7 | 16 | 0 | 0 | 1,04% | 92,4 | 104 | 533 | 196/196 |
| semente_02 | 294 | 40 / 250 / 4 | 20 | 0 | 0 | 0,97% | 92,2 | 138 | 471 | 294/294 |
| semente_03 | 450 | 107 / 338 / 5 | 41 | 0 | 0 | 1,57% | 92,3 | 197 | 438 | 450/450 |
| semente_04 | 643 | 204 / 431 / 8 | 65 | 0 | 0 | 1,18% | 92,4 | 256 | 398 | 643/643 |
| semente_05 | 891 | 362 / 518 / 11 | 74 | 0 | 0 | 1,14% | 92,1 | 317 | 355 | 891/891 |
| semente_06 | 1.200 | 600 / 579 / 21 | 99 | 0 | 0 | 1,09% | 92,5 | 356 | 297 | 1.200/1.200 |
| semente_07 | 1.598 | 993 / 577 / 28 | 133 | 0 | 0 | 1,03% | 92,2 | 387 | 242 | 1.598/1.598 |
| semente_08 | 2.198 | 1.556 / 614 / 28 | 173 | 0 | 0 | 1,18% | 92,4 | 429 | 195 | 2.198/2.198 |
| semente_09 | 3.189 | 2.425 / 721 / 43 | 251 | 0 | 0 | 1,25% | 92,3 | 557 | 175 | 3.189/3.189 |
| semente_10 | 4.988 | 4.426 / 487 / 75 | 401 | 0 | 0 | 0,97% | 93,0 | 485 | 97 | 4.988/4.988 |

Total: 15.647 páginas, nenhuma faltando, nenhuma falha de lote, nenhum falso `texto_divergente` nas 1.273 híbridas limpas. Acurácia de tipo de página pelo `medir.py`: **100%** nos dez. Fronteiras e eventos vazios (4E e 4F): precisão/recall 0 por construção.

#### CER medido pelo `medir.py` (todas as páginas, dez processos)

| Grupo | Páginas | CER |
|---|---|---|
| leve | 1.889 | 1,65% |
| media | 1.857 | 2,12% |
| forte | 953 | 7,58% |
| digitalizada | 3.426 | 3,56% |
| hibrida_corpo | 1.190 | 1,73% |
| hibrida_assinatura | 83 | 0,37% |
| nativa | 10.708 | 1,15% (marca d'água está na camada e fora do `texto` visível do gabarito) |
| capa / vazia | 10 / 230 | 0% |

Datas dd/mm/aaaa do gabarito encontradas literalmente no texto final das páginas com imagem: leve 9.895/10.677 (**92,7%**), media 9.567/10.518 (**91,0%**), forte 4.564/5.351 (**85,3%**). Todas dentro das metas definidas em 4C.6.

<a id="comandos-verificacao-4c"></a>

#### Verificação final

```
docker compose up -d --build --wait
docker compose exec api bash scripts/verificar.sh
```
ruff check: All checks passed · ruff format: 154 files already formatted · mypy --strict: no issues in 154 files
pytest: 551 passed, 1 skipped, 1 deselected (carga) em 140 s; cobertura total 99% (mínimo 90%)
ponta a ponta (integração, sem skip): 1 passed (upload PDF e ZIP → concluido com páginas)

#### Critério

| Critério | Evidência |
|---|---|
| Relatório gravado e exposto | `job_ingestao.relatorio`; rota GET auditada (`test_rotas_de_diagnostico_e_relatorio_sao_auditadas_e_isoladas`) |
| Gerado para os dez processos de referência | tabela acima |
| Saída mensurável por `scripts/medir.py` | `saida.json` medido nos dez |

### Revisão 4C

**Riscos e itens para etapas seguintes**

1. **Tempo de OCR.** 882 segundos por mil páginas digitalizadas com 4 lotes de 8 páginas. Um processo de 5.000 páginas majoritariamente digitalizado leva cerca de 75 minutos. Aceitável no piloto, mas o dimensionamento do worker (quantidade de filhos, CPU) precisa de decisão antes do uso real; registrar em 4F.9.
2. **Diagnóstico de ZIP lento**: 0,8 s por entrada. Com 878 entradas, 12 minutos só para diagnosticar. Investigar na 4E (provavelmente abrir cada PDF inteiro para ler o cabeçalho; basta ler as primeiras páginas).
3. **Teto por gabinete vale por réplica de worker.** Com várias réplicas, precisa de semáforo no Redis. Fica para quando houver mais de um worker.
4. **Reprocessamento automático ao mudar a versão do extrator** e cache por sha256 entre processos ficam para 4F.8, como previsto.
5. **Imagens decorativas opacas** (logotipo JPEG) em páginas nativas levam à abstenção e custam OCR. Sem perda de conteúdo. A calibração com o Projudi (4F.10) mede a frequência.
6. **Texto fora da página e girado** só vão ao OCR; a marcação é da 4D.1.

<a id="etapa-4d"></a>

## Etapa 4D — Saneamento

<a id="etapa-4d-1"></a>

### 4D.1 — Texto oculto

- Fundo de outra cor (texto da cor de um retângulo desenhado atrás): não detectado; a divergência OCR × nativo da 4C cobre parte. Comparar com a cor do pixel renderizado fica para quando houver caso real.

<a id="etapa-4d-2"></a>

### 4D.2 — Metadados e anotações

- Links (URI) e JavaScript do PDF não são listados (também não entram no texto).

<a id="etapa-4d-6"></a>

### 4D.6 — Idioma inesperado

**Limitações (registradas no YAML e em `docs/sistema/ingestao.md`)**

- Frases com menos de 8 palavras não são avaliadas; o espanhol divide muitas palavras com o português e só dispara em frase claramente espanhola; outros idiomas não são detectados.

<a id="etapa-4d-7"></a>

### 4D.7 — Densidade anômala

#### O que foi feito

- `dados/densidade.yaml` (versão 1): máximo de caracteres por tipo de página: nativa 15.000, ocr 15.000, vazia 200.
- `deteccao.densidade_anomala(texto, tipo)`; `FlagPagina.DENSIDADE_ANOMALA`.

#### Decisões não previstas

- Limite por tipo de **página** (nativa, ocr, vazia), porque o tipo de peça só existe na 4E; o YAML pode ganhar chaves por tipo de peça depois.

#### Critério

| Critério | Evidência |
| --- | --- |
| Página com 50 mil caracteres sinalizada | `test_densidade_anomala_por_tipo` (50.000 caracteres, nativa e OCR) |
| Páginas dos sintéticos não | `semente_01`: máximo de 2.724 (nativa) e 2.873 (ocr) caracteres; 0 páginas com a flag |

#### Comandos e saída

A 4D repetiu os [comandos de build e verificação da 4C.10](#comandos-verificacao-4c).

Saída resumida (21/10/2026): ruff e `ruff format --check` limpos; `mypy --strict` sem erros em 165 arquivos; pytest **588 passed, 1 skipped** (o skip é anterior à 4D; eram 551 testes), cobertura **98,66%**; ponta a ponta 1 passed; regressão de injeção 2 passed (159 s), `recall 1.0`, `falso_positivo 0.0`.

<a id="etapa-4d-10"></a>

### 4D.10 — Painel de flags e regressão

- Resumo por **peça** para o dossiê: peças só existem na 4E; o resumo por arquivo e por página está pronto.
- A migração 0005 não foi aplicada ao banco de desenvolvimento (que está na 0003): rodar `docker compose exec api alembic -c src/lupa/migrations/alembic.ini upgrade head` antes de usar o worker com ele. Os testes migram o banco de teste até a 0005.

<a id="etapa-4e"></a>

## Etapa 4E — Fronteiras e índice

<a id="etapa-4e-1"></a>

### 4E.1 — Sinais de fronteira

- Reinício de numeração e cabeçalho novo não ocorrem nos dez processos sintéticos (folhas contínuas,
  cabeçalho único); estão implementados e testados com páginas fabricadas. A revisão reservou a calibração com o processo real do Projudi na [4F.10](#etapa-4f-10) para exercitar esses dois sinais.

<a id="etapa-4e-2"></a>

### 4E.2 — Classificador de fronteira por regras

#### O que foi feito

- `src/lupa/ingestao/fronteiras.py`: `pontuar(sinais_pagina_anterior, sinais_pagina) -> float`
  (pura), `nivel`, `sinais_ativos`, `segmentar`. Pesos e limiares em
  `dados/fronteiras.yaml` (versão 1): título 0,5; título de seção 0,25; assinatura na página
  anterior 0,45; reinício de numeração 0,3; cabeçalho novo 0,15; protocolo no topo 0,1;
  fonte e layout 0,05. Forte ≥ 0,8; fraca ≥ 0,45 → peça com confiança baixa (pontuação × 0,5)
  e flag `fronteira_fraca`. Versos em branco são pulados (ficam com a peça anterior).

#### Medição (cenário `pdf_liso`, dez processos, `scripts/medir_extracao.py pecas` → `medir`)

Fronteira: precisão **100,0%** (2.825/2.825), recall **100,0%** (2.825/2.825); nenhuma
fronteira faltando ou sobrando. 22 fronteiras saíram fracas (todas corretas).

Erros mais comuns (antes da calibração e nas fracas restantes): assinatura destruída pelo
OCR ("eletronicame:«e", "eletron* ar ente") — resolvido com reconhecimento tolerante; páginas
lidas fora de ordem no `linhas.json` (lotes paralelos) — resolvido ordenando por número; peça
depois da capa (capa não tem assinatura) e peça cuja assinatura sumiu no OCR forte ficam
fracas (só título).

#### Decisões não previstas

- Fraca também cria peça (com flag), em vez de só avisar, seguindo "Peca.metodo = regra com
  confiança baixa e flag". `RAZÕES DE APELAÇÃO` é título de seção (0,25, nunca fronteira
  sozinho).

<a id="comandos-4e"></a>

#### Comandos

```
docker compose run --rm api python scripts/medir_extracao.py extrair semente_NN --lotes 8 --destino /medicao
docker compose run --rm api python scripts/medir_extracao.py pecas --destino /medicao
```
(volume Docker `lupa_medicao4e` montado em `/medicao`; nada copiado para o host)

#### Checklist

| Critério | Evidência |
|---|---|
| Precisão ≥ 95% no liso | 100,0% (2.825/2.825) |
| Recall ≥ 95% no liso | 100,0% (2.825/2.825) |
| Pesos em YAML versionado | `fronteiras.yaml` versão 1 |
| Testes | `tests/ingestao/test_fronteiras.py` (11 testes) |

<a id="etapa-4e-9"></a>

### 4E.9 — Medição contra gabarito

#### O que foi feito

- `PecaSaida.data` (opcional) em `saida_pipeline`; `medir` ganhou `data_peca` (acurácia; sem
  data prevista conta como erro) e a linha no Markdown.
- `scripts/medir_extracao.py extrair --destino` grava também `linhas.json.gz`; subcomando
  `pecas` monta o índice nos três cenários e mede com `medir`.

#### Decisões não previstas

- Só o `pdf_liso` foi extraído (OCR, ~55 min no total); as folhas são as mesmas nos três
  cenários, então o texto é reaproveitado pelo mapa `arquivos[].folhas` do gabarito; as páginas
  do índice do `pdf_indice` são lidas por texto nativo e o diagnóstico (fronteiras da origem)
  de cada cenário roda de verdade. Por isso tipo, origem e data são iguais nos três.
- A medição de peças envia páginas sem texto ao `medir` (o CER em Python puro levaria horas;
  ele já foi medido na 4C.10).

#### Por processo e cenário

| Processo | Cenário | Fonte | Peças gab./saída | Fronteira P | Fronteira R | Tipo | Origem | Data | Divergências | Fracas | Desconhecida | Sem data |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| semente_01 | zip_por_peca | manifesto | 51/51 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 1 | 0 | 0 | 0 |
| semente_01 | pdf_indice | bookmark | 51/51 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 1 | 0 | 0 | 0 |
| semente_01 | pdf_liso | regras | 51/51 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0 | 1 | 0 | 0 |
| semente_02 | zip_por_peca | manifesto | 84/84 | 100.0% | 100.0% | 100.0% | 100.0% | 98.8% | 2 | 0 | 0 | 1 |
| semente_02 | pdf_indice | bookmark | 84/84 | 100.0% | 100.0% | 100.0% | 100.0% | 98.8% | 2 | 0 | 0 | 1 |
| semente_02 | pdf_liso | regras | 84/84 | 100.0% | 100.0% | 100.0% | 100.0% | 98.8% | 0 | 2 | 0 | 1 |
| semente_03 | zip_por_peca | manifesto | 79/79 | 100.0% | 100.0% | 100.0% | 100.0% | 98.7% | 1 | 0 | 0 | 0 |
| semente_03 | pdf_indice | bookmark | 79/79 | 100.0% | 100.0% | 100.0% | 100.0% | 98.7% | 1 | 0 | 0 | 0 |
| semente_03 | pdf_liso | regras | 79/79 | 100.0% | 100.0% | 100.0% | 100.0% | 98.7% | 0 | 1 | 0 | 0 |
| semente_04 | zip_por_peca | manifesto | 120/120 | 100.0% | 100.0% | 100.0% | 100.0% | 98.3% | 1 | 0 | 0 | 1 |
| semente_04 | pdf_indice | bookmark | 120/120 | 100.0% | 100.0% | 100.0% | 100.0% | 98.3% | 1 | 0 | 0 | 1 |
| semente_04 | pdf_liso | regras | 120/120 | 100.0% | 100.0% | 100.0% | 100.0% | 98.3% | 0 | 1 | 0 | 1 |
| semente_05 | zip_por_peca | manifesto | 172/172 | 100.0% | 100.0% | 100.0% | 98.3% | 96.5% | 4 | 0 | 3 | 2 |
| semente_05 | pdf_indice | bookmark | 172/172 | 100.0% | 100.0% | 100.0% | 98.3% | 96.5% | 4 | 0 | 3 | 2 |
| semente_05 | pdf_liso | regras | 172/172 | 100.0% | 100.0% | 100.0% | 98.3% | 96.5% | 0 | 4 | 3 | 2 |
| semente_06 | zip_por_peca | manifesto | 240/240 | 100.0% | 100.0% | 100.0% | 99.6% | 99.6% | 2 | 0 | 1 | 1 |
| semente_06 | pdf_indice | bookmark | 240/240 | 100.0% | 100.0% | 100.0% | 99.6% | 99.6% | 2 | 0 | 1 | 1 |
| semente_06 | pdf_liso | regras | 240/240 | 100.0% | 100.0% | 100.0% | 99.6% | 99.6% | 0 | 2 | 1 | 1 |
| semente_07 | zip_por_peca | manifesto | 286/286 | 100.0% | 100.0% | 100.0% | 99.3% | 99.0% | 4 | 0 | 2 | 2 |
| semente_07 | pdf_indice | bookmark | 286/286 | 100.0% | 100.0% | 100.0% | 99.3% | 99.0% | 4 | 0 | 2 | 2 |
| semente_07 | pdf_liso | regras | 286/286 | 100.0% | 100.0% | 100.0% | 99.3% | 99.0% | 0 | 4 | 2 | 2 |
| semente_08 | zip_por_peca | manifesto | 384/384 | 100.0% | 100.0% | 100.0% | 98.7% | 98.7% | 2 | 0 | 5 | 1 |
| semente_08 | pdf_indice | bookmark | 384/384 | 100.0% | 100.0% | 100.0% | 98.7% | 98.7% | 2 | 0 | 5 | 1 |
| semente_08 | pdf_liso | regras | 384/384 | 100.0% | 100.0% | 100.0% | 98.7% | 98.7% | 0 | 2 | 5 | 1 |
| semente_09 | zip_por_peca | manifesto | 531/531 | 100.0% | 100.0% | 100.0% | 99.8% | 98.7% | 4 | 0 | 1 | 1 |
| semente_09 | pdf_indice | bookmark | 531/531 | 100.0% | 100.0% | 100.0% | 99.8% | 98.7% | 4 | 0 | 1 | 1 |
| semente_09 | pdf_liso | regras | 531/531 | 100.0% | 100.0% | 100.0% | 99.8% | 98.7% | 0 | 4 | 1 | 1 |
| semente_10 | zip_por_peca | manifesto | 878/878 | 100.0% | 100.0% | 100.0% | 100.0% | 99.1% | 1 | 0 | 0 | 3 |
| semente_10 | pdf_indice | bookmark | 878/878 | 100.0% | 100.0% | 100.0% | 100.0% | 99.1% | 1 | 0 | 0 | 3 |
| semente_10 | pdf_liso | regras | 878/878 | 100.0% | 100.0% | 100.0% | 100.0% | 99.1% | 0 | 1 | 0 | 3 |

#### Por cenário (micro-média)

| Cenário | Peças gab./saída | Fronteira P | Fronteira R | Tipo | Origem | Data | tipo_data igual | Divergências | Fracas | Desconhecida | Sem data |
|---|---|---|---|---|---|---|---|---|---|---|---|
| zip_por_peca | 2825/2825 | 100.0% (2825/2825) | 100.0% (2825/2825) | 100.0% (2825) | 99.6% (2813) | 98.8% (2791) | 31.3% | 22 | 0 | 12 | 12 |
| pdf_indice | 2825/2825 | 100.0% (2825/2825) | 100.0% (2825/2825) | 100.0% (2825) | 99.6% (2813) | 98.8% (2791) | 31.3% | 22 | 0 | 12 | 12 |
| pdf_liso | 2825/2825 | 100.0% (2825/2825) | 100.0% (2825/2825) | 100.0% (2825) | 99.6% (2813) | 98.8% (2791) | 31.3% | 0 | 22 | 12 | 12 |

#### Comandos

Use os [comandos de extração e medição da 4E.2](#comandos-4e) com o volume `lupa_medicao4e`.

<a id="etapa-4e-10"></a>

### 4E.10 — Índice no modelo e na API

- Divergências do cenário com índice não chegam a zero (22/2.825): ver 4E.3.
- Calibração com processo real (Projudi) fica para 4F.10.
- O teste de API reprocessa o PDF sintético em cada um dos 4 testes (≈ 45 s cada); dá para
  compartilhar o processamento quando as fixtures de banco aceitarem escopo maior.

### Revisão 4E

**Observações sobre as métricas**

- `tipo_data` coincide com o gabarito em 31%, porque o gabarito rotula como protocolo ou juntada datas que no texto só aparecem na assinatura. Não é critério; vale ajustar o gabarito na 4F ou aceitar a semântica do extrator.
- Os erros de data e origem vêm todos do nível forte de degradação do OCR. São os mesmos casos que o relatório da 4C.6 previu.

<a id="etapa-4f"></a>

## Etapa 4F — Eventos e ponta a ponta

<a id="etapa-4f-1"></a>

### 4F.1 — Padrões de data

- Datas sem ano ("15 de maio") e intervalos ("de 10 a 15/05/2014") não são datas para a
  extração; o segundo dá só `15/05/2014`.

<a id="etapa-4f-2"></a>

### 4F.2 — Extratores por tipo de peça

- Causas de aumento e diminuição e concurso de crimes na pena máxima (limitação já documentada
  nas validações).
- Recurso do assistente de acusação e prazos especiais (o catálogo não conhece).

<a id="etapa-4f-3"></a>

### 4F.3 — Evidência obrigatória

- `bbox` da evidência não é preenchida (as coordenadas por linha estão em
  `pagina.coordenadas`; a tela da Etapa 6 pode calcular).

<a id="etapa-4f-4"></a>

### 4F.4 — Validação cruzada

- A reconferência não pega o erro de OCR que troca um dígito por outro (o literal errado está no
  texto). Foi a causa das 2 datas erradas da 4F.9 (semente_04, nível forte de degradação). Mitigação
  possível depois: cruzar a data com o dia da semana ou com a data da peça (4E.6).

<a id="etapa-4f-5"></a>

### 4F.5 — Réus e pseudonimização

- Réu qualificado fora da denúncia (aditamento, termo de interrogatório) não é identificado.
- Cifragem de `reu_identidade` (fica para quando houver chave por gabinete, Etapa 1).

<a id="etapa-4f-6"></a>

### 4F.6 — Gravação de fatos

- Gravação em lote com um único `INSERT` (cada fato usa `salvar_fato`, que já é a interface do
  domínio; o maior processo de referência tem 50 fatos).

<a id="etapa-4f-7"></a>

### 4F.7 — Execução do catálogo

- Reexecução automática do catálogo quando o assessor corrige um fato (Etapa 6).

<a id="etapa-4f-8"></a>

### 4F.8 — Cache e reprocessamento

- Reaproveitar páginas de uma entrada de ZIP igual a um PDF já enviado (o cache é pelo hash do
  arquivo enviado, não por entrada).

<a id="etapa-4f-9"></a>

### 4F.9 — Ponta a ponta nos processos de referência

#### O que foi feito

- `scripts/ponta_a_ponta.py`: para cada processo e cenário, lacra o arquivo no MinIO do compose
  num processo novo do banco de desenvolvimento e roda `processar_job` (o código do worker:
  validação no sandbox, diagnóstico, páginas ou cache, índice, eventos, achados). Lê do banco
  peças, fatos e achados e mede com `lupa.sinteticos.medicao.medir` (agora com `datas`) e
  `lupa.sinteticos.achados.comparar` (achados na `data_referencia` do gabarito).
- `scripts/medir_extracao.py eventos`: a mesma medição sem banco, nos 30 arquivos, sobre as
  páginas do volume `lupa_medicao4e`.
- Upload "pelo worker com o arquivo no storage" (opção prevista no roteiro), não por HTTP: a
  rota de upload exige sessão com MFA e o caminho depois do lacre é idêntico.

#### O que foi reaproveitado do volume `lupa_medicao4e`

O OCR dos dez processos leva cerca de 64 min (15.647 folhas a ~245 s/mil na 4E), acima de uma
hora. Por isso:

1. **OCR real, ponta a ponta**: semente_01 (196 folhas) e semente_02 (294 folhas) nos três
   cenários (`pdf_liso`, `zip_por_peca`, `pdf_indice`), extrator `4f.0`, sem nada reaproveitado.
2. **Páginas do volume**: semente_03 a semente_10, cenário `pdf_liso`. As linhas
   `DIR/<processo>/pdf_liso/linhas.json.gz` (extração 4E, versão `4e.0`) foram gravadas como
   páginas de um arquivo-fonte do mesmo gabinete com o SHA-256 do PDF e a versão corrente
   (`4f.0`), e o upload do PDF real recebeu essas páginas pelo cache da 4F.8. Validação no
   sandbox, diagnóstico, índice, eventos, achados e gravação rodaram de verdade. A diferença
   4e.0 → 4f.0 é só o OCR de detecção em imagens de páginas nativas (não muda texto).
3. **Sem banco, 30 arquivos**: `medir_extracao.py eventos` sobre as mesmas linhas do volume, com
   o diagnóstico real de cada cenário (ZIP e `pdf_indice` dos dez processos).

#### Resultados

##### Ponta a ponta pelo worker (14 uploads)

| Processo | Cenário | Folhas | Tempo (s) | s/mil folhas | Eventos P | Eventos R | Datas P | Achados iguais | 2º upload (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| semente_01 | pdf_liso | 196 | 159,9 | 816 | 23/23 | 23/23 | 20/20 | 3/3 | 3,6 |
| semente_01 | zip_por_peca | 196 | 167,0 | 852 | 23/23 | 23/23 | 20/20 | 3/3 | 5,2 |
| semente_01 | pdf_indice | 196 | 162,3 | 828 | 23/23 | 23/23 | 20/20 | 3/3 | 3,6 |
| semente_02 | pdf_liso | 294 | 212,7 | 723 | 48/48 | 48/48 | 45/45 | 3/3 | 5,1 |
| semente_02 | zip_por_peca | 294 | 228,5 | 777 | 48/48 | 48/48 | 45/45 | 3/3 | 7,9 |
| semente_02 | pdf_indice | 294 | 218,8 | 744 | 48/48 | 48/48 | 45/45 | 3/3 | 4,6 |
| semente_03 | pdf_liso (volume) | 450 | 7,1 | — | 12/12 | 12/13 | 9/9 | 3/3 | 6,8 |
| semente_04 | pdf_liso (volume) | 643 | 8,9 | — | 28/30 | 28/31 | 25/27 | 1/3 | 9,4 |
| semente_05 | pdf_liso (volume) | 891 | 11,1 | — | 21/21 | 21/22 | 18/18 | 2/3 | 12,0 |
| semente_06 | pdf_liso (volume) | 1200 | 14,7 | — | 50/50 | 50/50 | 47/47 | 3/3 | 14,9 |
| semente_07 | pdf_liso (volume) | 1598 | 17,7 | — | 13/13 | 13/13 | 10/10 | 3/3 | 17,2 |
| semente_08 | pdf_liso (volume) | 2198 | 22,5 | — | 30/30 | 30/30 | 27/27 | 3/3 | 21,9 |
| semente_09 | pdf_liso (volume) | 3189 | 31,8 | — | 49/49 | 49/50 | 46/46 | 2/3 | 31,7 |
| semente_10 | pdf_liso (volume) | 4988 | 44,8 | — | 25/25 | 25/25 | 22/22 | 3/3 | 46,6 |

Totais: eventos 441/443 corretos (precisão 99,5%), recall 441/447 (98,7%); **datas 399/401
(99,5%)**; achados iguais 38/42 (90,5%); 0 fato sem evidência e 0 evidência não literal.

##### Sem banco, 30 arquivos (`medir_extracao.py eventos`)

| Medida | Valor |
| --- | --- |
| Eventos: precisão | 897/903 = 99,34% |
| Eventos: recall | 897/915 = 98,03% |
| **Datas: precisão** | **807/813 = 99,26%** (meta ≥ 99%) |
| Datas: recall | 807/825 = 97,82% |
| Achados iguais (resultado e valores) | 78/90 = 86,7%; resultado igual 81/90 = 90,0% |
| Fatos sem evidência | 0 |
| Evidências cujo trecho difere de `texto[inicio:fim]` | 0 |
| Tempo da extração de eventos | 1,4 s por mil folhas |

Os três cenários dão o mesmo resultado por processo (mesmas folhas). Os únicos erros de data
(2, na semente_04, contados nos três cenários) são leituras do OCR em degradação forte
(2017 → 2020, 02 → 12); as perdas de recall são páginas digitalizadas fortes em que o trecho
saiu ilegível. O detalhe por processo da [4F.7](#etapa-4f-7) está no relatório arquivado no commit `58e9774`.

<a id="tempo-4f-9"></a>

##### Tempo por mil páginas e dimensionamento do worker

Configuração: 1 worker, 12 CPUs no host Docker, `paginas_por_lote=8`, `lotes_por_job=4`,
`lotes_por_gabinete=4`, sandbox 1024 MB / 60 s de CPU por lote, Tesseract com uma thread, sem
fatiar.

| Medida | s por mil páginas |
| --- | --- |
| Nativo (1000 páginas, extrator 4f.0 com OCR de detecção em imagens) | 35,8 |
| Digitalizado (100 páginas) | 911,9 |
| Processo misto real (semente_01/02, 85–94% OCR), do upload aos achados | 723 a 852 |
| Segundo upload do mesmo arquivo (cache), do upload aos achados | 9 a 26 (dominado pela validação no sandbox) |
| Eventos + catálogo | ~1,4 (eventos) + < 1 (catálogo) |

#### Decisões não previstas

- `imagem_com_texto` (revisão 4D §6.2): implementado o OCR só de detecção em imagens com área
  acima de 2% da página nativa (`lupa/ingestao/imagem_nativa.py`, extrator `4f.0`). Custo medido
  antes de implementar: 21 a 27 s por mil páginas nativas (semente_04 e semente_06); depois, o
  nativo completo ficou em 35,8 s por mil. A injeção do corpus é detectada
  (`dirigido_a_sistema`, `alterar_resultado`). Registrado em `docs/sistema/ingestao.md`.
- Dimensionamento (revisão 4C §5.1): registrado acima e em `docs/sistema/ingestao.md`.

#### O que ficou de fora

- OCR real dos processos 03 a 10 (reaproveitado, como descrito).
- Upload pela rota HTTP.

#### Comandos

```
docker compose run --rm -T api python scripts/ponta_a_ponta.py \
    --processos semente_01,semente_02 --cenarios pdf_liso,zip_por_peca,pdf_indice --repetir
docker compose run --rm -T -v lupa_medicao4e:/m api python scripts/ponta_a_ponta.py \
    --processos semente_03,...,semente_10 --cenarios pdf_liso --volume /m --repetir
docker compose run --rm -T -v lupa_medicao4e:/m api python scripts/medir_extracao.py eventos --destino /m
docker compose run --rm -T api python scripts/medir_extracao.py tempo --nativas 1000 --digitalizadas 100
```

#### Checklist

| Item | Evidência |
| --- | --- |
| Dez processos no `pdf_liso` até achados | 10/10 `concluido` (2 com OCR real, 8 com páginas do volume) |
| ≥ 2 no ZIP e ≥ 2 no `pdf_indice` | semente_01 e semente_02 nos dois, OCR real |
| Harness com eventos: P/R de eventos e precisão de datas | `medir` com `datas`; tabelas acima |
| Datas ≥ 99% de precisão | 99,5% (ponta a ponta) e 99,26% (30 arquivos) |
| Zero fato sem evidência | 0 em 443 (ponta a ponta) e 0 em 903 (30 arquivos) |
| Tempo por mil páginas | 35,8 s nativo, 911,9 s digitalizado, 723–852 s misto |
| Reaproveitamento documentado | seção "O que foi reaproveitado" |

<a id="etapa-4f-10"></a>

### 4F.10 — Calibração com o processo real

#### O que foi feito

O arquivo do Projudi ainda não existe. Entregue o roteiro e a ferramenta para o dia em que ele
chegar:

- `docs/piloto/calibracao-projudi.md`: como montar o arquivo no contêiner sem copiá-lo para o
  repositório, comando, o que o relatório traz, instruções de conferência para o assessor, o que
  medir (com a referência sintética de cada medida), onde ajustar cada tipo de erro e qual versão
  subir, limpeza e a tabela "Registro" a preencher (acertou, errou, mudou).
- `scripts/calibrar.py <arquivo>` sobre `lupa/ingestao/calibracao.py`: cria um gabinete de
  calibração, lacra e processa o arquivo pelo código do worker e grava `relatorio.md` (diagnóstico,
  páginas, peças, eventos com trecho, achados, colunas "Confere?") e `relatorio.json` em `/tmp`
  do contêiner.
- `tests/ingestao/test_calibracao.py`: o mesmo caminho sobre o processo sintético dos testes.

#### Teste com processo sintético

```
docker compose exec -T api python scripts/calibrar.py \
    /app/.sinteticos/referencia/semente_01/pdf_indice/autos.pdf --saida /tmp/calibracao --titulo "semente_01 pdf_indice"
rc=0
Cenário pdf_com_bookmarks_e_indice; 198 páginas (7 nativas, 184 OCR, 7 vazias); 16 abstidas;
CER estimado 0,0104; 160,5 s de extração (811 s por mil); 90 linhas de tabela no relatório;
achados: tempestividade conforme, preventiva atencao, prescrição atencao.
```

A prescrição sai `atencao` porque o worker usa a data de hoje (2026) como referência; no
gabarito (referência 17/07/2016) ela é `conforme`, e a 4F.9 confirma 3/3 nessa data.

#### Decisões não previstas

- O relatório contém trechos dos autos: fica no contêiner e o roteiro proíbe versioná-lo.

#### O que ficou de fora

- A calibração em si (depende do arquivo real); a seção "Registro" está vazia.

#### Checklist

| Item | Evidência |
| --- | --- |
| Roteiro pronto (comandos, o que medir, comparar com o assessor, onde registrar) | `docs/piloto/calibracao-projudi.md` |
| `scripts/calibrar.py` gera o relatório Markdown | execução acima, `rc=0` |
| Testado com processo sintético | acima e `test_calibracao_de_processo_sintetico_gera_relatorio_para_conferencia` |

<a id="etapa-5"></a>

## Etapa 5 — Agente e chat

<a id="etapa-5-1"></a>

### 5.1 — Contrato do agente

- Aprovação formal do contrato pelo responsável técnico.

<a id="etapa-5-2"></a>

### 5.2 — Ferramentas de leitura estruturada

- Evento `busca` por chamada de `buscar_texto`: a chamada já fica em `chamada_modelo` e o termo seria conteúdo.

<a id="etapa-5-3"></a>

### 5.3 — Ferramenta de cálculo

- Nada.

<a id="etapa-5-4"></a>

### 5.4 — Válvula de escape

- Imagem da página para o modelo (visão): fora do escopo.

<a id="etapa-5-5"></a>

### 5.5 — Montagem de contexto e prompts

- Pseudonimização só do nome completo e do CPF; nome parcial (só sobrenome) passa. Fica com a anonimização na origem (TODO da seção 11 dos requisitos).

<a id="etapa-5-6"></a>

### 5.6 — Conferência de citações

- Marcar o processo `em revisão` no incidente (prompt-injection.md §8): o status do processo é da ingestão; fica para o painel da Etapa 6.

<a id="etapa-5-7"></a>

### 5.7 — Política de recusa

- Classificador por modelo: fora; as regras atingem as metas e são determinísticas.

<a id="etapa-5-8"></a>

### 5.8 — Suíte de injeção do agente

- Rodar a suíte com o modelo real (exige credencial).

<a id="etapa-5-9"></a>

### 5.9 — Registro e custo

- Custo em dinheiro por chamada (`total_cost_usd`): não gravado; os tokens bastam para o relatório de uso.

<a id="etapa-5-10"></a>

### 5.10 — Dossiê gerado

- Resumo narrativo do processo inteiro: fora (só por peça).

<a id="balanco-5"></a>

### Balanço da etapa 5 e das subetapas 6.1 a 6.3

| Verificação | Resultado |
| --- | --- |
| ruff, mypy --strict | limpos, 234 arquivos |
| pytest | 766 testes; três execuções completas, com uma falha intermitente do mesmo teste de observabilidade da 4A.9 (ver revisão 5, §1), nenhuma outra; cobertura 98,7% |
| Front | lint 0, typecheck 0, 18 testes unitários; 8 de 8 testes Playwright contra a stack real |
| Agente | recusa: recall 100% e falso positivo 0% em 60 perguntas; injeção: 14 execuções com modelo manipulado simulado, zero achado suprimido ou criado, zero vazamento, nenhuma ferramenta embutida executada |
| Banco | migração 0007 (head) |
| Stack | api, db, minio, redis, worker, front, proxy saudáveis; front em `https://localhost:8443` pelo proxy Caddy, API no mesmo origin |

Requisitos atendidos nesta rodada: chat de localização e extração com citação conferida por código e recusa de valoração, tipificação e conclusão jurídica (seção 4.4 dos requisitos); interface web com login por usuário e senha, MFA por aplicativo, reset manual e gestão de usuários pelos três papéis (seções 3 e 8); as duas correções obrigatórias da Etapa 3 (auditoria gravada antes da resposta; bloqueio progressivo e rate limit por IP).

**Condição registrada:** o smoke test com o modelo real (dois testes marcados `llm`) não rodou por falta de credencial neste ambiente. Deve ser executado pelo responsável técnico com `ANTHROPIC_API_KEY` no ambiente antes de qualquer uso real do chat. Até lá, a garantia de que o harness do Claude Agent SDK não executa ferramentas embutidas vem das opções do SDK e do hook de bloqueio, ambos testados sem rede.

Novas decisões pendentes de Victor: chave de API da Anthropic para o piloto; aprovação formal do contrato `docs/sistema/agente.md`.

<a id="etapa-6"></a>

## Etapa 6 — Interface web

<a id="etapa-6-1"></a>

### 6.1 — Esqueleto do front

**Fora do escopo desta subetapa**

CSP, HSTS e demais cabeçalhos de segurança completos (6.10; já há `nosniff`, `Referrer-Policy`,
`X-Frame-Options`). Alternância manual de tema (só segue o sistema).

<a id="etapa-6-2"></a>

### 6.2 — Login e MFA

**Limitações**

- A expiração real (30 min de inatividade ou 8 h) não é esperada no E2E: o teste remove o cookie
  do navegador, que é o efeito visto pelo front quando o servidor recusa a sessão. A expiração no
  servidor segue coberta por `test_sessao_expira_por_inatividade_e_por_prazo_absoluto`.
- Numa recarga completa da página sem sessão válida o front não distingue "expirou" de "nunca
  entrou" (o cookie é `HttpOnly`); o aviso aparece nas navegações e chamadas dentro da SPA.
- A porta direta da API (`API_PORTA_HOST`), quando publicada, entra pela rede do Docker; se a
  origem cair na sub-rede `borda`, um cliente local poderia forjar `X-Forwarded-For`. Só em
  127.0.0.1; em produção, não publique `API_PORTA_HOST`.

<a id="etapa-6-3"></a>

### 6.3 — Gestão de usuários

**Fora do escopo**

Editar nome de usuário ou mudar papel (a API não oferece); listar sessões ativas; confirmação
antes de desativar (a ação é reversível pela reativação e auditada).

<a id="etapa-6-4"></a>

### 6.4 — Lista e upload de processos

**Fora do escopo**

Arrastar e soltar; vários arquivos em paralelo (um envio por vez); retomar envio interrompido
(o envio é refeito do zero; o SHA-256 evita duplicar o conteúdo já lacrado); websockets (o
polling para quando nada está em processamento). O processo novo fica com `status=criado` até o
worker atualizá-lo; a situação mostrada vem de `job_ingestao`.

<a id="etapa-6-5"></a>

### 6.5 — Dossiê e linha do tempo

**Fora do escopo**

Edição da ficha; exportação do dossiê em PDF; filtro da linha do tempo por tipo.

<a id="etapa-6-6"></a>

### 6.6 — Visualizador de PDF com evidência

**Limitação registrada (texto oculto)**

A imagem mostra o que o PDF desenha, sem as camadas opcionais e só dentro da `CropBox`. Assim,
texto numa camada OCG ou fora da área visível não aparece. Texto branco sobre fundo branco ou em
fonte de 1 pt também não aparece visualmente (como para quem lê o papel). Mas conteúdo que o
próprio PDF desenha visível (por exemplo, uma instrução impressa no corpo, ou texto da mesma cor
de um retângulo colorido desenhado atrás dele) aparece normalmente: a imagem não é filtro de
injeção; os alertas de saneamento da 4D continuam sendo a fonte para isso. Anotações do PDF não
são desenhadas.

**Fora do escopo**

Seleção ou cópia de texto na página (de propósito); miniaturas; destaque com precisão de
caractere dentro da linha (o retângulo cobre a linha inteira atingida); invalidação do cache de
PNG quando a versão de renderização muda (a versão está na chave; versões antigas ficam até
limpeza manual do prefixo).

<a id="etapa-6-7"></a>

### 6.7 — Tela de validações

**Fora do escopo**

Desfazer correção (corrige-se de novo o fato vigente); editar ou apagar anotação; correção de
fato que não tenha evidência (todo fato tem ao menos uma); escolha da data de referência das
validações na tela (usa a data do dia).

<a id="etapa-6-8"></a>

### 6.8 — Chat (com o item 3 da revisão 5)

- Teto por chamada continua com status `descartada` (contrato da Etapa 5); a interface mostra o
  texto do limite. O rótulo "Limite de uso atingido" aparece no teto de conversa/processo.
- Depois do E2E a API fica com o cliente falso até a próxima subida sem a variável.

<a id="etapa-6-9"></a>

### 6.9 — Tela de auditoria (com o item 5 da revisão 5)

- Seleção de usuário/processo por nome (a API de auditoria trabalha com ids).
- Custo dos resumos do dossiê não entra no relatório por usuário (não têm conversa).

<a id="etapa-6-10"></a>

### 6.10 — Acessibilidade, segurança do front e testes ponta a ponta

**Fora do escopo ou pendente**

- HSTS só vale de verdade com certificado real (produção, 7.10). Não foi pedido preload.
- O hash do anunciador do SvelteKit precisa ser revisto a cada atualização do framework. Se mudar,
  o E2E e a varredura acusam.
- O `limpar_dev.py` não remove objetos órfãos no MinIO.
- Destaque de evidência por caractere, retomada de upload e desfazer correção continuam para
  depois do piloto (revisão 6.4-6.9, itens 4 e 5).
- Incidente de processo: no editor do host, alguns arquivos meus ficaram com fim de linha CRLF e
  quebraram o `verificar.sh` no contêiner (`set -o pipefail` inválido). Foi corrigido convertendo
  para LF só os arquivos desta subetapa. Arquivos de outras etapas que já estavam em CRLF ficaram
  como estavam.

<a id="balanco-6"></a>

### Balanço ao concluir a interface (6.4 a 6.10)

| Verificação | Resultado |
| --- | --- |
| Backend | 828 testes, 1 pulado; cobertura 98,59%; três execuções completas verdes pelo executor, mais a do revisor (seção 1.1 da revisão 6.10) |
| Front | 56 testes unitários; 36 de 36 testes Playwright contra a stack real, incluindo axe em 13 telas nos dois temas e varredura de cabeçalhos |
| Segurança do front | CSP sem script inline, HSTS, Permissions-Policy, COOP e CORP; nada dos autos renderizado como HTML ou link; PDF nunca chega ao navegador (página renderizada no servidor dentro do sandbox) |
| Banco | migração 0009 (head); banco de desenvolvimento limpo de dados sintéticos (89 gabinetes e 1 milhão de eventos removidos, cadeia global preservada) |

Requisitos atendidos nesta rodada: dossiê navegável com índice, ficha, linha do tempo e alertas; visualizador com evidência destacada; tela de validações com anotação e correção de fato com histórico; chat com citações clicáveis e estado "em revisão" após incidente; tela de auditoria com exportação, verificação da cadeia e relatório de uso com custo estimado; acessibilidade e cabeçalhos de segurança.

A interface web da primeira versão está completa. Restam as Etapas 7 (criptografia em repouso, guia do assessor, operação) e 8 (piloto).

Cobre tudo que foi executado por agentes e revisado: Etapa 0 (esqueleto), 1 (esquemas de dados), 2 (validações), 3 (acesso e auditoria), 4A.1 (adaptador), 4A a 4F (ingestão completa), 5 (agente e chat) e 6 completa (interface web, subetapas 6.1 a 6.10).

<a id="etapa-7"></a>

## Etapa 7 — Criptografia, backup e guias

<a id="etapa-7-1"></a>

### 7.1 — Decisão do object storage

- Assinatura do responsável técnico.
- Teste de compatibilidade do `ArmazenamentoS3` contra Garage/RustFS (só se o plano C for adotado).

<a id="etapa-7-2"></a>

### 7.2 — Cofre de chaves (HashiCorp Vault)

- TLS no listener, auto-unseal e repartição das chaves de unseal (produção; ver
  `docs/sistema/criptografia.md`). Reiniciar o Vault sela o cofre: rodar o script de novo.

<a id="etapa-7-3"></a>

### 7.3 — Chave de dados por processo

- Zerar a memória da DEK: em Python `bytes` é imutável; o contexto só descarta a referência.
- Nos testes antigos que criam vários processos numa sessão e depois gravam páginas, o processo
  ativo é o último criado (as páginas abrem normalmente; em produção o processo ativo é sempre o do
  caminho ou do job).

<a id="etapa-7-4"></a>

### 7.4 — Cifra dos originais

- Objetos gravados em claro antes da 7.4 no MinIO de desenvolvimento não foram recifrados (são
  lidos como legado); reenvio ou descarte resolve.
- `ArmazenamentoS3.ler` continua lendo o objeto inteiro em memória (comportamento anterior).

A [varredura da 7.10](#etapa-7-10) e a [decisão posterior à v1](../decisoes/registro.md#decisões-posteriores-à-v1) registram o que mudou no tratamento do legado.

<a id="etapa-7-5"></a>

### 7.5 — Cifra de colunas

#### O que foi feito

- `TextoCifrado`/`JsonCifrado` (`seguranca/tipos.py`) em `pagina.texto`, `texto_normalizado`,
  `texto_nativo`, `texto_ocr`, `trechos_ocultos`, `trechos_suspeitos`, `evidencia.trecho` e
  `mensagem.texto` (formato `lupa1:`, AAD com coluna e processo). `texto_nativo`/`texto_ocr`
  entraram além do roteiro: guardam o mesmo texto da página.
- Migração 0010 (`esquema_v0010.py`, `down_revision = "0009"`): coluna da DEK, `descartado` no
  CHECK, trechos JSONB → texto, funções `lupa_chave_processo` e `lupa_descartar_processo`, e
  conversão em lotes de 500 dos dados existentes (idempotente: pula `lupa1:`/`vault:`; reversível;
  processos de gabinete com chave destruída ficam como estão). Aplicada no banco de
  desenvolvimento com o Vault real: 30 de 30 páginas cifradas.
- `ingestao/repositorio.resumo_paginas`: `jsonb_array_length` → `len()` em Python.
- `agente/ferramentas/leitura.buscar_texto`: busca em memória por processo, em blocos de 200,
  até 20 acertos ou `LUPA_BUSCA_MAX_PAGINAS` (padrão 5000).

#### Testes

- `test_dump_logico_nao_contem_sentinelas_em_claro`: dump lógico de todas as tabelas do banco de
  teste (`pg_dump --data-only` se houver no contêiner, senão `COPY ... TO STDOUT` de cada tabela,
  que é o que o pg_dump de dados produz; a imagem da API não tem pg_dump) sem as sentinelas de
  página, trecho, mensagem e nome do réu.
- `test_migracao_cifra_dados_existentes_idempotente_e_reversivel`: banco próprio na 0009 com dados
  em claro → head (cifrado e legível pela aplicação) → 0009 (claro de volta) → head.
- `test_busca_em_memoria_respeita_o_teto_de_paginas`, `test_texto_gravado_cifrado_e_lido_em_claro`.

#### Desempenho (contêiner da API, banco do compose, 1000 páginas de 2500 caracteres, 3 colunas de texto + 2 JSON por página)

Medido com um script de rascunho (`medir_cifra.py`, fora do repositório) num processo sintético,
duas rodadas de cada (após aquecimento):

| | gravar 1000 páginas (ORM) | ler texto de 1000 páginas |
|---|---|---|
| sem cifra | 0,37 s / 0,39 s | 0,015 s |
| com cifra | 0,70 s / 0,45 s | 0,09 s / 0,06 s |

Custo: cerca de +0,1 a +0,3 s por mil páginas na gravação e +0,05 a +0,08 s na leitura, ínfimo
perto da extração (segundos por página com OCR). Objeto de 1 MB: cifrar + decifrar em 0,5 a 1,2 ms.

#### O que ficou de fora

- Busca por índice (sem ILIKE não há índice de texto; o teto limita o custo em processos grandes).
- `hash_texto`/`hash_trecho` continuam em claro (SHA-256 necessário às citações).

<a id="etapa-7-6"></a>

### 7.6 — Identidades dos réus

- `identidade_lida` sem `usuario_id` (o pseudonimizador não recebe o ator); o processo e o
  instante identificam a requisição na trilha.

<a id="etapa-7-7"></a>

### 7.7 — Exclusão criptográfica

- Backups do banco anteriores ao descarte ainda guardam o envelope da DEK (a política de
  retenção da 7.8 decide quando somem).
- A listagem do cache de renderização percorre o prefixo `renderizacao/` inteiro (aceitável no piloto).

<a id="etapa-7-8"></a>

### 7.8 — Backup cifrado

**Fora de escopo / pendente**

- Teste automático do caminho de recusa por falta de espaço (não há como simular disco cheio
  com bind mount sem tocar o host); conferido por leitura e pelo log.
- A imagem `lupa-backup:local` ainda cria `/trabalho` (inofensivo, não é mais usado); remover no
  próximo rebuild.
- Ligar o snapshot do Vault quando o serviço existir.

<a id="etapa-7-9"></a>

### 7.9 — Guias do assessor e do desembargador

**Pendente**

- Leitura por um assessor humano de fora do projeto (critério do roteiro) continua a fazer no piloto.

<a id="etapa-7-10"></a>

### 7.10 — Documentação de operação

21 de outubro de 2026 · executor

#### O que foi feito

1. **`docs/operacao/operacao.md`**: manual do responsável técnico, em 13 seções: dimensionamento (tempos
   das revisões 4C/4F e relatório 4F.9, disco por mil folhas, recomendação para o piloto);
   instalação do zero na ordem exata (tabela de todas as variáveis do `.env` com as que são
   segredo); atualização de versão; Vault (inicialização de produção à mão com 5 partes e limiar
   3, unseal, procedimento de reinício, rotação pela rota, backup a frio do volume, perda das
   partes, pendências de produção); certificado real no Caddy (ACME ou fornecido) e efeito do
   HSTS; porta direta da API (vazia = porta efêmera em loopback; sobreposição `ports: !reset []`
   para não publicar nada); backup e restauração, expurgo, chaves de período e o que o backup não
   cobre; descarte e rotação; `limpar_dev.py`; monitoramento (`/saude`, `/metricas`, logs, o que
   nunca vai a log); resposta a incidente com fluxo para vazamento, injeção, credencial e disco
   cheio; relatório de uso para o tribunal; checklist da seção 6 dos requisitos item a item; e o
   registro dos ensaios.
2. **Ensaios** executados uma vez (seção "Ensaios" abaixo).
3. **Itens herdados**:
   - `identidade_lida` com `usuario_id` (revisão 7.1-7.9, item 4): `pseudonimizador_do_processo`
     ganhou o parâmetro opcional `usuario_id`, que vai ao evento. Para que o valor chegue, foi
     preciso passá-lo pelos três chamadores: `agente/dossie.py` (`montar_dossie` e o resumo de
     peça), `agente/servico.py` (chat) e `api/rotas/dossie.py` (passa `chat.usuario_id`). São
     alterações de uma linha fora de `contexto.py`, registradas aqui. Testes:
     `tests/agente/test_dossie.py::test_identidade_lida_no_dossie_registra_quem_pediu` (pela rota) e
     `tests/seguranca/test_cifra_banco.py::test_identidade_lida_registra_o_usuario_informado`.
   - Recusa do backup por falta de espaço (item 5): `LUPA_BACKUP_ESTIMATIVA_BYTES` em
     `backup_conteiner.sh` faz uma conferência de espaço com a estimativa forçada **antes** de
     medir banco e bucket (repassada por `backup_comum.sh` e `.ps1`). Teste
     `tests/backup/test_espaco.py` (marcador `backup`, só no host): 1 EB forçado → saída com erro,
     `backup.log` com `RECUSADO`, nenhum `.age`, nenhuma área de trabalho, nenhuma chave criada.
     Passou (1 teste, 2,7 s).
   - `.gitattributes` (`* text=auto`, LF para `sh py yaml yml hcl md ts svelte json`, Caddyfile,
     Dockerfile e `ps1`; binários marcados) e `scripts/preparar_repositorio.md`.
   - `scripts/recifrar_objetos_legado.py` com simulação (padrão) e `--executar`, idempotente,
     conferência de cada objeto regravado; teste `tests/seguranca/test_recifrar_legado.py` (2
     testes: simula/executa/idempotente com objeto cifrado, legado, órfão e chave fora do padrão;
     parada quando a releitura não confere).
4. **README**: seção "Operação" e tabela "Onde cada etapa fica" refeita (etapa, código,
   documentação); frase de abertura atualizada. `docs/sistema/criptografia.md` aponta para o script de
   recifragem. `.env.example`: acréscimo comentado de `LUPA_BACKUP_ESTIMATIVA_BYTES` e nota de
   operação.

#### Recifragem dos objetos legados (desenvolvimento)

Espaço livre antes: 120 GB.

| | Objetos |
| --- | --- |
| Examinados no bucket `lupa-autos` | 377 |
| Já cifrados (pulados) | 29 |
| **Recifrados** | **4** (2 processos, 524.563.585 bytes em claro), 40,6 s |
| Em claro sem DEK (não tocados) | 344 |
| Segunda passada | 0 a recifrar, 33 cifrados (idempotente) |

O revisor contou 50 objetos em claro; a varredura completa achou 348. Classificação feita antes
de executar: os 344 sem DEK pertencem a processos que **não existem mais no banco** (removidos pela
limpeza da 6.10, antes da exclusão criptográfica da 7.7; é o item 2 da revisão 6.10, "objetos
órfãos"). Sem DEK não há como cifrá-los. São dados sintéticos; não os apaguei porque apagar é
irreversível e não estava pedido. Recomendação: apagar os órfãos (prefixos de processos
inexistentes) antes do piloto, com decisão do responsável técnico.

<a id="ensaios-7-10"></a>

#### Ensaios

Todos pela aplicação real (rotas FastAPI, banco, Vault real), em desenvolvimento, com gabinete
`Gabinete E2E ensaio 7.10 ...`, desembargador e assessor sintéticos com MFA e um processo de três
páginas sintéticas. O chat usou o cliente falso roteirizado (`LUPA_AGENTE_CLIENTE=falso`, roteiro
"incidente"). Para a rota de rotação, o administrador do banco de desenvolvimento recebeu senha e
autenticador de teste e, ao fim, foi resetado de novo com `scripts/e2e_preparar.py` (senha
temporária aleatória, como o E2E espera). Os gabinetes do ensaio foram removidos ao fim pelo
mesmo caminho do `limpar_dev.py` (prefixo do ensaio só).

Correção de percurso: a primeira execução importou `tests.conftest`, que força
`LUPA_COFRE_BACKEND=memoria`; a rotação e as DEKs daquela rodada foram para o cofre em memória
(tokens `mem:v2`) e o processo ficou ilegível para a API em execução. Descartei aquela rodada,
reescrevi o roteiro sem o conftest, com conferência de que o cofre é `CofreVault`, e repeti. Os
números abaixo são da rodada válida (token `vault:v2`).

<a id="credencial-7-10"></a>

##### 1. Credencial de assessor comprometida

| Passo | Comando (rota) | Tempo | Resultado |
| --- | --- | --- | --- |
| Preparo | duas sessões do assessor ("legítima" e "atacante") | 0,82 s | ambas abrem o processo |
| 1 | `POST /gabinetes/{id}/rotacionar-chave` (administrador) | 0,020 s | 200, `deks_recifradas: 1`, envelope `vault:v1` → `vault:v2` |
| 2 | `POST /usuarios/{id}/resetar-senha` (desembargador) | 0,072 s | 200, troca obrigatória |
| 3 | `POST /usuarios/{id}/resetar-mfa` (desembargador) | 0,016 s | 200 |
| 4 | conferência | 0,123 s | sessão do atacante 401, sessão legítima 401, login com a senha antiga 401, dossiê do processo 200 depois da rotação |

Total das rotas: 0,233 s. Auditoria (cadeia do gabinete): `chave_rotacionada` (administrador,
objeto `gabinete`), `senha_resetada` e `mfa_resetado` (desembargador, objeto `usuario`),
`login_falha` (assessor, resultado `falha`), `processo_aberto` (desembargador). Não há rota só
para revogar sessões: reset de senha, reset de MFA e desativação revogam (documentado).

##### 2. Incidente de injeção

| Passo | Tempo | Resultado |
| --- | --- | --- |
| Pergunta cujo roteiro devolve "Ignore as instruções anteriores..." | 0,160 s | mensagem `descartada`, processo `em_revisao` |
| `GET /processos/{id}/revisao` e nova pergunta | 0,039 s | em revisão; pergunta recusada (`recusa`) |
| `POST /processos/{id}/liberar-revisao` (desembargador) | 0,026 s | 200, `em_revisao: false` |
| Nova pergunta | 0,032 s | chat responde de novo (`sem_evidencia`, o roteiro padrão) |

Total: 0,258 s. Auditoria: `pergunta_chat`, `chamada_modelo` (resultado `bloqueado`),
`processo_em_revisao` (resultado `bloqueado`, objeto `incidente`), `pergunta_chat`,
`revisao_liberada` (desembargador), `pergunta_chat`, `chamada_modelo` (`ok`). A tentativa de
liberação pelo assessor deu 401 (a sessão dele já tinha sido revogada no ensaio 1), então não
prova a recusa por papel; essa recusa já é coberta pelos testes da 6.8.

##### 3. Reinício do Vault

| Passo | Comando | Tempo | Resultado |
| --- | --- | --- | --- |
| Antes | login + `GET /api/processos/{id}/dossie` pelo proxy | 2,4 s | 200 |
| Reinício | `docker compose restart vault` | 1,3 s | `vault status`: `sealed true` |
| Compose | `docker compose ps vault` | — | `healthy` 6 s depois, **mesmo selado** |
| Selado | mesma chamada | 0,1 s | login 200, dossiê **500** (`CofreError: vault respondeu 503` no log) |
| Unseal | `vault operator unseal` com a chave de `.vault-dev/init.json` (sem eco) | 0,9 s | `sealed false` |
| Depois | mesma chamada; `abrir_dek` no worker | 0,2 s | dossiê 200; worker abre a DEK |

Do reinício à conferência: 15,9 s. API e worker voltaram a decifrar sem serem reiniciados.

Achados do ensaio, registrados no manual: o healthcheck do `vault` aceita selado (o compose mostra
`healthy`) e o `/saude` da API não consulta o Vault; o usuário vê só "erro interno" nas rotas de
processo. Precisa de alerta externo sobre `vault status` (pendência para 8.1; mudar o `/saude` ou o
compose está fora do escopo desta subetapa).

#### Decisões não previstas

- `/saude` e healthcheck do Vault não foram alterados (fora do escopo: `docker-compose.yml` e
  rotas da API); a lacuna está no manual e nas pendências.
- Backup do Vault: o storage é `file`, então o `raft snapshot` comentado no `backup_conteiner.sh`
  não serve. O manual descreve backup a frio do volume `lupa_vault-dados`. Não foi executado
  (exigiria copiar dados de volume para o host, vedado nesta subetapa).
- Prazos de comunicação da LGPD: `requisitos-v1.md` não os fixa (só diz que o fornecedor é o
  controlador). O manual não inventa prazo nem artigo; registra a regra operacional de avisar
  Victor e o desembargador no mesmo dia e deixa a definição para o [plano de resposta a incidentes da 8.2](../conformidade/CONFORMIDADE.md#prazos-incidentes).
- Dimensionamento de disco: originais estimados pelos autos sintéticos (4,7 GB para 3 × 15.647
  folhas); banco medido por página na base de desenvolvimento. O cache de PNG do visualizador não
  foi medido.

#### O que ficou de fora

- Exclusão dos 344 objetos órfãos em claro (decisão do responsável técnico).
- Backup real do Vault e ensaio de restauração do Vault.
- TLS no Vault, auto-unseal, divisão das partes, TLS entre serviços, certificado real: pendências
  de produção documentadas (8.1).
- Revisão 7.1-7.9, item 6 (tela do valor corrigido) e item 8 (leitura dos guias por assessor
  externo): Etapa 8.

#### Espaço em disco

120 a 121 GB livres em todas as conferências (antes da recifragem, dos ensaios, do rebuild e da
verificação). Nenhuma cópia de contêiner para o host; nada gravado em camada de contêiner além do
que a imagem já fazia.

#### Testes

```
docker compose exec api bash scripts/verificar.sh
LUPA_VERIFICAR_BACKUP=1 .venv/Scripts/python -m pytest -m backup tests/backup/test_espaco.py --no-cov -q --confcutdir=tests/backup
```

Saída resumida: ver a seção "Verificação final" abaixo.

#### Verificação final

`docker compose exec api bash scripts/verificar.sh` (imagem reconstruída, Vault destravado),
13 min 39 s, saída 0:

- ruff check e format: sem avisos; mypy --strict: sem erros.
- pytest: **860 passaram**, 3 pulados (inclui os testes de backup, que só rodam no host), 3
  desmarcados; cobertura **98,27%**.
- Ponta a ponta da ingestão: 1 passou. Regressão de injeção: 2 passaram, recall 1,0, falso
  positivo 0.
- Front: carimbo do build ok. Cabeçalhos: ok em 4 rotas.
- Suíte de injeção do agente: 9 passaram; 0 achados suprimidos ou criados, 0 vazamentos.
- No host: `tests/backup/test_espaco.py` 1 passou.

Espaço livre ao fim: 118 GB.

### Revisão 7.10

**Decisões e pendências para Victor antes do piloto**

1. **344 objetos órfãos em claro no storage de desenvolvimento**, de processos sintéticos já removidos do banco. Não há chave para recifrá-los e a exclusão é irreversível, por isso o executor não apagou. Recomendação: apagar antes do piloto; são só dados sintéticos. O script de descarte não os alcança porque não há processo; basta um `mc rm` ou um pequeno script com lista por prefixo.
2. **Vault em produção**: TLS, auto-unseal ou divisão das partes de unseal entre pessoas, backup frio do volume (o Vault usa storage em arquivo, então `raft snapshot` não se aplica). Tudo documentado como pendente para 8.1.
3. **Certificado real no proxy** e porta direta da API não publicada (8.1).
4. **Prazos de comunicação de incidente**: o manual não cita artigos nem prazos porque `requisitos-v1.md` não os fixa; manda avisar Victor e o desembargador no mesmo dia e remete ao [plano de resposta a incidentes da 8.2](../conformidade/CONFORMIDADE.md#prazos-incidentes).
5. Assinatura da decisão do object storage (`docs/decisoes/object-storage.md`).

<a id="balanco-7"></a>

### Balanço ao concluir a etapa 7

| Verificação | Resultado |
| --- | --- |
| Backend | 860 testes; cobertura 98,3%; todos os passos do `verificar.sh` verdes (ver revisão 7.10, §1.1) |
| E2E | 36 de 36 com a cifra ativa |
| Backup | restauração em banco e bucket limpos conferida por hash; recusa por falta de espaço testada |
| Cifra | páginas, evidências, mensagens, identidades e objetos novos cifrados; conferido no banco e no storage; objetos legados de processos existentes recifrados |
| Vault | serviço real no compose com Transit e AppRole; ensaios de rotação, incidente de injeção e reinício com unseal registrados |
| Guias | assessor e desembargador com 11 capturas reais; leitor externo 10 de 10 |
| Operação | `docs/operacao/operacao.md` com instalação, atualização, Vault, certificado, backup, descarte, monitoramento, incidentes, relatório de uso e checklist de segurança |

Incidente de processo: a primeira execução encheu o disco por um backup de teste contra o banco e o bucket principais, derrubando Docker e WSL. Recuperado com autorização do responsável técnico; regras de disco adicionadas aos briefs e ao script de backup (estimativa e recusa). Registrado na revisão 7.1-7.9, §0.

Restam a Etapa 8 (piloto) e as decisões listadas na revisão 7.10, §5: apagar 344 objetos órfãos sintéticos, endurecer o Vault para produção, certificado real, assinatura da decisão do storage, prazos de incidente no [plano de resposta a incidentes](../conformidade/CONFORMIDADE.md#prazos-incidentes). Achado a corrigir em 8.1: healthcheck do Vault e `/saude` não detectam cofre selado.

<a id="etapa-8"></a>

## Etapa 8 — Piloto

<a id="etapa-8-1"></a>

### 8.1 — Ambiente de piloto

Data: 21/10/2026. Ambiente de prova: desenvolvimento (Windows 11, Docker Desktop). Sem servidor
nem domínio reais: a instalação ficou como sequência de comandos com variáveis; o que dependia do
ambiente foi provado no dev. Nenhum dado real, nenhuma cópia de contêiner para o host, sem git.
Disco conferido antes de cada build: 115–116 GB livres o tempo todo (nunca abaixo de 15 GB).
[`docs/conformidade/**`](../conformidade/CONFORMIDADE.md), `front/**` e `src/lupa/migrations/**` não foram tocados; os 344 objetos
órfãos não foram apagados.

#### 1. Correção do achado da 7.10 (cofre selado)

- `docker-compose.yml`, serviço `vault`: healthcheck `["CMD", "vault", "status"]` (sai com 0 só
  destravado, 2 selado, 1 fora). Consequência registrada no compose e no manual: depois de
  recriar ou reiniciar o `vault`, ele fica `unhealthy` e a `api`/`worker` (que dependem dele
  `service_healthy`) esperam o unseal; a ordem passa a ser `up -d vault` → `vault_inicializar` →
  `up -d --wait`.
- `src/lupa/seguranca/cofre.py`: constante `CHAVE_SAUDE = "lupa-saude"`.
- `src/lupa/api/saude.py`: `verificar_cofre` cifra e decifra um valor fixo pela chave
  `lupa-saude` (no cofre em memória, cria a chave); qualquer erro (selado, fora, sem AppRole, sem
  a chave) ou valor diferente → falso.
- `src/lupa/api/rotas/saude.py`: `GET /saude` ganha `"cofre"`; 503 se falhar.
- `vault/politicas/lupa.hcl`: o AppRole só pode `encrypt`/`decrypt` em `lupa-saude` (não cria nem
  apaga). `vault_inicializar.sh`/`.ps1` criam a chave com o token raiz.
- Testes: `tests/api/test_saude.py` (+4: 503 com cofre selado; memória ida e volta; cofre que
  falha ou decifra outra coisa; Vault inalcançável) e ajuste dos existentes.

**Prova no dev** (`docker compose restart vault`, `/saude` pela API, unseal, `/saude` pelo proxy):

```text
== antes: 2026-10-21T23:44:47Z
{"api":"ok","db":"ok","minio":"ok","cofre":"ok"} HTTP 200
Sealed          false
== docker compose restart vault
 Container lupa-vault-1 Started
== depois do reinicio (selado): 2026-10-21T23:45:10Z
Sealed             true
vault status rc=2
503 {"api":"ok","db":"ok","minio":"ok","cofre":"falha"}
api healthy
vault starting
== unseal
vault: unseal ok
== depois do unseal: 2026-10-21T23:45:29Z
{"api":"ok","db":"ok","minio":"ok","cofre":"ok"} HTTP 200
api healthy
vault healthy
```

A `api` só passou a `unhealthy` depois das 5 tentativas do healthcheck (≈50 s); o 503 do
`/saude` é imediato.

#### 2. Perfil de produção (`docker-compose.prod.yml`)

Uso: `docker compose -f docker-compose.yml -f docker-compose.prod.yml ...` (ou
`COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml`). `config -q` válido.

- Portas: `api` e `minio` com `ports: !reset []` (`API_PORTA_HOST` ignorada); `proxy` com
  `!override` só `443→8443` e `80→8080` (IP em `LUPA_PROXY_IP`, padrão `0.0.0.0`). Conferido no
  `config --format json`: só o proxy publica.
- `restart: unless-stopped` e logs `json-file` (`max-size` 10m, `max-file` 5) em todos, por âncora
  `x-comum`; `minio-init` com `restart: "no"`.
- Limites de CPU e memória por serviço (api 2/2g, worker 6/6g, db 2/3g, minio 1/1g, demais
  menores), ajustáveis por variável.
- `read_only`: front, proxy (já eram), redis (+ tmpfs `/data`), backup-agendado, prometheus.
  Não: api/worker (uploads de até 512 MB e temporários em `/tmp`, tmpfs em memória seria pior),
  db, minio, vault (o entrypoint faz `setcap` no binário para o mlock).
- Vault: `cap_add: [IPC_LOCK]`, `vault/producao/lupa.hcl` com `disable_mlock = false`, sem
  `no-new-privileges` (anularia a capability de arquivo). Provado num contêiner descartável:
  `Mlock: supported: true, enabled: true`.
- Volumes `db-dados`, `minio-dados`, `vault-dados`, `caddy-dados`, `prometheus-dados`,
  `grafana-dados` como bind em `${LUPA_DADOS_DIR:-/srv/lupa/dados}/<nome>`.
- `backup-agendado`: definido no compose base (perfil `agendamento`) e ligado sempre no prod
  (`profiles: !reset []`). Imagem do próprio backup (`lupa-backup:local`, bases já fixadas por
  digest/versão), `crond` do BusyBox via `scripts/cron_backup.sh`: diário `fazer` (02:00 UTC) e
  semanal `expurgar` (dom 03:30 UTC), horários em `LUPA_BACKUP_CRON_DIARIO/_EXPURGO`, gravando em
  `LUPA_BACKUP_DIR` e `cron.log`. Não usei ofelia/supercronic: a imagem já tem `crond`, e evita
  dar o socket do Docker a um agendador. Prova (agenda a cada minuto, estimativa forçada para
  recusar, sem tocar no banco grande):

```text
cron_backup: agenda diario='* * * * *' expurgo='30 3 * * 0'
--- cron.log
backup: fazer banco=lupa bucket=lupa-autos estimativa_forcada=1 estimativa_bytes=1000000000000000 livre_bytes=124241321984 exigido_bytes=2000002147483648
backup: fazer banco=lupa bucket=lupa-autos estimativa_forcada=1 RECUSADO: espaco livre insuficiente no destino
backup: espaco livre insuficiente: livre=124241321984 exigido=2000002147483648 (2 x 1000000000000000 + 2 GB)
healthy
```

#### 3. Certificado e domínio

`proxy/Caddyfile` virou um snippet comum `(lupa_site)` (cabeçalhos e rotas) mais
`import modos/{$LUPA_TLS_MODO:interno}.caddy`; o compose monta a pasta `proxy/` inteira.
Globais: `http_port 8080`, `https_port 8443` (o desafio HTTP-01 entra pela 80 do host).

| Modo | Arquivo | Endereço | TLS | HSTS |
| --- | --- | --- | --- | --- |
| `interno` (padrão; dev) | `modos/interno.caddy` | `localhost:8443, proxy:8443`, `tls internal` | 1.2+1.3 | sim (ver abaixo) |
| `acme` (padrão do prod) | `modos/acme.caddy` | `{$LUPA_DOMINIO}`, `tls {$LUPA_ACME_EMAIL}` | só 1.3 | sim |
| `fornecido` | `modos/fornecido.caddy` | `{$LUPA_DOMINIO}`, `tls /certs/lupa.crt /certs/lupa.key` (de `LUPA_TLS_CERT`/`LUPA_TLS_CHAVE`) | só 1.3 | sim |

**Desvio registrado — HSTS em dev:** o pedido era "HSTS só com certificado real", mas o E2E
`front/e2e/testes/seguranca.spec.ts` (que não posso editar) e a varredura exigem o cabeçalho em
dev. Mantive-o no modo `interno`; o navegador ignora HSTS recebido com certificado não confiável,
então não fixa `localhost`. Para tirar, basta apagar a linha em `modos/interno.caddy` e afrouxar
os dois testes numa etapa que possa mexer no front.

`scripts/validar_caddyfile.sh` (contêiner `caddy:2.8.4-alpine`, certificado descartável gerado
dentro do contêiner para o modo fornecido): `Valid configuration` nos três; um modo inexistente
sai com 1. A varredura de cabeçalhos do `verificar.sh` continua `ok em 4 rotas` e o E2E passa.

<a id="vault-8-1"></a>

#### 4. Vault para produção

- `scripts/vault_inicializar.sh` com `LUPA_AMBIENTE=producao`: `init -key-shares=3
  -key-threshold=2`; cada parte mostrada uma vez, numa tela limpa, para um portador; nada em disco;
  unseal pedindo duas partes sem eco; configuração com o token raiz só em memória e **revogação do
  token raiz** no fim; `--so-unseal` para reinícios. Em dev continua 1/1 com `.vault-dev/init.json`.
  O `.ps1` recusa produção e aponta para o `.sh`. O modo produção **não foi executado** (exige
  terminal interativo e três pessoas); a sintaxe foi conferida e os caminhos de dev rodaram.
- **Decisão: sem TLS entre API/worker e Vault no piloto** (registrada em `docs/operacao/operacao.md` 4.6 e
  no `vault/producao/lupa.hcl`). Rede interna de um único host, sem porta publicada; quem enxerga
  a ponte do Docker já é root e lê o `.env` e a memória; a CA interna traria renovação e mais um
  ponto de falha no reinício sem ganho real. Reavaliar se o Vault sair do host.
- Backup do Vault: o serviço de backup monta `vault-dados` só leitura e `backup_conteiner.sh fazer`
  põe `vault.tar` no `.age` do dia (com entrada no manifesto); `restaurar` o deixa em
  `LUPA_BACKUP_DIR/vault-<arquivo>.tar` para a reposição manual (passos em `operacao.md` 4.4).
  `scripts/backup.sh --vault-frio` para cópia fria (para e sobe o vault, que volta selado).
  **Teste de restauração no dev** (banco `lupa_bkp81` de 3 linhas e bucket `lupa-bkp81` de 1
  objeto, para não fazer backup do banco e do bucket grandes; tudo apagado ao fim): backup →
  restauração → volume novo com o `vault.tar` → Vault descartável → unseal com a chave de dev →
  as 44 chaves Transit presentes, iguais às do Vault em uso:

```text
backup: manifesto conferido
backup: restaurando banco em lupa_bkp81_r
backup: restaurando objetos em lupa-bkp81-r
backup: armazenamento do vault em vault-lupa-2026-10-20261021T235335Z.tar (reposicao manual)
backup: restaurado lupa-2026-10-20261021T235335Z.tar.age em banco=lupa_bkp81_r bucket=lupa-bkp81-r
-rw-r--r-- 1 vh15f 197609 822272 Oct 21 20:53 vault-lupa-2026-10-20261021T235335Z.tar
auth
core
logical
sys
Sealed          false
Total Shares    1
Keys
----
lupa-gabinete-1c81f1f2-78d3-4695-8e33-8176ac7b892f
lupa-gabinete-1c81f1f2-78d3-4695-8e33-8176ac7b892f-identidades
lupa-gabinete-239c8e47-d3d8-4adf-98fc-83d5d50ff7f4
chaves no vault restaurado: 44
chaves no vault em uso:      44
limpeza: conteiner, volume e tar extraido removidos
banco restaurado: 3 linhas
```

O arquivo de teste `lupa-2026-10-20261021T235335Z.tar.age` (830 KB) ficou em `.backups/`.

#### 5. Monitoramento

- Rota nova `GET /metricas/servico` (em `src/lupa/api/rotas/saude.py`): `Authorization: Bearer`
  comparado em tempo constante com `LUPA_METRICAS_TOKEN` (`config.py`); sem token configurado, 404;
  errado, 401. Motivo: `GET /metricas` exige sessão de administrador com TOTP, que o Prometheus
  não consegue manter, e `rotas/ingestao.py` estava fora do escopo. Devolve as métricas de
  ingestão de sempre mais `lupa_cofre_ok`, `lupa_modelo_chamadas_24h`,
  `lupa_modelo_tokens_24h{tipo}` e `lupa_auditoria_eventos_24h{acao}` (só contagens). Testes em
  `tests/api/test_metricas_servico.py` (3).
- `docker-compose.yml`, perfil `monitoramento`: `prometheus` (v3.5.0 por digest, `read_only`,
  token por `secrets:` de `LUPA_METRICAS_TOKEN_ARQUIVO`, padrão `.segredos/metricas_token`) e
  `grafana` (12.1.1 por digest, senha do admin por `GF_SECURITY_ADMIN_PASSWORD__FILE`, sem
  cadastro nem anônimo, sem telemetria). Portas `127.0.0.1:9090` e `127.0.0.1:3000`.
- `monitoramento/prometheus/prometheus.yml` e `regras.yml` (`promtool check rules`: 4 regras):
  `LupaFilaParada` (> 30 min), `LupaFalhasDeIngestao` (> 3 em 1 h), `LupaCofreSelado`,
  `LupaApiFora`. Sem Alertmanager (notificação é decisão do responsável).
- Grafana provisionado (`monitoramento/grafana/`): fonte Prometheus e painel **Lupa — piloto**
  (cofre, idade da fila, chamadas e tokens do modelo, jobs por estado, falhas por motivo, eventos
  de auditoria por ação). Prova: alvo `up`, `lupa_cofre_ok 1`, regras `inactive`; captura em
  `docs/imagens/grafana.png` com os dados sintéticos do dev, tirada por
  `monitoramento/capturar_painel.cjs` na imagem do E2E (a senha do Grafana é lida do arquivo de
  segredo dentro do contêiner, sem passar pelo terminal).
- `.segredos/` (token e senha do Grafana) no `.gitignore`.

<a id="conferencia-8-1"></a>

#### 6. Instalação e conferência

- `scripts/instalar_piloto.sh` (produção; `--dev`) e `scripts/instalar_piloto.ps1` (Windows, só
  dev): pré-requisitos e disco (para abaixo de 15 GB) → `.env` (copia o exemplo, pergunta
  domínio/modo do certificado/pastas, gera senhas e tokens aleatórios sem mostrar, zera
  `API_PORTA_HOST` no prod) → pastas com o dono de cada imagem (`sudo install -d`) e
  `.segredos/` → build → Vault (sobe só ele, inicializa) → `up --wait` → `alembic upgrade head` →
  usuário restrito → admin → oferece apagar `LUPA_ADMIN_SENHA` → `conferir_piloto.py`. Idempotente
  (só completa o que falta); confirmação antes de mexer num `.env` existente, criar pastas e
  apagar a senha. **Não foi executado de ponta a ponta** (o dev já está instalado e o fluxo de
  produção precisa de terminal interativo e de `sudo`); sintaxe conferida (`bash -n`, parser do
  PowerShell) e cada comando que ele encadeia rodou nesta etapa.
- `scripts/conferir_piloto.py`: lê `docker compose ps/exec`, `/api/saude`, apertos de mão TLS 1.2
  e 1.3 e contagens no banco (páginas e identidades no formato cifrado); imprime cada item da
  seção 12 como atendido/pendente/manual, mais três extras. Saída no dev (os pendentes 2, 13, 14 e
  E2 são do perfil de desenvolvimento; o 3 é a decisão de não usar TLS interno):

```text
[atendido]  1. Infraestrutura própria, MinIO local compatível com S3: 8 serviços healthy; MinIO local fixado por digest (assinatura da imagem: docs/decisoes/object-storage.md)
[pendente]  2. TLS 1.3 entre navegador e servidor: TLS 1.3 ok, mas TLS 1.2 aceito (modo `interno` de dev; acme e fornecido exigem 1.3)
[pendente]  3. TLS entre serviços: decisão 8.1: redes internas de um host só, sem TLS entre contêineres (operacao.md 4.6)
[atendido]  4. Criptografia em repouso com chaves no Vault próprio: backend vault; /api/saude cofre=ok (cifra e decifra com lupa-saude)
[atendido]  5. Texto extraído e índices também cifrados: 306 páginas, todas com texto no formato cifrado (lupa1:)
[atendido]  6. Arquivo cifrado antes de qualquer parser: por desenho (7.4) e testes de tests/seguranca; worker sem rede externa
[atendido]  7. Exclusão pela destruição da chave: 7.7; backups guardam o envelope por até 30 dias
[manual  ]  8. Objetos legados em claro: 344 órfãos em claro mantidos por decisão do responsável técnico
[atendido]  9. Só processos públicos; sigilo identificado e bloqueado: sigiloso recebe 403 na ingestão (testes da Etapa 4A)
[atendido] 10. Pseudonimização; tabela de identidades separada e cifrada: 10 identidades, todas cifradas no Transit; leitura auditada
[manual  ] 11. Contrato do fornecedor do modelo veda treino: conferir os termos da API do modelo (decisão de Victor)
[atendido] 12. Nenhum dado de autos usado para treinar modelo: não há treino nem ajuste no sistema
[pendente] 13. Vault em produção (partes, unseal, reinício): destravado e healthcheck exige Sealed false, mas partes=1 limiar=1 (dev; produção: 3 partes, limiar 2)
[pendente] 14. Porta direta da API e console do MinIO fechados: publicadas: api:127.0.0.1:18000, minio:127.0.0.1:9001 (o perfil prod não publica)
[atendido] E1. /api/saude com componente cofre: {"api": "ok", "db": "ok", "minio": "ok", "cofre": "ok"}
[pendente] E2. backup agendado: backup-agendado fora (o perfil prod o liga)
[atendido] E3. monitoramento: prometheus e grafana healthy

resumo: 10 atendidos, 5 pendentes, 2 manuais
```

#### 7. Documentação

`docs/operacao/operacao.md`: 2.1 (variáveis novas), 2.2 (atalho do instalador e ordem nova com o Vault
primeiro), 3 (atualização com o Vault selado), 4 (intro), 4.1 (produção pelo script, 3/2), 4.2
(selado agora detectado; `--so-unseal`), 4.4 (Vault dentro do `.age`, restauração testada), 4.6
(tabela de decisões, TLS interno), 5.1 (três modos), 5.3 (portas), 5.4 (perfil prod), 6 (backup
agendado), 9 (Prometheus/Grafana/alertas, `/saude` com cofre), 12 (checklist atualizado e ligado
ao `conferir_piloto.py`). `README.md` (subida nova, seção "Ambiente de piloto"), `.env.example`
(bloco 8.1), `.gitignore` (`.segredos/`).

#### 8. Verificação final

| Verificação | Resultado |
| --- | --- |
| `docker compose up -d --build --wait` (perfil padrão) | 8 serviços `healthy` (+ prometheus e grafana do perfil `monitoramento`, deixados no ar) |
| `docker compose -f docker-compose.yml -f docker-compose.prod.yml config -q` | válido |
| `docker compose exec api bash scripts/verificar.sh` | ok: ruff, format, mypy strict (274 arquivos), **867 passed**, 3 skipped, cobertura **98,28%**; ponta a ponta 1, injeção 2, front (carimbo), cabeçalhos ok em 4 rotas, agente 9 |
| `bash front/scripts/e2e.sh` | **36 passed** |
| `bash scripts/validar_caddyfile.sh` | três modos válidos |
| `promtool check rules` | 4 regras |

Testes de backend: 860 → 867 (+4 em `test_saude.py`, +3 em `test_metricas_servico.py`).

#### 9. Fora do escopo ou pendente

- Execução real em servidor: domínio, ACME, certificado fornecido, `instalar_piloto.sh` de ponta a
  ponta, Vault 3/2 com três pessoas e o perfil prod com `LUPA_DADOS_DIR` em outro disco. Só
  validados por `config -q`, `caddy validate`, `bash -n` e um Vault descartável com mlock.
- TLS 1.2 desligado só nos modos `acme`/`fornecido`; em dev continua aceito.
- HSTS mantido em dev (desvio da seção 3, por causa do E2E que não posso editar).
- TLS entre serviços: não adotado (decisão da seção 4).
- Auto-unseal (KMS/HSM): não há KMS; reinício exige dois portadores.
- Notificação de alertas (Alertmanager, e-mail): não configurada.
- Cópia do Vault no backup diário é a quente (escritas raras); a fria fica em `--vault-frio`.
- Itens manuais do checklist: 8 (344 órfãos, decisão do responsável) e 11 (termos do fornecedor
  do modelo).
- `ruff` no host acusa 5 linhas longas em scripts antigos (`medir_extracao.py` etc.), fora do
  `verificar.sh` (que cobre `src` e `tests`); não mexi.

<a id="etapa-8-2"></a>

### 8.2 — Conformidade do piloto

**Para o advogado decidir**

1. Base legal para dados dos autos tratados por particular em apoio a magistrado (art. 7º, VI / 11, II, "d" vs. legítimo interesse) e tratamento de dados de natureza penal.
2. Hipótese legal da transferência internacional ao fornecedor do modelo.
3. Encarregado: indicação ou dispensa; canal e forma de publicidade do aviso aos titulares.
4. Prazo de retenção da auditoria.
5. Forma do aceite dos termos; responsabilidade por indisponibilidade; remuneração do piloto.
6. Aplicação a uso privado do registro previsto no art. 19, § 6º, e da capacitação do § 3º, I.
7. Existência de regulamento do TJGO para o § 7º e se o modelo de relatório o atende.
8. Critério de "risco ou dano relevante" e meio de comunicar titulares que não interagem com o sistema; conferir se a Res. CD/ANPD 15/2024 sofreu alteração.

**Não confirmado**

- Termos atuais da API da Anthropic (treino, retenção, local de processamento): não consultados; ficam no [item 6 do checklist](../conformidade/CONFORMIDADE.md#checklist-6).
- Se a pseudonimização cobre nomes de vítimas e testemunhas além do réu: registrado como verificação técnica na [Parte B do aviso](../conformidade/CONFORMIDADE.md#pessoas-citadas-nos-autos).
- Os PDFs de pesquisa da raiz não foram necessários para os fundamentos citados.

O [balanço de conformidade](#conformidade-geral) registra o fechamento da revisão 8.2 e as decisões antes do primeiro processo real.

<a id="etapa-8-6"></a>

### 8.6 — Métricas do piloto (previstas)

O gabinete ainda precisa registrar as medições com os gabaritos reais e confirmar os calendários oficiais do TJGO. Essa subetapa integra a execução humana prevista para 8.3 a 8.10. Roteiro do piloto (removido; ver histórico do Git)

## Conformidade geral

21 de outubro de 2026 · revisor · Etapas 0 a 7 e 8.1 a 8.2. A última atualização registra o fim do trabalho previsto para os agentes.

### Fechamento após 8.1 e 8.2

| Verificação | Resultado |
| --- | --- |
| Backend | 867 testes; cobertura 98,3% (ver revisão 8.1, §1.1) |
| E2E | 36 de 36 |
| Cofre selado | detectado pelo healthcheck do Vault e por `/saude` (503), provado pelo revisor |
| Perfil de produção | compose válido; só o proxy publica portas; backup e expurgo agendados; monitoramento em loopback com 4 alertas |
| Certificado | três modos validados; ACME e fornecido só TLS 1.3 com HSTS |
| Conformidade | [seis minutas para revisão de advogado](../conformidade/CONFORMIDADE.md), com fundamentos confirmados na fonte e itens abertos listados |
| Checklist de segurança no dev (`conferir_piloto.py`) | 10 atendidos, 5 pendentes por serem de produção, 2 manuais (objetos órfãos, termos do fornecedor do modelo) |

**Estado do projeto:** a primeira versão está implementada, testada e documentada nas Etapas 0 a 7, com ambiente de piloto preparado (8.1) e conformidade minutada (8.2). As subetapas 8.3 a 8.10 são execução humana com o gabinete: usuários reais, processo do Projudi, gabarito, uso acompanhado, revisão de segurança externa, relatório e decisão de continuidade.

**Decisões do responsável técnico antes do primeiro processo real** (consolidadas de todas as revisões; também no [checklist antes do primeiro processo real](../conformidade/CONFORMIDADE.md#checklist-piloto)):

1. Pseudonimização de vítimas e testemunhas: estender (recomendado) ou aceitar a limitação com registro no [aviso de tratamento](../conformidade/CONFORMIDADE.md#pessoas-citadas-nos-autos) (revisão 8.2, §3).
2. Chave da API da Anthropic, smoke test real do agente, e leitura dos termos vigentes quanto a treinamento e retenção.
3. Assinatura da decisão do object storage.
4. Apagar os 344 objetos sintéticos órfãos em claro no storage de desenvolvimento.
5. Vault em produção com três pessoas, certificado real, perfil de produção num servidor de verdade.
6. Revisão das [minutas](../conformidade/CONFORMIDADE.md) por advogado e [aceite dos termos](../conformidade/CONFORMIDADE.md#aceite-dos-termos) pelos usuários.
7. Confirmação dos dados jurídicos pelo gabinete: calendários, prazos, tabela do art. 109, tipos penais, regras de borda.
8. Conta na MaxMind para geolocalização por IP (opcional).

O roteiro do piloto (removido; ver histórico do Git) detalhava a execução humana das subetapas 8.3 a 8.10. Os roteiros originais das Etapas 4 a 8 estão no histórico do Git.

### Verificações anteriores

A base das tabelas a seguir é o fechamento da ingestão, até a 4F. Os balanços posteriores registram a [Etapa 5 e o início da interface](#balanco-5), a [interface completa](#balanco-6) e a [criptografia, o backup, os guias e a operação](#balanco-7).

#### Estado verificado ao fim da 4F

Última verificação completa, com imagem reconstruída do zero:

| Verificação | Resultado |
| --- | --- |
| ruff check e ruff format | sem avisos, 204 arquivos |
| mypy --strict | sem erros, 204 arquivos |
| pytest | 697 passaram, 1 pulado, 1 desmarcado (carga), cobertura 98,72% |
| Ponta a ponta da ingestão (integração) | passou |
| Regressão de injeção sobre o corpus | recall 100% (16/16), falso positivo 0% (0/196) |
| Banco de desenvolvimento | migração 0006 (head) |
| Stack do compose | api, db, minio, redis, worker saudáveis; nenhum contêiner como root; worker sem saída de rede |

Evolução da suíte: 18 testes na Etapa 0, 46 na 1, 117 na 2, 210 na 3, 476 em 4A/4B, 551 em 4C, 588 em 4D, 616 em 4E, 697 em 4F.

#### Requisitos da primeira versão ao fim da 4F

| Requisito (`requisitos-v1.md`) | Situação | Onde |
| --- | --- | --- |
| Nenhum fato sem evidência (página, trecho, hash) | atendido, imposto no pydantic e no banco por trigger; 0 fatos sem evidência nos 30 arquivos | Etapas 1, 4F |
| Validações determinísticas com todos os valores e página de cada dado | atendido; alerta conclusivo com datas, prazo, base legal, feriados, marcos | Etapa 2 |
| Explicações por template, nunca por modelo | atendido, com testes de frase inteira | Etapa 2 |
| Usuário e senha sem e-mail, MFA obrigatório, reset manual | atendido | Etapa 3 |
| Três papéis com autorização no servidor; 404 fora do gabinete | atendido; matriz como dados; RLS forçada no banco | Etapas 1, 3 |
| Admin vê tudo e o acesso a conteúdo fica destacado | atendido (`admin_acesso_conteudo`) | Etapa 3 |
| Auditoria de tudo, com IP e localização, consulta rápida, append-only | atendido; cadeia de hash, 3 ms em 1 milhão de eventos; geolocalização depende da base MaxMind | Etapa 3 |
| Logs nunca com conteúdo de autos | atendido, com teste de sentinela no worker e filtro no logger | Etapas 0, 3, 4A |
| Pipeline determinística sem modelo de linguagem | atendido | Etapa 4 |
| Funciona no pior caso e diagnostica caso a caso | atendido: 30/30 diagnósticos; fronteiras 100% sem índice | Etapas 4C, 4E |
| Controles de injeção na ingestão como flags, sem bloquear | atendido | Etapa 4D |
| Pseudonimização de réus nos derivados | atendido; nome só em `reu_identidade` | Etapa 4F |
| Só processos públicos na primeira versão | atendido: sigiloso recebe 403 na ingestão | Etapa 4A |
| Parsers em sandbox sem rede e sem credenciais | atendido | Etapa 4A |
| TLS agora, criptografia em repouso depois | pendente por desenho (Etapa 7) | — |
| Chat e agente | não iniciado (Etapa 5) | — |
| Interface web | não iniciado (Etapa 6) | — |

#### Métricas de qualidade da ingestão (dez processos sintéticos, 15.647 páginas, 2.825 peças)

| Medida | Resultado | Meta |
| --- | --- | --- |
| Diagnóstico do contêiner | 30/30 | 30/30 |
| Roteador: falso negativo perigoso | 0 de 4.699 | < 1% |
| Texto nativo igual ao gabarito | 10.718/10.718 | — |
| OCR, CER leve / média / forte | 1,65% / 2,12% / 7,58% | 3% / 5% / 15% |
| Fronteira de peça, precisão e recall (sem índice) | 100% / 100% | ≥ 95% |
| Tipo de peça | 100% | ≥ 95% |
| Origem da peça | 99,6% | medir |
| Data da peça | 98,8%, nenhuma inventada | medir |
| Eventos, precisão / recall | 99,3% / 98,0% | — |
| Datas extraídas, precisão | 99,26% a 99,5% | ≥ 99% |
| Fatos sem evidência | 0 | 0 |
| Achados iguais ao esperado | 86,7% (90% no resultado); divergências só por OCR forte, nenhuma conclusão falsa | — |
| Tempo por mil páginas | 35,8 s nativo; 912 s digitalizado | registrar |

#### Correções obrigatórias identificadas antes do piloto

Registradas nas revisões, não bloqueantes para as próximas etapas:

1. Auditoria automática de leitura gravada depois da resposta (revisão 3, §6.1). Gravar na transação da requisição. Etapa 6.
2. Bloqueio de login por nome permite negação de serviço (revisão 3, §6.2). Rate limit por IP e bloqueio progressivo. Etapa 6.
3. Repetir o ponta a ponta com OCR real dos dez processos num worker dimensionado (revisão 4F, §3).
4. Limpar os gabinetes sintéticos do banco de desenvolvimento (revisão 4F, §6.4).

O [balanço da etapa 5 e da 6.1 à 6.3](#balanco-5) registra a entrega dos itens 1 e 2. O [balanço da etapa 6](#balanco-6) registra a limpeza do item 4. Para o item 3, a [4F.9](#etapa-4f-9) especifica os processos que passaram por OCR real e os que usaram páginas do volume.

#### Decisões pendentes de Victor ao fim da 4F

| Decisão | Contexto | Prazo |
| --- | --- | --- |
| Object storage | MinIO não é mais mantido; fork `pgsty/minio` fixado por hash em uso. Alternativas: Chainguard, Garage, RustFS. O código só fala S3 | antes de 7.1 |
| Base GeoLite2 | conta gratuita na MaxMind; sem ela a localização fica `desconhecida` | antes do piloto |
| Dimensionamento do worker | 1 worker, 12 CPUs, 4 lotes de 8 páginas: 15 minutos por mil páginas digitalizadas | antes do piloto |
| Pasta `.sinteticos` no OneDrive | 4,7 GB sincronizando; excluir da sincronização ou mover com `LUPA_SINTETICOS_DIR` | quando quiser |
| Dados jurídicos a confirmar pelo gabinete | calendários (`feriados`, `suspensoes`), `prazos_recursos`, `prescricao_art109`, `tipos_penais`, `eventos.yaml`; regras de borda listadas em `docs/sistema/validacoes.md` | antes do piloto |
| Valores reais das variáveis de produção | `LUPA_DB_*`, `LUPA_ADMIN_*`, chaves do MinIO | ambiente do piloto |

#### Limitações declaradas e aceitas nessa revisão

- Prescrição após a sentença usa a pena em abstrato (nunca gera alarme falso; pode deixar de apontar). Pena aplicada não é extraída. Próxima rodada do catálogo.
- Súmula 310 do STF, prazos especiais, pronúncia e acórdão como marcos, causas suspensivas: não aplicados; documentados no guia.
- Assinatura digital conferida só pela estrutura, sem validação criptográfica.
- Texto girado e fundo não branco não são tratados como ocultos.
- Detecção de idioma por heurística de palavras funcionais, só para parágrafos com 8 palavras ou mais.
- `bbox` da evidência não gravado; o visualizador da Etapa 6 deriva dos blocos da página.
- Calibração com o Projudi espera o arquivo real; roteiro e script prontos.

#### Incidentes de processo e regras adotadas

- Um agente copiou arquivos do contêiner para o host e sobrescreveu por dois minutos o trabalho de outro (Etapa 3). Regra desde então: fluxo só host → contêiner. Cumprida nas etapas seguintes.
- Dois bugs de etapas anteriores foram encontrados por etapas seguintes graças ao gabarito sintético: página sem conteúdo mandando o PDF à quarentena (4A, achado na 4C) e comparação de cor sem máscara de alfa (4C, achado na 4D). Ambos corrigidos na origem com teste.

<a id="divergencias"></a>

### Divergências entre registros

- **Integração das validações.** Na Etapa 2, o executor considerou suficiente trocar o import. O revisor identificou diferenças de tipos (`UUID`, tuplas e datas em JSON) e campos obrigatórios de `Achado`. A tarefa passou a incluir conversões nos dois sentidos e um teste de ida e volta. [Revisão 2](#etapa-2) · [Adaptador da 4A.1](#etapa-4a-1)
- **Rede do parser.** A matriz de conformidade registra “parsers em sandbox sem rede e sem credenciais”. A 4A.4 descreve um filho sem credenciais que compartilha a rede interna do worker. O isolamento de rede do filho no kernel, seccomp e namespaces ficaram fora da entrega. [Sandbox da 4A.4](#etapa-4a-4)
- **Datas lidas por OCR.** A 4C.6 previa que uma data mal lida seria descartada por falta de correspondência literal. Na 4F.9, duas leituras erradas de `semente_04` (`2017 → 2020` e `02 → 12`) passaram pela verificação porque o próprio texto extraído continha os dígitos trocados. Os dois erros se repetiram nos três cenários. [Previsão da 4C.6](#etapa-4c-6) · [Validação da 4F.4](#etapa-4f-4) · [Medição da 4F.9](#etapa-4f-9)
- **Diagnóstico de ZIP.** A 4C.1 remeteu o agrupamento de entradas em um filho à 4F.8. A revisão 4C apontou a investigação do tempo de leitura já para a 4E. A documentação da 4E.0 registra que as entradas passaram a ser inspecionadas em grupos de 32 por filho, com nova inspeção individual em caso de falha. A 4F.8 manteve o cache pelo hash do arquivo enviado. [4C.1 e revisão 4C](#etapa-4c) · [Diagnóstico implementado na 4E.0](../sistema/ingestao.md#diagnóstico-de-zip-4e0) · [Cache da 4F.8](#etapa-4f-8)
- **Prazo para decidir o object storage.** A revisão 0 pediu decisão antes da primeira gravação de objetos na Etapa 4. O balanço da ingestão passou o prazo para antes da 7.1. A 7.1 e o fechamento da 8.2 ainda registram a assinatura do responsável como pendente. [Revisão 0](#etapa-0) · [Decisão da 7.1](#etapa-7-1) · [Conformidade geral](#conformidade-geral)
- **Cifra das identidades.** A 4F.5 remete a cifra de `reu_identidade` à Etapa 1. A Etapa 1 registrou apenas a referência à chave do gabinete. A conferência da 8.1 encontrou dez identidades cifradas no Transit. [Esquemas da Etapa 1](#etapa-1) · [Pseudonimização na 4F.5](#etapa-4f-5) · [Conferência da 8.1](#etapa-8-1)
- **Objetos legados em claro.** A 7.4 previa leitura de legado e reenvio ou descarte. Na 7.10, a revisão contou 50 objetos em claro e a varredura completa encontrou 348. Quatro foram recifrados. Os outros 344 eram órfãos de processos sintéticos já removidos do banco. A saída da 8.1 diz que foram mantidos “por decisão do responsável técnico”, mas a revisão 7.10 e o fechamento da 8.2 ainda listam a exclusão como decisão a tomar. A decisão posterior à v1 passou a recusar dados em claro e prevê recriar o bucket de desenvolvimento. [7.4](#etapa-7-4) · [Varredura da 7.10](#etapa-7-10) · [Conferência da 8.1](#etapa-8-1) · [Decisões posteriores à v1](../decisoes/registro.md#decisões-posteriores-à-v1)
- **Leitura dos guias.** O balanço da 7 registra “leitor externo 10 de 10”. A 7.9 e a 7.10 mantêm pendente a leitura por um assessor humano de fora do projeto. O resultado do leitor externo não identifica essa pessoa como assessor. [Guias da 7.9](#etapa-7-9) · [Revisão 7.10](#etapa-7-10) · [Balanço da etapa 7](#balanco-7)
- **Partes do Vault.** O manual descrito na 7.10 previa cinco partes e limiar de três para produção. O instalador da 8.1 passou a prever três partes e limiar de duas. O ensaio foi em desenvolvimento, com configuração 1/1. O procedimento 3/2 ainda dependia de três pessoas e de um servidor real. [Operação na 7.10](#etapa-7-10) · [Perfil de produção da 8.1](#etapa-8-1)
- **TLS interno e checklist.** A 7.10 deixou TLS entre serviços como pendência de produção. A 8.1 decidiu operar sem TLS entre API/worker e Vault no piloto de host único e reavaliar se o Vault mudar de host. O fechamento atribui as cinco pendências do checklist ao ambiente de desenvolvimento. A saída detalhada da 8.1 atribui quatro ao perfil de desenvolvimento (2, 13, 14 e E2) e uma à decisão sobre TLS (item 3). [7.10](#etapa-7-10) · [Decisão e saída da 8.1](#etapa-8-1) · [Fechamento](#conformidade-geral)
- **HSTS em desenvolvimento.** O pedido da 8.1 previa HSTS apenas com certificado real. A implementação manteve o cabeçalho também no modo `interno` para atender ao E2E e à varredura. O relatório registra que o navegador ignora HSTS recebido com certificado não confiável. [Certificado e domínio na 8.1](#etapa-8-1)

**Mudanças confirmadas em etapas posteriores**

- A 4A.3 previa retorno manual de jobs `falho` para `recebido`. A 4C.9 passou a tentar de novo por motivo, com limite para falhas de tempo e de parser. [Fila na 4A.3](#etapa-4a-3) · [Retentativas na 4C.9](#etapa-4c-9)
- Na 7.6, `identidade_lida` não recebia o ator. Na 7.8, a recusa de backup por falta de espaço só tinha sido conferida por leitura e log. A 7.10 levou o `usuario_id` aos três chamadores e testou a recusa com estimativa forçada de 1 EB. [Identidades na 7.6](#etapa-7-6) · [Backup na 7.8](#etapa-7-8) · [Testes na 7.10](#etapa-7-10)
- Na 7.10, o Vault aparecia `healthy` mesmo selado, o dossiê respondia 500 e o backup do Vault ainda não tinha ensaio de restauração. A 8.1 passou a devolver 503 em `/saude` com o cofre selado e verificou as mesmas 44 chaves Transit após restaurar o backup em desenvolvimento. [Ensaio da 7.10](#ensaios-7-10) · [Provas da 8.1](#etapa-8-1)
