# Lupa — Registro de decisões

Todas as decisões tomadas no projeto num lugar só. As decisões tomadas depois da Etapa 8 ficam em [seção própria](#decisões-posteriores-à-v1), no fim, dizendo o que substituem. Fora isso, este arquivo junta duas fontes:

- as decisões que cada executor tomou sem estarem no roteiro, copiadas dos relatórios de etapa. Os 19 relatórios citados pelo código e pelos manuais estão no [histórico por etapa](../etapas/ETAPAS.md#etapas-e-pendencias); os outros 78 estão no histórico do Git (commit `58e9774`);
- as decisões dos executores que os revisores endossaram, e o resultado de cada revisão. As revisões foram removidas do repositório; o texto original está no histórico do Git (commit `54219a2`, pasta `docs/etapas/`).

Decisões de produto estão em `docs/especificacao/requisitos-v1.md` e não são repetidas aqui. A decisão do object storage tem documento próprio: [object-storage.md](object-storage.md).

O que ficou de fora, as limitações e os riscos de cada etapa estão no [histórico por etapa](../etapas/ETAPAS.md#etapas-e-pendencias).

As pendências (o que ainda falta decidir ou fazer) estão em [`docs/piloto/pendencias.md`](../piloto/pendencias.md).

## Mantido assim no desenvolvimento, por decisão

TLS 1.2 aceito no modo interno; portas da API e do console do object storage em loopback; Vault com uma parte; backup agendado só no perfil de produção.

## Decisões tomadas na execução, por etapa

Extraídas das seções de decisão de cada relatório de etapa e das decisões endossadas nas revisões. A maior parte dos relatórios e todas as revisões foram removidas do repositório; o texto original está no histórico do Git (relatórios no commit `58e9774`, revisões no `54219a2`). Texto mantido como foi escrito na época.

### Etapa 0 — Esqueleto do projeto

#### 0 — Esqueleto do projeto

1. **pip + `requirements.txt` com hashes** (não há `uv` na máquina). Gerados por `pip-compile
   --generate-hashes` a partir de `requirements.in` e `requirements-dev.in`; o `Dockerfile` instala
   com `--require-hashes`. Versões espelhadas no `pyproject.toml`.
2. **Imagem do MinIO**: `minio/minio` e `quay.io/minio/*` não estão mais disponíveis publicamente
   (pull negado). Usei o fork comunitário `pgsty/minio` fixado por digest
   (`sha256:b6bfe723…2372`, MinIO RELEASE.2026-08-04), que inclui `mc` e serve também ao
   `minio-init`. Recomendo o revisor/arquiteto validar a fonte ou trocar por imagem interna.
3. `GET /saude` responde **503** com `"falha"` no componente quando banco ou MinIO não respondem
   (o plano só especificava o caso 200). O healthcheck da `api` usa a própria `/saude`.
4. Verificação do MinIO via `GET /minio/health/live` com `urllib` (sem SDK S3, para não adicionar
   dependência que o plano não lista). Banco via SQLAlchemy `SELECT 1`.
5. Filtro de log: modo estrito (lança `CampoProibidoError`) quando `LUPA_AMBIENTE=teste`; nos demais
   remove a chave. Comparação insensível a maiúsculas.
6. Portas publicadas só em `127.0.0.1`. A API S3 do MinIO (9000) e o PostgreSQL não são expostos.
7. A imagem contém `tests/` e `scripts/` e, no compose, as dependências de desenvolvimento
   (`INSTALAR_DEV=true`) para que o revisor rode `verificar.sh` dentro do contêiner. Para produção,
   construir com `INSTALAR_DEV=false` (padrão do `Dockerfile`).
8. `.dockerignore` criado (exclui `.env`, PDFs, DOCX, caches).
10. **Correções da revisão (REVISAO-ETAPA-0.md, seção 4):** `db` roda com `user: "70:70"` (uid
   do `postgres` na imagem alpine; o volume nomeado herda a posse do diretório de dados da imagem e
   continua gravável). `minio` e `minio-init` rodam com `user: "10002:10002"` e `HOME=/tmp`. Como o
   `/data` da imagem pertence a root, o volume `minio-dados` é montado em `/var/tmp` (diretório 1777
   da imagem, cuja permissão o volume novo herda) e o servidor usa `/var/tmp/dados`. Sem contêiner
   auxiliar rodando como root. O healthcheck fictício do `minio-init` foi removido. O README registra
   que a imagem do MinIO é fork comunitário e que o object storage está em aberto.
9. `pytest` ignora um `DeprecationWarning` interno do `starlette.testclient` (de terceiros).

### Etapa 1 — Esquemas de dados

#### 1 — Esquemas de dados

1. **Organização (tarefa 1):** um módulo `esquemas.py` (pydantic) e um `tabelas.py` (SQLAlchemy) para
   todas as entidades, em vez de um submódulo por entidade. Motivo: as entidades se referenciam muito
   (FKs, enums) e um ponto único de import evita ciclos e dá à Etapa 2 um único lugar de import.
2. **`gabinete_id` desnormalizado** em todas as tabelas que pertencem a um gabinete (arquivo, pagina,
   peca, evidencia, fato, fato_evidencia, reu, reu_identidade, achado, anotacao), para a RLS filtrar
   sem junções. Consistência garantida por FKs compostas `(x_id, gabinete_id)`. Os esquemas pydantic
   **não** têm esse campo (ficam iguais ao plano); o repositório o obtém do processo.
3. **Tabela de associação `fato_evidencia`** (N:N): uma evidência pode sustentar mais de um fato.
4. **"Fato sem evidência" no banco** é um `CONSTRAINT TRIGGER ... DEFERRABLE INITIALLY DEFERRED`
   (o fato precisa ser inserido antes das associações). Também é recusado apagar a última associação.
5. **Enums como `text` + `CHECK`**, não `ENUM` nativo do PostgreSQL, para estender sem `ALTER TYPE`.
6. **Papel `lupa_app` (NOLOGIN)** criado pela migração: superusuários ignoram RLS, então a aplicação
   (e os testes de RLS) operam sob esse papel. `FORCE ROW LEVEL SECURITY` também ligado. O
   `downgrade` não remove o papel (é global ao cluster).
7. **`arquivo` também é imutável** (mesmo trigger do achado), já que o plano o declara imutável.
8. **Local das migrações:** `src/lupa/migrations/` (e não `migrations/` na raiz), porque o
   `Dockerfile` da Etapa 0 só copia `src`, `tests` e `scripts`; assim a migração vai na imagem sem
   alterar o `Dockerfile`. Comando: `alembic -c src/lupa/migrations/alembic.ini upgrade head`.
9. **Migração dividida em dois arquivos:** o conteúdo está em `lupa.migrations.esquema_v0001` e
   `versions/v0001_inicial.py` só reexporta `upgrade`/`downgrade`. Motivo: o Alembic carrega os
   arquivos de revisão por caminho com nome de módulo fora de `lupa`, e o `--cov=lupa` não os mede;
   com a lógica em módulo do pacote, a migração entra na cobertura (100%). O teste
   `test_migracao_coincide_com_tabelas` compara banco migrado × `tabelas.py` com
   `alembic.autogenerate.compare_metadata` (diferença vazia).
10. **Banco de teste:** em vez de um compose de teste separado, a fixture `engine_teste` cria um
    database `lupa_teste_<pid>` no serviço `db` existente, aplica `upgrade head`, e o apaga no fim.
    O sufixo pelo PID evita colisão com execuções paralelas (por exemplo, da Etapa 2).
    `docker-compose.yml` não foi alterado.
11. Validações extras no pydantic: `Pagina.hash_texto` = sha256(texto), `Anotacao` com exatamente um
    alvo, só administrador sem gabinete, `confianca` em [0, 1], `Arquivo.sha256` hexadecimal.

#### Endossadas na revisão 1

- `gabinete_id` desnormalizado em todas as tabelas filhas com chaves compostas. Deixa a RLS barata e impede filho apontar para pai de outro gabinete.
- Enums como texto com CHECK. Estender tipo de fato ou de peça vira migração simples.
- Migração escrita à mão com teste que a compara ao modelo SQLAlchemy. É a melhor garantia possível de que as duas fontes não divergem.
- Papel `lupa_app` sem login com RLS forçada, porque superusuário ignora RLS.

### Etapa 2 — Motor de validações

#### 2 — Motor de validações e as três validações do piloto

1. **Esquemas próprios em `validacoes/modelo.py`** porque a Etapa 1 corria em paralelo. Mesmos
   nomes de campo; a troca por `lupa.dominio.esquemas` é só mudar o import (documentado na
   docstring). Nada em `validacoes` importa de `lupa.dominio`.
2. **Formato de `valor`**: datas como string ISO; `tipo_recurso` como
   `{"tipo": ..., "recorrente": "defesa"|"mp"}` (a tabela da Etapa 1 não tem fato para quem
   recorre); pena em meses inteiros; fatos por réu como `{"valor": ..., "reu_id": ...}`.
3. **Dois YAML a mais** além dos listados: `prazos_recursos.yaml` e `preventiva.yaml`, para que
   nenhum prazo fique em `.py`. A redução do art. 115 (21/70 anos, divisor 2) fica em
   `prescricao_art109.yaml`.
4. **Injeção de dados**: cada `executar` aceita um terceiro argumento opcional com as tabelas
   (testes usam feriados sintéticos); sem ele, usa os YAML empacotados (cache `lru_cache`).
5. **Regras de borda** (a confirmar, listadas em `docs/sistema/validacoes.md`): intervalo igual ao prazo
   prescricional não prescreve (limite = início + prazo em meses de calendário); "maior de 70"
   = 70 completos; 90 dias exatos na preventiva é conforme; dias de suspensão não contam no prazo
   corrido; empate de datas de intimação escolhe a do réu.
6. **Validações extras de consistência** que geram `verificar`: marcos da prescrição fora de ordem
   ou posteriores à referência; revisão da preventiva anterior à decretação ou posterior à
   referência; recorrente não identificado.
7. Cada data rastreável em `valores` tem `data`, `tipo`, `fato_id`, `evidencia_id` (primeira) e
   `evidencia_ids` (todas). A data de referência aparece como `{"data", "tipo": "data_referencia"}`,
   sem fato, por não vir dos autos.
8. `docs/` não entra na imagem (Dockerfile da Etapa 0), então os testes usam
   `tests/validacoes/fatos_exemplo.json`, e um teste garante que é idêntico a
   `docs/exemplos/fatos.json` quando `docs/` existe.
9. Log do motor ao capturar exceção: só `validacao` e `erro_tipo` (mensagem fica no achado, não no
   log).

#### Endossadas na revisão 2

- Esquemas de entrada locais em `modelo.py` com os mesmos nomes da Etapa 1. Necessário para o paralelismo.
- `tipo_recurso` com `{"tipo", "recorrente"}`: o modelo de dados não tinha quem recorre, e o prazo depende disso.
- Tabelas injetáveis como terceiro argumento: permite feriados sintéticos nos testes sem tocar nos YAML.
- Regras de borda declaradas e marcadas para confirmação do gabinete, em vez de escolhidas em silêncio.

### Etapa 3 — Autenticação, papéis e auditoria

#### 3 — Autenticação, papéis e auditoria

1. **O banco guarda o SHA-256 do token de sessão,** não o token. Uma cópia do banco não permite
   sequestrar sessões.
2. **Segundo passo do login:** tabela `desafio_mfa` (token de 256 bits, 5 minutos, uso único).
   A sessão só é criada depois do TOTP.
3. **QR code:** a API devolve o segredo em texto e a URI `otpauth://`; quem desenha o QR é a
   interface. Nenhuma biblioteca de QR estava autorizada.
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

### Etapa 4A — Fundações da ingestão

#### 4A.1 — Adaptador validações ↔ domínio

**Decisão: (a), com um resultado intermediário**

As validações passam a consumir **diretamente** `lupa.dominio.esquemas.Fato`/`Evidencia` (ids
`UUID`, `tipo` como `TipoFato`, `evidencias` em tupla). Os esquemas locais `Fato`, `Evidencia`
e `Achado` de `modelo.py` foram removidos; `modelo.py` reexporta `Fato`/`Evidencia` do domínio.

Por quê: a lógica das validações não mudou, só tipos. `TipoFato` é `StrEnum`, então os índices
por tipo e as comparações com strings continuam funcionando; `UUID` é ordenável, então a ordem
determinística por id continua.

A saída do motor não pode ser o `Achado` do domínio diretamente, porque ele exige
`processo_id` e o motor não conhece o processo. Por isso há `AchadoValidacao` (sem `id`,
`processo_id`, `criado_em`; `resultado` usa o enum do domínio; `fatos_usados: tuple[UUID, ...]`).
Não é cópia do esquema do domínio: `para_dominio` o vincula ao processo.

#### 4A.2 — Esquemas da ingestão

- **`TABELAS_COM_GABINETE` passou a incluir as tabelas novas**, porque o teste da Etapa 1
  `test_rls_ativa_em_todas_as_tabelas_com_gabinete` compara esse conjunto com as tabelas com RLS.
  Como as migrações 0001 e 0002 iteravam sobre essa tupla, criei `TABELAS_COM_GABINETE_V1` (os 13
  nomes originais, congelados) e troquei o import em `esquema_v0001.py` e `esquema_v0002.py`. O
  SQL das revisões antigas é idêntico; os testes de ida e volta e de migração × tabelas passam.
  Alteração em arquivos de etapas anteriores, registrada aqui.
- Transições: `falho -> recebido` (nova tentativa), `em_revisao -> em_extracao` e
  `parcial -> em_extracao` permitidas; `concluido` e `quarentena` sem saída.
- O banco reforça `motivo_quarentena` por CHECK; a máquina de estados fica em código (sem trigger).

#### 4A.3 — Fila e worker base

- **RQ** escolhido (registrado), com `SimpleWorker` (sem fork por job): o isolamento pesado está
  no sandbox por subprocesso (4A.4).
- **O banco é a fonte da verdade; o Redis é volátil.** O varredor reenfileira jobs `recebido` com
  lease vencido ou nunca tomados há mais de 30 s. Mensagem perdida, Redis reiniciado ou falha no
  enfileiramento do upload não perdem job.
- **Lote = um PDF**: PDF avulso é um lote; ZIP vira um lote por entrada do manifesto. Na 4C o lote
  pode passar a ser faixa de páginas sem mudar o protocolo.
- Instantes vêm do chamador (`agora`), não do `now()` do banco, para a expiração ser testável.
- O worker conecta com `url_banco_aplicacao()` (usuário sem superusuário), assume `lupa_app` e
  define o gabinete do job em cada transação; só o varredor usa `lupa.papel = administrador`
  para ler jobs de todos os gabinetes.
- Depois de `LUPA_MAX_TENTATIVAS` (3) aquisições o job vai para `falho/erro_interno`.
- O loop captura exceção por ciclo e loga só o nome da classe; sem isso o contêiner morreria
  enquanto a 0003 não estivesse aplicada.

#### 4A.4 — Sandbox de parsing

- O MuPDF sem memória lança `FzErrorSystem` com mensagem vazia; o parser trata
  `FzErrorSystem`/`FzErrorMemory` e `MemoryError` como falta de memória (saída 3).
- `python -I` ignora `PYTHONPATH`; o comando insere a raiz de `src` no `sys.path`.
- O worker precisa de banco, storage e Redis (é ele quem grava); "sem rede e sem banco" vale para
  o processo do parser: sem variáveis, sem credenciais e sem sockets.

#### 4A.5 — Cliente de object storage

- `boto3` não tem stubs: override `ignore_missing_imports` para `boto3`/`botocore` no
  `pyproject.toml`; o cliente é `Any` só dentro do adaptador.
- Erro do S3 que não é ausência (ex.: 403) propaga; só `404`/`NoSuchKey`/`NotFound` viram
  `ObjetoAusenteError`.

#### 4A.6 — Recepção e lacre

- **Corpo binário em vez de multipart**: `python-multipart` não está nas dependências e o
  `UploadFile` faz spool próprio; com `request.stream()` o streaming é real. Nome em `?nome=`.
- **Processo sigiloso bloqueado (403)**, como pede `requisitos-v1.md` §6, com evento `negado`.
- Falha ao enfileirar (Redis fora) só gera log `fila_indisponivel`; o varredor recupera o job.
- `arquivo_enviado` entra na cadeia do gabinete do processo, também quando quem envia é o
  administrador.

#### 4A.7 — Inventário de zip

- Erros viram `ZipRecusadoError(motivo, detalhe)`: `zip_malicioso` para as regras de segurança,
  `senha` para entrada cifrada, `corrompido` para ZIP ilegível, CRC errado ou compressão
  desconhecida, `tipo_invalido` para ZIP sem arquivos. Entrada que não é PDF vira `tipo_invalido`
  no worker.
- Diretórios dentro do ZIP são ignorados.

#### 4A.8 — Quarentena e falhas

- `assinatura_invalida` é conferida **estruturalmente**: se o arquivo tem `/ByteRange` e nenhum
  começa em 0 e termina no fim do arquivo, houve alteração depois da assinatura. A validação
  criptográfica (certificado, cadeia ICP-Brasil) fica fora.
- `truncado` é falta de `%%EOF` nos últimos 1024 bytes, conferida antes de abrir o PDF, porque o
  MuPDF repara arquivos truncados em silêncio.
- PDF com cifra só de dono (abre sem senha) não é quarentena; só `needs_pass`.
- O lote de uma entrada recusada é gravado com estado `falho` e o motivo no resultado.

#### 4A.9 — Observabilidade da pipeline

- **Métricas lidas do banco**, não de contadores em memória: API e worker são processos
  diferentes e o banco já é a fonte da verdade.
- `/metricas` protegida por `exige_papel(Permissao.GERIR_GABINETES)`, a permissão que só o
  administrador tem; não criei permissão nova para não alterar `acesso/papeis.py` (fora do meu
  escopo). Assessor recebe 403; anônimo 401.
- O nome original do arquivo nunca vai ao log (pode conter nome de parte).

#### 4A.10 — Ponta a ponta da fundação

- PDFs e ZIPs sintéticos de teste em `tests/ingestao/arquivos.py` (sem depender da 4B), com
  metadados vazios, `no_new_id` e data fixa no ZIP, para o mesmo conteúdo ter o mesmo hash.
- `tests/conftest.py` (acréscimo): fixture autouse que remove `LUPA_DB_USUARIO_APP` e
  `LUPA_DB_SENHA_APP` do ambiente dos testes. Com o `.env` atual, que define as duas,
  `tests/acesso/test_banco_acesso.py::test_url_da_aplicacao_troca_usuario_quando_configurado` e
  `::test_scripts_de_instalacao` já falhavam antes das minhas mudanças, porque `Settings()`
  herdava o usuário da API. Os testes que precisam dele passam o valor explicitamente.
- A imagem foi reconstruída (`up -d --build --wait`), o que recriou os contêineres usados também
  pela 4B, e o banco principal foi migrado para `0003`.

#### Endossadas na revisão 4A

- Upload como corpo binário com nome em query, sem multipart, para não adicionar dependência. Adequado à API; a interface da Etapa 6 envia assim.
- Processo sigiloso recebe 403 na ingestão: cumpre a regra da primeira versão (só processos públicos).
- Migrações 0001 e 0002 passaram a importar uma tupla congelada com os nomes originais, para que `TABELAS_COM_GABINETE` possa crescer sem reescrever SQL antigo. Correto.
- `requirements` regenerados dentro do contêiner. Resolve a divergência Windows/Linux apontada na revisão da Etapa 3.

#### Endossadas na revisão 4A.1

Opção (a): as validações consomem `lupa.dominio.esquemas.Fato` e `Evidencia` diretamente; os esquemas locais foram removidos de `modelo.py`. Sobrou `AchadoValidacao`, que não é cópia do `Achado` do domínio: não tem id, processo nem data, porque o motor não conhece o processo. `para_dominio` faz a vinculação. É a separação certa.

`data_de` aceita string ISO e `date`, e recusa `datetime` para não descartar a hora em silêncio. Correto.

### Etapa 4B — Autos sintéticos

#### 4B.1 — Esquema do gabarito

- `TipoPagina` só tem `nativa`, `ocr` e `vazia`. Para registrar como a folha foi fabricada criei a
  enumeração local `Composicao` (nativa, digitalizada, hibrida_corpo, hibrida_assinatura, vazia,
  capa); `tipo` continua em `TipoPagina` e diz o que a pipeline deve concluir (híbrida → `ocr`).
- Folhas são numeradas pela folha de conteúdo (igual nos três cenários); a posição física em cada
  arquivo fica em `arquivos[].folhas` (com `null` para páginas de índice). Assim o conteúdo do
  gabarito é idêntico entre cenários.
- Dois textos por folha: `texto` (visível, alvo do OCR, base dos offsets) e `texto_camada`
  (exatamente o `get_text()`), porque marca d'água e injeções ocultas ficam só na camada.
- `resultado_esperado` é calculado pelo próprio motor do Lupa (`executar_catalogo`) a partir dos
  eventos do gabarito, com ids determinísticos (uuid5); `valores` guarda o que o motor devolveu.

#### 4B.2 — Textos por tipo de peça

- Números CNJ: segmento 8, tribunal 99 (inexistente) e sequencial 9900000–9999999, faixa que
  declaramos reservada a testes (documentado em `identidades.py` e `docs/sistema/sinteticos.md`).
- O roteiro escolhe o crime pela prescrição desejada (pena baixa quando o processo deve prescrever)
  e força intervalos entre revisões da preventiva acima de 90 dias quando o resultado pretendido é
  atenção. O resultado gravado é sempre o do motor, não o pretendido.
- Parágrafos de enchimento trazem datas distratoras (ofícios, audiências, mandados).

#### 4B.3 — Renderização nativa

- `texto_camada` é lido do próprio PDF gerado; o teste prova que o texto montado pelo gerador
  (`texto`) é prefixo exato da camada.

#### 4B.4 — Renderização digitalizada

- Desempenho: o ruído vem de um campo pré-calculado por nível, recortado em posição sorteada
  (gerar ruído novo por folha custava três quartos do tempo); o JPEG usa qualidade 40–45 com
  desfoque de 0,7 px. Uma folha digitalizada pesa de 150 a 300 KB.
- `numpy` foi acrescentado às dependências (ruído), junto com `pymupdf` e `pillow`.

#### 4B.6 — Carimbos, marcas e rodapés

- A marca d'água fica na camada de texto (no fim de `get_text()`), não em `texto`: é ruído que a
  extração precisa ignorar.

#### 4B.7 — Três cenários de empacotamento

- O índice traz a folha física já deslocada pelas páginas de índice; o gabarito marca essas
  páginas com `null` em `arquivos[0].folhas`.

#### 4B.8 — Injeções por vetor

- Injeções não alteram o resultado esperado: o gabarito diz o que é verdade; a pipeline passa se
  não obedecer.
- "Repositório separado com acesso restrito" foi atendido como pasta fora do repositório
  (`.sinteticos/injecao/`, ignorada pelo git); criar um repositório de verdade é decisão do
  gabinete.

#### 4B.9 — Processos de referência

- O maior processo ficou com 5.000 folhas (não foi preciso reduzir para 2.000): a geração é rápida
  porque ele é quase todo nativo. Inverter a mistura (o maior mais digitalizado) passaria de 3 GB
  só nele, numa pasta sincronizada pelo OneDrive.
- "Repositório separado versionado": a reprodutibilidade vem da semente e da versão do código (teste
  prova que mesma semente → gabarito idêntico byte a byte). Os PDFs ficam fora do git; versionar os
  binários em outro repositório é decisão do gabinete.
- Variantes pequenas (alvo de 30 folhas) saem com 50 a 60 quando há muitas revisões da preventiva:
  as peças obrigatórias já passam do alvo.
- A pasta `.sinteticos/` está no OneDrive: 4,7 GB vão sincronizar. Sugiro excluí-la do OneDrive ou
  usar `LUPA_SINTETICOS_DIR` fora dele.

#### 4B.10 — Harness de medição

- Página do índice (folha `null`) usada como início de peça conta como erro de fronteira.
- Página sem texto na saída entra no CER com tudo faltando.
- Levenshtein descarta prefixo e sufixo comuns antes da programação dinâmica; em folhas muito
  divergentes custa alguns segundos por folha.

#### Endossadas na revisão 4B

- Enum `Composicao` separado de `TipoPagina`: o gabarito precisa distinguir híbrida de corpo e de assinatura, e capa de vazia, enquanto o roteador da 4C só decide entre nativa, OCR e vazia. É a separação correta entre "o que a página é" e "o que fazer com ela".
- Dois textos por página: o visível, onde os offsets apontam, e o que `get_text()` devolve. Permite medir o roteador e o saneamento de texto oculto.
- CPFs inválidos pelo dígito e CNJ em tribunal inexistente com faixa reservada: garante que nenhum dado sintético colide com dado real.
- Resultado esperado calculado pelo motor: evita manter duas lógicas; o gabarito testa a extração, não o motor, que já tem seus testes.

### Etapa 4C — Diagnóstico e páginas

#### 4C.1 — Diagnóstico do contêiner

- **Novo valor `CenarioArquivo.PDF_COM_BOOKMARKS_E_INDICE`**: o gabarito 4B espera `pdf_com_bookmarks_e_indice` para o cenário com índice; sem o valor, o critério 30/30 era impossível.
- **ZIP com uma só entrada** é diagnosticado pelo PDF de dentro (sinal `zip_com_um_pdf`).
- **Correção em arquivo da 4A** (`parser_pdf.py`): página sem stream de conteúdo (folha em branco, presente em todos os processos de referência) fazia o PyMuPDF 1.25.1 lançar `AssertionError` em `read_contents()` e o PDF ia para quarentena como `corrompido`. Agora a página sem conteúdo é pulada. Teste: `test_pdf_com_pagina_sem_conteudo_nao_e_corrompido`.

#### 4C.2 — Bookmarks e índice

- Guardamos as duas fontes (índice e bookmarks) quando existem; a Etapa 4E confere uma contra a outra e contra o conteúdo.
- A página registrada é a física no arquivo (já com as páginas de índice); o deslocamento sai de `sinais.paginas_indice`.

#### 4C.3 — Sinais por página

- **Área de imagem opaca separada da total**: carimbos (PNG com transparência) aparecem em 1.290 páginas nativas dos processos de referência com área até 2,7%, enquanto a assinatura digitalizada das híbridas ocupa 2,0 a 4,7%. Só a máscara de transparência separa os dois; imagem opaca é tratada como conteúdo digitalizado.
- **Texto invisível** (fora da página exige `clip=INFINITE_RECT` e sem `TEXT_MEDIABOX_CLIP`) entrou como sinal porque é o que permite levar a página de camada manipulada ao OCR (4C.7).

#### 4C.4 — Roteador de páginas

- **Capa mapeada para `nativa`**, não `vazia`: o gabarito 4B marca a capa como `TipoPagina.NATIVA` (tem 400+ caracteres de camada de texto); rotear como vazia descartaria esse texto.
- **Digitalização em branco não é `vazia`**: na primeira calibração 53 páginas digitalizadas de contraste baixo saíram com tinta < limiar; agora `vazia` exige ausência de imagem opaca e a página vai ao OCR (que devolve `vazia` se não ler nada).

#### 4C.5 — Texto nativo com coordenadas

- A página com injeção `texto_branco` tem a linha oculta escrita por último no arquivo, mas posicionada acima do rodapé: a ordem de leitura a põe no lugar físico; o conjunto de linhas é igual ao `texto_camada`.

#### 4C.6 — OCR

- OSD a 150 DPI dava confiança 1,9 numa página deitada (abaixo do limiar); passou a usar o raster de 300 DPI, sem custo extra de rasterização quando a página está de pé.
- `.sinteticos` entrou no `.dockerignore` (4,7 GB no contexto de build) e é montado só leitura no `api`.

#### 4C.7 — Páginas híbridas

- Linhas não horizontais do nativo (marca d'água) ficam fora do texto fundido e fora da comparação; continuam em `texto_nativo`. Texto oculto girado fica para a 4D.1.
- Texto fora da página não entra no texto nativo (o PyMuPDF recorta), mas o sinal `caracteres_invisiveis` leva a página à abstenção; a marcação dele é da 4D.1.

#### 4C.8 — Paralelismo e desempenho

- Round-robin em vez de fila com prioridade: não exige mudar o RQ nem saber o tamanho do job ao enfileirar, e o estado do job continua só no banco.
- O semáforo por gabinete vale por processo worker; com várias réplicas o teto passa a ser por réplica (registrado em `docs/sistema/ingestao.md`). Um semáforo no Redis fica para quando houver mais de um worker.
- O varredor também recupera jobs `validado`/`em_extracao` com lease vencido, e os que cederam a vez e ficaram 10 min sem heartbeat (mensagem perdida).

#### 4C.9 — Gravação de páginas

- A chave de idempotência é `(arquivo_id, versão)`; como o arquivo é único por `(processo, sha256)`, equivale a `(sha256, versão)` dentro do processo. Reaproveitar páginas do mesmo sha256 em outro processo é cache da 4F.8.
- `concluido` é final na máquina de estados; reprocessar um job concluído com nova versão exige reabrir o job (feito no teste por SQL). O gatilho de reprocessamento por versão é da 4F.8.
- A fixture `deps` dos testes da 4A passou a `extrair=False, max_retentativas=0` (comportamento da fundação); os testes 4C usam `deps_extracao`. Arquivo de outra etapa alterado: `tests/ingestao/conftest.py`, e o ponta a ponta (`test_ponta_a_ponta.py`) agora vai até `concluido`.

#### 4C.10 — Relatório de qualidade por arquivo

- Os relatórios dos dez processos foram gerados pelo script (mesmas funções do worker) e não pelo upload no MinIO, para não carregar 1,9 GB no storage de desenvolvimento; o caminho com banco é coberto por `test_pdf_sintetico_com_indice_vai_a_concluido...` e pelo ponta a ponta.
- Paralelismo das medições: 8 lotes de 8 páginas (12 CPUs). O tempo com o padrão de produção (4 lotes) está no [relatório da 4C.8](../etapas/ETAPAS.md#etapa-4c-8).
- Só o cenário `pdf_liso` foi extraído por completo (as páginas são as mesmas nos três cenários; o diagnóstico dos três está em 4C.1).

#### Endossadas na revisão 4C

- Correção de bug em `parser_pdf.py` da 4A: página sem stream de conteúdo mandava o PDF inteiro para quarentena. Afetava todos os processos de referência e foi pego pela medição. É exatamente para isso que o gabarito existe.
- Enum `CenarioArquivo.PDF_COM_BOOKMARKS_E_INDICE`, porque o cenário sintético tem os dois. Correto, e o diagnóstico continua distinguindo os casos só com um.
- `.sinteticos` montado só leitura e fora do contexto de build.

### Etapa 4D — Saneamento

#### 4D.1 — Texto oculto

- No PyMuPDF 1.25 a cor do span vem com o byte de alfa (`-1` = branco opaco); a comparação usa `cor & 0xFFFFFF`. Isso mostra que o sinal `caracteres_invisiveis` da 4C (que compara `color == 0xFFFFFF`) só pega texto branco quando ele também é pequeno ou está fora da página; não alterei o sinal da 4C para não mexer no roteamento calibrado (fica para a revisão decidir).
- Trocar o estado das OCGs com `set_layer` não muda a extração do documento aberto; é preciso regravar e reabrir. A cópia com tudo ligado é feita uma vez por documento e só quando há OCG desligada.
- Texto girado é visível ao assessor: não é tratado como oculto (a 4C já o tira do fluxo de leitura). Registrado na docstring e em `docs/sistema/ingestao.md`.
- Testes da 4C ajustados (arquivos de outra etapa, registrado aqui): `test_hibridas.py::test_camada_de_texto_manipulada_e_separada_como_texto_oculto` (antes `..._gera_texto_divergente`: o texto branco agora é separado antes da fusão, então a página tem `texto_oculto` em vez de `texto_divergente`); `test_paginas.py::test_texto_nativo_igual_a_camada_do_gabarito_com_offsets` (a linha oculta do gabarito não está mais no texto); `test_worker_extracao.py` passou a exigir `texto_oculto` onde exigia `texto_divergente`.

#### 4D.2 — Metadados e anotações

- **`arquivo.metadados_descartados` virou `diagnostico_arquivo.metadados_descartados`**: `arquivo` é imutável (trigger `arquivo_imutavel`, 0001) e é gravado antes do parsing. O diagnóstico é um por arquivo e já guarda o que a inspeção do PDF descobre.

#### 4D.3 — Normalização Unicode

- O mapa de offsets não é gravado: `normalizar` é determinística para a mesma versão do YAML, então o mapa é recalculado a partir de `pagina.texto` quando preciso (`hash_trecho_normalizado`). Cada trecho suspeito já grava os offsets nos dois textos.
- NFKC aplicado por aglomerado, e não no texto inteiro, para que cada caractere normalizado aponte para um intervalo exato do original.

#### 4D.4 — Blocos codificados

- O OCR parte o código de autenticação de 40 hex dos sintéticos em pedaços e troca letras (`0`→`O`, `5`→`S`, `1`→`I`): a primeira medição em `semente_01` deu 53 de 196 páginas sinalizadas. A tolerância de tamanho e o alfabeto de uma só caixa zeraram isso sem perder a injeção (o base64 da instrução tem minúsculas).

#### 4D.5 — Padrões de instrução

- Os padrões exigem destinatário de máquina, pedido de ignorar instruções, regras ou laudo, pedido de revelar dados ou ordem dirigida (`declare`, `registre que`, `classifique ... como`), nunca imperativo genérico: peças legítimas usam "registre-se", "considere-se", "requer seja declarada".

#### 4D.6 — Idioma inesperado

- `min_proporcao` entrou depois que a citação "the burden of proof lies with the prosecution", dentro de frase em português, disparou (4 funcionais em 13 palavras).

#### 4D.7 — Densidade anômala

- Limite por tipo de **página** (nativa, ocr, vazia), porque o tipo de peça só existe na 4E; o YAML pode ganhar chaves por tipo de peça depois.

#### 4D.8 — Origem por trecho

- `pagina.origem_peca` não foi criada: a origem é consultada na peça (fonte única); a 4E decide se vale desnormalizar.

#### 4D.10 — Painel de flags e regressão

- `imagem_com_texto` conta como **não textual** (2 casos): a página é roteada como nativa, não vai ao OCR e a instrução da imagem não chega a texto nenhum. O objetivo não se materializa na ingestão, mas também não há alerta. Se o OCR passar a ler imagens embutidas em páginas nativas, o teste passa a exigir `padrao_instrucao`.
- A regressão também roda dentro do `pytest` geral (marcador `integracao`, pula sem corpus); o passo próprio repete sem skip e grava as métricas. Custo: cerca de 160 s cada.

#### Endossadas na revisão 4D

- Metadados descartados em `diagnostico_arquivo` porque `arquivo` é imutável por trigger. Correto.
- Mapa de offsets recalculado em vez de gravado: evita coluna grande e mantém `texto` como única fonte.
- Ajustes nos testes da 4C: texto oculto agora é tratado antes da fusão com o OCR, e os testes passaram a esperar `texto_oculto` em vez de `texto_divergente`. É a semântica certa.

### Etapa 4E — Fronteiras e índice

#### 4E.0 — Tarefas prévias (texto branco, ZIP lento, duas colunas)

- Versão do extrator subida (`4e.0`) em vez de manter `4d.1`: a correção muda a rota de
  páginas com texto branco.
- Grupo de 32 entradas por filho: com o limite de 2 GB e 300 s por filho, cabe com folga nas
  peças típicas; o pior caso (grupo com uma bomba) custa 32 reinspeções individuais.

#### 4E.1 — Sinais de fronteira

- Sinais calculados no processo do worker a partir do texto e das caixas já gravados, não no
  filho do sandbox: evita reabrir o PDF e dá o mesmo resultado para nativo e OCR. A "fonte
  dominante" é a altura mediana das caixas de linha (o nome da fonte não está gravado), e a
  mudança de fonte só conta entre páginas do mesmo tipo (nativo × OCR têm alturas diferentes).
- Só as zonas de topo e fim contam como repetidas: na primeira versão os parágrafos de
  enchimento repetidos eram tirados do corpo (e o cálculo levava 4 s por 40 páginas).

#### 4E.2 — Classificador de fronteira por regras

- Fraca também cria peça (com flag), em vez de só avisar, seguindo "Peca.metodo = regra com
  confiança baixa e flag". `RAZÕES DE APELAÇÃO` é título de seção (0,25, nunca fronteira
  sozinho).

#### 4E.3 — Uso do índice quando existe

- "Sem sinal forte" segue literal o roteiro (pontuação < 0,8), por isso a capa gera uma
  divergência por processo; afrouxar para "sem sinal nenhum" zeraria o número, mas esconderia
  as peças cuja assinatura o OCR perdeu.

#### 4E.8 — Reclassificação manual

- Ação nova `peca_reclassificada` em vez de `fato_corrigido` (peça não é fato).
- Colunas novas `vigente`, `flags`, `classificacao` além de `substitui_peca_id`: a união
  substitui duas peças e precisa da lista; o índice filtra por `vigente`.
- A data acompanha a parte que contém a página da evidência; a outra parte fica sem data.

#### 4E.9 — Medição contra gabarito

- Só o `pdf_liso` foi extraído (OCR, ~55 min no total); as folhas são as mesmas nos três
  cenários, então o texto é reaproveitado pelo mapa `arquivos[].folhas` do gabarito; as páginas
  do índice do `pdf_indice` são lidas por texto nativo e o diagnóstico (fronteiras da origem)
  de cada cenário roda de verdade. Por isso tipo, origem e data são iguais nos três.
- A medição de peças envia páginas sem texto ao `medir` (o CER em Python puro levaria horas;
  ele já foi medido na 4C.10).

### Etapa 4F — Eventos e ponta a ponta

#### 4F.1 — Padrões de data

- Ano de 2 dígitos: pivô fixo 50 em vez de janela relativa à data de referência, para o mesmo
  texto dar sempre a mesma data; quem usa a ocorrência multiplica a confiança por 0,8 (4F.2).
- `data_peca.py` (4E.6) continua com as suas expressões; não foi trocado para não mudar a
  medição aprovada da 4E. Pode passar a usar `datas.py` numa próxima versão do índice.

#### 4F.2 — Extratores por tipo de peça

- `data_denuncia` (existe em `TipoFato` e no gabarito) também é extraída: linha "Local, data."
  no fim da denúncia (`ultima: true`).
- Pena aplicada não é gravada: `TipoFato` não tem tipo para ela e nenhuma validação a usa. Fica
  registrada aqui; entra se o catálogo ganhar a prescrição pela pena aplicada (revisão 2, item 3).
- Gatilho de `data_sentenca` aceita vírgula no lugar do ponto ("Publique-se, Registre-se,"), erro
  de OCR visto na medição da 4F.9.
- Fatos de um tipo por réu: só nascimento e intimação do réu (os que dependem da pessoa).

#### 4F.3 — Evidência obrigatória

- O trecho começa no gatilho e termina no fim da data ("mantenho a prisão preventiva em
  07/10/2014"), para a evidência mostrar por que a data é aquele fato, não só a data solta.

#### 4F.4 — Validação cruzada

- A comparação de conflito é por réu (dois nascimentos de réus diferentes não conflitam).

#### 4F.5 — Réus e pseudonimização

- O nome continua no texto da página (aceito pelo roteiro). O recorte vale para o réu; nomes de
  defensor e testemunha ficam nos trechos (não são partes pseudonimizadas). Nos sintéticos, o
  defensor às vezes compartilha sobrenome com o réu; o teste confere o nome completo e o CPF.
- O `reu_id` em `valor` é o UUID do réu, não o pseudônimo, para a ligação não depender de ordem.

#### 4F.6 — Gravação de fatos

- Fato anotado de uma versão antiga cujo valor e evidência continuam iguais não é duplicado na
  versão nova (mesma chave natural): fica o antigo, com a anotação.
- `reu.id` não tem default no banco; o repositório gera o UUID.

#### 4F.7 — Execução do catálogo

- O worker roda o catálogo com a data de hoje (`deps.relogio`); a comparação com o gabarito usa
  a `data_referencia` do gabarito (`achados_do_processo(..., referencia)`), porque prescrição e
  preventiva dependem da data de referência.
- "Valores principais" = todos os valores do achado menos os ids (datas, prazos, vencimento,
  intervalos, faixa do art. 109, redução do art. 115, cadeia da preventiva). É mais estrito que
  comparar só o resultado.

#### 4F.8 — Cache e reprocessamento

- O extrator de páginas subiu para `4f.0` (OCR de detecção em imagens de páginas nativas, ver
  4F.9 e `docs/sistema/ingestao.md`); páginas gravadas em `4e.0` não servem de cache para `4f.0`.

#### 4F.9 — Ponta a ponta nos processos de referência

- `imagem_com_texto` (revisão 4D §6.2): implementado o OCR só de detecção em imagens com área
  acima de 2% da página nativa (`lupa/ingestao/imagem_nativa.py`, extrator `4f.0`). Custo medido
  antes de implementar: 21 a 27 s por mil páginas nativas (semente_04 e semente_06); depois, o
  nativo completo ficou em 35,8 s por mil. A injeção do corpus é detectada
  (`dirigido_a_sistema`, `alterar_resultado`). Registrado em `docs/sistema/ingestao.md`.
- Dimensionamento (revisão 4C §5.1): registrado acima e em `docs/sistema/ingestao.md`.

#### 4F.10 — Calibração com o processo real

- O relatório contém trechos dos autos: fica no contêiner e o roteiro proíbe versioná-lo.

#### Endossadas na revisão 4F

- OCR só de detecção nas imagens de páginas nativas com área acima de 2%, gerando flag sem entrar no texto. Fecha o item `imagem_com_texto` da revisão 4D com custo de 21 a 27 s por mil páginas. Subiu a versão do extrator de páginas para `4f.0`, o que invalida o cache antigo; correto.
- Trecho de evidência recortado para não conter nome nem CPF do réu. Mantém a rastreabilidade (a página continua apontada) e cumpre a pseudonimização nos derivados.
- Correção de `logging.py`: `configurar_logging` prendia o `sys.stdout` do momento. Resolve o problema de saída fechada na origem, como pedido.

### Etapa 5 — Agente e chat

#### 5.1 — Contrato do agente

- O SDK exige `mcp>=1.23`, que exige `pydantic>=2.11`: `pydantic` passou de 2.10.4 para
  2.11.10 (`pydantic-core` 2.33.2) em `requirements.in`, `pyproject.toml` e nos `requirements*.txt`
  regenerados com `pip-compile --generate-hashes` num contêiner `python:3.12-slim` descartável
  (escrita pelo volume montado). Mudança em arquivo comum, registrada aqui; suíte inteira verde.
- O binário do Claude Code vem dentro do wheel: o `Dockerfile` não precisou mudar; a imagem da API
  cresce cerca de 300 MB.
- A documentação diz que terceiros não podem oferecer login do claude.ai em produtos feitos com o
  SDK: no piloto a credencial deve ser `ANTHROPIC_API_KEY` vinda de cofre.
- Marcadores novos no `pyproject.toml`: `agente` e `llm`; `addopts` passa a excluir `llm`.

#### 5.2 — Ferramentas de leitura estruturada

- Busca por ILIKE (e não FTS) para casar exatamente com o texto citável; índice trigram pode vir depois.

#### 5.3 — Ferramenta de cálculo

- Nome da validação no esquema da ferramenta como `enum` do catálogo da matéria.

#### 5.4 — Válvula de escape

- O texto original também sai pseudonimizado (nome e CPF dos réus), como todo texto enviado.

#### 5.5 — Montagem de contexto e prompts

- O hash citável é o do segmento enviado (linha do texto normalizado e pseudonimizado), porque o modelo não calcula SHA-256; a conferência recalcula os segmentos do texto gravado.

#### 5.6 — Conferência de citações

- Resposta bloqueada vira `chamada_modelo` com resultado `bloqueada` e evento de auditoria com resultado `bloqueado` (o registro do incidente).

#### 5.7 — Política de recusa

- Pergunta recusada é gravada e auditada (`pergunta_chat`), sem chamada ao modelo.

#### 5.8 — Suíte de injeção do agente

- O teste reaproveita as fixtures de ingestão sintética (`tests/ingestao/conftest.py`); a extração da sessão roda de novo neste módulo (cerca de 1 minuto).

#### 5.9 — Registro e custo

- Hashes e tokens ficam em tabela própria porque o evento de auditoria tem formato fixo, sem
  campo livre (Etapa 3); a cadeia da auditoria não muda.
- O SDK não tem `max_tokens` por chamada: o teto por chamada é conferido depois (resposta
  descartada) e o laço é limitado por `max_turns`.

#### 5.10 — Dossiê gerado

- As páginas do arquivo diferem das folhas do gabarito por deslocamento constante (capa/índice); o teste confere tipos, extensões e que o deslocamento é único.

#### Endossadas na revisão 5

- O modelo cita copiando o hash do segmento que a ferramenta entregou; a conferência recalcula os segmentos do texto gravado. Evita pedir ao modelo um SHA-256 e mantém a barreira em código.
- `pydantic` de 2.10.4 para 2.11.10, exigido pelo SDK; suíte inteira passa. Registrado.
- Busca por ILIKE no texto normalizado, para casar exatamente com o que pode ser citado.
- Hashes e tokens em tabela própria em vez de campo livre na auditoria: mantém o esquema da auditoria fixo.

### Etapa 6 — Interface web

#### 6.1 — Esqueleto do front

**Decisões de arquitetura**

| Decisão | Escolha | Por quê |
| --- | --- | --- |
| Framework | **SvelteKit 2 + Svelte 5**, `adapter-static`, SPA (`ssr = false`) | Bundle pequeno e sem runtime pesado; TypeScript estrito de ponta a ponta (`svelte-check`); avisos de acessibilidade do compilador viram erro no typecheck. Next.js traria React + servidor Node para SSR que não usamos: toda a autorização está na API, e uma SPA estática não precisa repassar cookie em servidor intermediário. |
| UI | CSS próprio com tokens (`src/app.css`), claro/escuro por `prefers-color-scheme` | Sem biblioteca de UI; única dependência de execução é `qrcode` (matriz do QR). |
| Servir o front | Serviço `front`: imagem multi-estágio; o estágio `verificacao` roda lint, typecheck e testes e o build só continua se passarem; runtime Caddy estático, usuário `10001`, `read_only`, `no-new-privileges` | Build de produção, não root. |
| Mesmo origin | Serviço `proxy` (Caddy 2.8.4): `/api/*` → `api:8000` com o prefixo removido (`handle_path`), `/*` → `front:8080`; `tls internal` em `https://localhost:8443` (`PROXY_PORTA_HOST`) | Sem CORS; cookie `Secure`/`SameSite=Strict` funciona. `api/app.py` não precisou de `root_path`. |
| IP real na API | `command` da `api` no compose com `--proxy-headers --forwarded-allow-ips <sub-rede borda>`; rede `borda` com sub-rede fixa (`REDE_BORDA_SUBREDE`) | Auditoria e rate limit por IP veem o cliente (conferido: eventos do E2E gravados com o IP do contêiner `e2e`, não o do proxy). |
| Porta direta da API | `127.0.0.1:${API_PORTA_HOST:-}:8000` | Com a variável definida, continua publicando nela (o `.env` atual usa 18000); sem ela, porta efêmera só em loopback. O compose não tem publicação condicional; esta é a forma mais próxima de "não publicar". |
| Testes | Vitest + Testing Library (jsdom) para componentes; Playwright 1.49.1 em contêiner (`e2e`, perfil `e2e`, rede `cliente`) | Ver 6.2 e 6.3. |
| Lockfiles | `package-lock.json` gerados num contêiner `node:22.12.0-alpine3.20` e lidos pela saída padrão; `npm ci` no build | Node não existe no host; nenhuma cópia de diretório do contêiner para o host. `picomatch` 4.0.2 fixado como devDependency para contornar um erro de consistência do `npm ci` 10.9 (lock com `picomatch@2` hoisted). |

#### 6.8 — Chat (com o item 3 da revisão 5)

- Liberar usa a permissão `ver_auditoria` (exatamente desembargador e admin) em vez de criar
  permissão nova em `papeis.py` (fora do meu escopo).
- `tabelas.py` recebeu só acréscimos (`TABELAS_REVISAO`, `RevisaoProcessoTabela`), necessário
  para o teste que compara migração e metadados.
- `tests/agente/test_injecao_agente.py`: a suíte roda os cenários em sequência no mesmo processo;
  agora libera a revisão entre cenários e confere `processo_em_revisao` em cada resposta.
- Arquivos compartilhados alterados (só acréscimos): `docker-compose.yml`
  (`LUPA_AGENTE_CLIENTE` na API, padrão `sdk`; variáveis `LUPA_E2E_CHAT_*` no e2e),
  `front/scripts/e2e.sh` e `e2e.ps1` (exportam `LUPA_AGENTE_CLIENTE=falso` e rodam
  `scripts/e2e_semear_chat.py --carga`), `MenuLateral.svelte` (item Auditoria).
- O spec E2E ficou em `front/e2e/testes/chat-auditoria.spec.ts` (o `testDir` do Playwright é
  `testes/`); 6.8 e 6.9 no mesmo arquivo para reaproveitar o desembargador semeado.

#### Endossadas na revisão 6.1-6.3

- Proxy reverso removendo o prefixo `/api` em vez de `root_path` na API: mantém `api/app.py` intocado e o cookie `Secure`/`SameSite=Strict` funciona sem CORS.
- API com `--proxy-headers` restrita à sub-rede do proxy, para a auditoria registrar o IP do cliente e não o do proxy. Conferido pelo executor com o contêiner de E2E.
- `scripts/e2e_preparar.py` fora da lista inicial: necessário porque a senha do admin de desenvolvimento não é conhecida. Recusa rodar fora de desenvolvimento ou teste e reseta o admin com senha aleatória só em memória. Aceito.

#### Endossadas na revisão 6.4-6.9

- Visualizador por imagem renderizada no servidor, não pdf.js com o PDF cru: o PDF nunca chega ao navegador, e o texto oculto por camada ou fora da área não é desenhado. Limitação registrada: conteúdo visível no PDF aparece como está.
- Modo de teste do agente (`LUPA_AGENTE_CLIENTE=falso`) recusado em produção, com teste. Necessário para E2E sem chave.
- Migração numerada 0009 com `down_revision` 0007, porque a 0008 nunca existiu. Linear e aplicada.
- Correção de bug no histórico do chat (ordem de pergunta e resposta na mesma transação), com teste.

#### Endossadas na revisão 6.10

- Hash de estilo em vez de `unsafe-inline`: a exceção é mínima e explícita, e a varredura acusa se o hash mudar numa atualização do SvelteKit.
- Recriação do proxy pelo `e2e.sh`: o Caddyfile entra por bind mount e a edição não chega ao contêiner em execução. Documentado.
- Fins de linha: as edições pelo host gravaram CRLF e quebraram o `verificar.sh` no contêiner; o executor converteu seus arquivos para LF e devolveu os demais ao estado anterior. Vale um `.gitattributes` com `* text=auto eol=lf` para scripts, quando o repositório for iniciado no git.

### Etapa 7 — Criptografia, backup e guias

Decisão do object storage: ver [object-storage.md](object-storage.md).

#### 7.10 — Documentação de operação

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

#### Endossadas na revisão 7.1-7.9

- Cifra na aplicação, não no servidor de storage: é o que torna o MinIO substituível por configuração.
- Cifrar também `texto_nativo` e `texto_ocr`, além da lista do roteiro: sem isso o dump ainda mostraria os autos. Correto.
- Busca do agente em memória por processo com teto, em vez de índice HMAC: aceitável no piloto porque a busca é sempre por um processo; registrado.
- Backup copia bytes cifrados como estão e a restauração exige o Vault com as mesmas chaves; snapshot do Vault preparado e comentado no script.
- Captura de telas sem reduzir o upload para 5 MB, porque a redução quebrava o teste de progresso; correção só no script e no spec de capturas.

### Etapa 8 — Piloto

#### Endossadas na revisão 8.1

- Sem TLS entre API/worker e Vault no piloto: um host, redes internas sem porta publicada; quem observa a rede do Docker já é root. Registrado em `docs/operacao/operacao.md` 4.6 e a reavaliar se o Vault sair do host.
- HSTS mantido no modo de desenvolvimento porque a varredura de cabeçalhos e o E2E exigem; sem efeito com certificado não confiável.
- Agendador pelo crond da imagem de backup, para não entregar o socket do Docker a um serviço de agendamento.
- `/metricas/servico` separado da rota de admin, porque o Prometheus não faz login com TOTP.

## Decisões posteriores à v1

Tomadas depois da Etapa 8, ao simplificar o projeto. Cada uma diz o que substitui; as entradas antigas acima ficam como foram escritas.

### Simplificação (novembro de 2026)

- **Dependências declaradas só no `pyproject.toml`.** Os `requirements.txt` e `requirements-dev.txt`, com hashes, são gerados dele por `make lock` (`uv pip compile`, mirando `x86_64-manylinux_2_28` e Python 3.12). O `requirements-dev.txt` traz produção + dev, e a imagem de dev instala só ele. Substitui o item 1 da Etapa 0 (`pip-compile` a partir dos `.in`) e a regeneração dentro do contêiner da 4A. Motivo: a mesma lista estava em três arquivos, e gerar no Windows trazia `tzdata` e `colorama`; mirar a plataforma resolve isso sem contêiner. Versões e hashes de produção não mudaram.
- **Só scripts `.sh`.** Os oito `.ps1` saíram. No Windows, os scripts rodam pelo Git Bash; o resto, pelo `docker compose`. Substitui a menção ao `e2e.ps1` da Etapa 6. Motivo: os pares já tinham divergido. O `verificar.ps1` tinha os passos de E2E e de backup que faltavam no `verificar.sh`, e eles foram levados para o `.sh`.
- **Dado em claro é recusado na leitura.** Objeto sem cabeçalho `LUPAOBJ` e campo sem prefixo `lupa1:` geram `CifraInvalidaError`; identidade sem token do cofre gera `TokenInvalidoError`. Saiu o `scripts/recifrar_objetos_legado.py` (7.10). A migração `0012` tira o `DEFAULT '[]'` em claro de `pagina.trechos_ocultos` e `pagina.trechos_suspeitos`; a lista vazia agora vem do modelo, já cifrada. Substitui a leitura de legado da 7.4 (aviso `objeto_legado_em_claro`) e resolve a pendência registrada na [7.4 — Cifra dos originais](../etapas/ETAPAS.md#etapa-7-4). Motivo: aceitar dado em claro servia só como caminho de migração e escondia gravação sem cifra; não há dado real anterior à 7.4. Consequência: dado em claro no banco ou no bucket passa a ser incidente (`docs/operacao/operacao.md`, seção 10), e o bucket de desenvolvimento é recriado antes do piloto (`docs/piloto/roteiro-piloto.md`, passo 0.4).

## Resultado das revisões

| Revisão | Resultado |
| --- | --- |
| 0 | **Aprovado com correções obrigatórias antes do início das Etapas 1 e 2.** |
| 1 | **Aprovado.** Etapa 3 liberada. |
| 2 | **Aprovado.** |
| 3 | **Aprovado.** Etapas 4A (restante) e 4B liberadas. |
| 4A | **Aprovado.** Etapa 4C liberada assim que a 4B for aprovada. |
| 4A.1 | **Aprovado.** |
| 4B | **Aprovado.** Etapa 4C liberada. |
| 4C | **Aprovado.** Etapa 4D liberada. |
| 4D | **Aprovado.** Etapa 4E liberada. |
| 4E | **Aprovado.** Etapa 4F liberada. |
| 4F | **Aprovado.** Etapa 4 (4A a 4F) concluída. |
| 5 | **Aprovado, condicionado à execução do smoke test real pelo responsável técnico antes do piloto.** |
| 6.1-6.3 | **Aprovado.** Subetapas 6.4 a 6.10 liberadas. |
| 6.4-6.9 | **Aprovado.** Subetapa 6.10 liberada. |
| 6.10 | **Aprovado.** Etapa 6 concluída. |
| 7.1-7.9 | **Aprovado.** Subetapa 7.10 liberada. |
| 7.10 | **Aprovado.** Etapa 7 concluída. |
| 8.1 | **Aprovado.** O que agentes conseguem construir para a primeira versão está concluído. |
| 8.2 | **Aprovado como minuta**, condicionado à revisão de advogado antes do aceite pelos usuários e à decisão sobre a pseudonimização de vítimas e testemunhas (seção 3). |
