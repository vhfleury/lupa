# Lupa — O que ficou de fora em cada etapa

Limitações, itens fora do escopo e pendências registrados durante a construção, num lugar só. Vêm de duas fontes:

- as seções "O que ficou de fora", "Fora do escopo", "Limitações" e "Pendente" de cada relatório de etapa. Só os 19 relatórios citados pelo código e pelos manuais continuam em `docs/etapas/`; os outros 78 estão no histórico do Git (commit `58e9774`);
- os riscos, observações e pendências apontados nas revisões, que foram removidas do repositório e continuam no histórico do Git (commit `54219a2`, pasta `docs/etapas/`).

Texto mantido como foi escrito na época. Muitos itens foram resolvidos em etapas seguintes; o estado consolidado está em `docs/etapas/CONFORMIDADE-GERAL.md`. As pendências abertas para o piloto e os itens para o advogado estão em `docs/piloto/pendencias.md` e não são repetidos aqui. As decisões estão em `docs/decisoes/registro.md`.

## Etapa 0 — Esqueleto do projeto

### 0 — Esqueleto do projeto

- **Alembic não inicializado** (sem `alembic.ini`/`migrations/`): não há modelos até a Etapa 1. O alvo
  `make migrate` já chama `alembic upgrade head` e passará a funcionar quando a Etapa 1 criar o ambiente.
- **Log de acesso do uvicorn** não está em JSON (sai no formato padrão do uvicorn; não contém corpo
  nem cabeçalhos). Unificar com structlog fica para quando houver rotas com dados.
- Alvos do `Makefile` (`test`, `lint`, `typecheck`) rodam dentro do contêiner `api`; `format` roda
  no host porque altera arquivos do repositório.

### Revisão 0

**Riscos observados fora dos critérios**

- **MinIO deixou de ser mantido.** As imagens oficiais sumiram do Docker Hub e do Quay, o repositório aparece como arquivado em 2026, e a última imagem publicada carrega CVE conhecida. O executor usou o fork `pgsty/minio` fixado por digest, que é uma escolha razoável de curto prazo, mas é dependência de terceiro sem garantia de manutenção. O código da aplicação só conversa com a API S3, então trocar o servidor é barato agora e caro depois. Decisão para o responsável técnico antes da Etapa 4 (ingestão), que é a primeira que grava objetos.
- **Portas 8000 e 8080 ocupadas na máquina do piloto.** Sem impacto no código; o `.env` local usa 18000.
- **Log de acesso do uvicorn fora do JSON.** Sem conteúdo sensível por ora; unificar quando houver rotas com dados.
- **Alembic não inicializado.** Correto, porque não há modelos. A Etapa 1 deve criar `alembic.ini` e a pasta de migrações.

## Etapa 1 — Esquemas de dados

### 1 — Esquemas de dados

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

## Etapa 2 — Motor de validações

### 2 — Motor de validações e as três validações do piloto

- Feriados do TJGO **reais**: não há portaria conferida; `tjgo.yaml` é provisório e marcado
  "a confirmar". Só 2026 está preenchido em `nacionais.yaml`.
- Pronúncia, acórdão e causas suspensivas da prescrição (fora do escopo da v1; aparecem como
  limitação na explicação e em `valores.limitacoes`).
- Súmula 310 STF (intimação na sexta), prazos especiais e exceções do recesso para réu preso:
  registrados como conferência manual.
- Execução por réu (`por_reu`) existe no modelo, mas o motor roda sobre o modelo recebido;
  quem chama decide recortar por réu.
- `README.md` não foi alterado (arquivo da Etapa 0, fora da lista permitida).

### Revisão 2

**Trabalho pendente gerado por esta etapa**

1. **Adaptador validações ↔ domínio (pequeno, antes da Etapa 4).** O executor diz que basta trocar o import, mas não é exato: em `lupa.dominio.esquemas`, `id` é `UUID` e não `str`, `evidencias` é tupla, `Achado` exige `processo_id` e `id`, e `Fato.valor` volta do banco com datas como string ISO. É preciso uma função `para_modelo(fatos_dominio) -> ModeloProcesso` e outra `para_dominio(achado, processo_id) -> Achado`, com teste de ida e volta usando a fixture `fabrica_fato` do `tests/conftest.py`. Só então os esquemas locais de `modelo.py` podem ser removidos.
2. **Tempestividade quando a defesa recorre exige as duas intimações (réu e defensor).** Faltando uma, o resultado é `verificar`. É a leitura conservadora do art. 392 e está documentada, mas vai gerar muitos "verificar" em réu solto intimado só pelo defensor. O gabinete decide se mantém.
3. **Prescrição após a sentença usa a pena em abstrato.** Depois da sentença condenatória, a prescrição que importa costuma ser pela pena aplicada (retroativa e intercorrente). Como a pena em abstrato é maior ou igual à aplicada, o cálculo atual nunca gera alarme falso, mas pode deixar de apontar prescrição. A limitação está no guia; a validação pela pena aplicada é candidata à próxima rodada do catálogo.
4. **Calendários provisórios.** `tjgo.yaml` está marcado como provisório e `nacionais.yaml` cobre só 2026. Antes do piloto com autos reais, o gabinete substitui pelos calendários oficiais e o recesso do art. 798-A recebe as exceções de réu preso.
5. **Súmula 310 do STF e prazos especiais** não são aplicados, e o guia avisa. Entram como regras de dados quando o gabinete confirmar o texto.

## Etapa 3 — Autenticação, papéis e auditoria

### 3 — Autenticação, papéis e auditoria

- **Base GeoLite2:** exige conta na MaxMind. O caminho de instalação está no README; os testes
  usam um leitor falso.
- **Desenho do QR:** fica para a interface (ver decisão 3).
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

### Revisão 3

**Pendências para Victor**

- **GeoLite2.** A localização aproximada por IP depende da base da MaxMind, que exige conta gratuita e aceite de licença. Sem ela o campo fica `desconhecida`. O README explica como obter e onde colocar.
- **Variáveis de produção.** `LUPA_DB_USUARIO_APP`, `LUPA_DB_SENHA_APP`, `LUPA_ADMIN_USUARIO` e `LUPA_ADMIN_SENHA` precisam de valores reais no ambiente do piloto; no dev já estão configuradas com valores fictícios.
- **Dependências transitivas.** `geoip2` trouxe `aiohttp` e `requests`. Aceitável, mas aumenta a superfície; vale reavaliar na Etapa 7 se a resolução por arquivo `.mmdb` pode usar só `maxminddb`.

**Observações menores**

- Rota `GET /processos/{id}` criada como mínimo para os testes de 404 e de acesso do admin; será substituída pelas rotas reais da Etapa 6.
- QR code do MFA sai como URI `otpauth://`; a interface desenha. Correto para a API.
- `requirements*.txt` regenerados no Linux; o executor reinseriu `tzdata` e `colorama` para manter instalação no Windows. Conferir na Etapa 4A se o `pip-compile` passa a rodar sempre no contêiner, para evitar esse vaivém.

## Etapa 4A — Fundações da ingestão

### 4A.1 — Adaptador validações ↔ domínio

**Pendência**

- O `.venv` do host precisa das dependências da Etapa 3 (`pyotp`, `argon2-cffi`, `geoip2`) para o
  `verificar.sh` passar inteiro no host; não instalado aqui (restrição de dependências).

### 4A.2 — Esquemas da ingestão

- Preencher `DiagnosticoArquivo` com o cenário real é da 4C.1; aqui só entidade, tabela e
  repositório.
- Estados de `em_extracao` em diante existem e entram na matriz, mas nenhum código da 4A os usa.

### 4A.3 — Fila e worker base

- Retentativa automática de jobs `falho` (falha por limite tende a repetir); a volta é manual
  (`falho -> recebido`).
- Morte por `SIGKILL` real: simulada por uma `BaseException` lançada depois do lote 1 (não é
  capturada como `Exception`, então nada é finalizado, como num kill).

### 4A.4 — Sandbox de parsing

- Isolamento de rede no nível do kernel para o filho (ele compartilha a rede interna do worker,
  sem credenciais). Documentado em `docs/sistema/ingestao.md`; um contêiner de parser sem rede fica para
  quando a decifragem por processo (fase 2, `requisitos-v1.md` §6) exigir worker separado.
- seccomp e namespaces (exigiriam privilégios no contêiner).

### 4A.5 — Cliente de object storage

- Criptografia do lado do servidor por processo (fase 2 dos requisitos).

### 4A.6 — Recepção e lacre

- `processo.status` não muda para `em_ingestao` (fica para quando a extração existir).
- Antivírus e cifragem antes do parser (fase 2).

### 4A.7 — Inventário de zip

- ZIP dentro de ZIP não é aberto (a entrada não é PDF, logo `tipo_invalido`).

### 4A.8 — Quarentena e falhas

- A tela de quarentena (vai ler `motivo_quarentena` e `DESCRICOES`).

### 4A.9 — Observabilidade da pipeline

- Servidor Prometheus e painel Grafana no compose: o painel mínimo é o endpoint de exposição.

### 4A.10 — Ponta a ponta da fundação

- `scripts/verificar.ps1` não recebeu o passo extra (o fluxo oficial é no contêiner).

### Revisão 4A.1

**Observações**

- O `.venv` do host está sem `pyotp`, `argon2-cffi` e `geoip2`, que a Etapa 3 adicionou. O `verificar.sh` no host só volta a passar quando a Etapa 3 instalar as dependências no venv ou quando o revisor reinstalar. Dentro do contêiner, após rebuild, não há esse problema.
- O executor relatou edições que "não ficaram gravadas" durante o trabalho e precisaram ser reaplicadas. O estado final foi conferido aqui. Causa provável: sincronização do OneDrive sobre a pasta do projeto enquanto dois agentes escrevem. Vale considerar mover o repositório para fora do OneDrive antes das etapas com muitos arquivos (4B gera PDFs grandes).

## Etapa 4B — Autos sintéticos

### 4B.1 — Esquema do gabarito

- Nada do escopo.

### 4B.2 — Textos por tipo de peça

- Múltiplos réus e concurso de crimes (o gabarito suporta; o roteiro gera um réu e um crime).

### 4B.3 — Renderização nativa

- Leiaute em duas colunas (fica para o teste de ordem de leitura da 4C.5).

### 4B.4 — Renderização digitalizada

- **CER de OCR de referência por nível**: não há Tesseract no host nem na imagem (`which tesseract`
  vazio nos dois), e instalar pacote de sistema muda o `Dockerfile`, que não é desta etapa. O
  harness (4B.10) já mede CER por nível de degradação; a meta e a medição ficam para a 4C.6, que
  instala o Tesseract.

### 4B.5 — Páginas híbridas, vazias e capas

- Tabela como imagem (a assinatura cobre o caso de bloco localizado em imagem).

### 4B.8 — Injeções por vetor

- Unicode de direção (RTL) e cadeia entre documentos (vetores de risco baixo na tabela).

### 4B.9 — Processos de referência

- Geração dentro do contêiner (rodou no host para gravar direto na pasta do host sem copiar do
  contêiner, como pedem as regras).

### 4B.10 — Harness de medição

- Matriz de confusão de tipo de página (fica para a 4C.4, que precisa dela).

### Revisão 4B

**Pendência para Victor**

A pasta `.sinteticos/` tem 4,7 GB e está dentro do OneDrive, então vai sincronizar e consumir cota. Duas opções: excluir a pasta da sincronização nas configurações do OneDrive, ou definir `LUPA_SINTETICOS_DIR` para um caminho fora do OneDrive e regerar com `python scripts/gerar_autos.py referencia` (12 minutos). Sem decisão, fica como está.

## Etapa 4C — Diagnóstico e páginas

### 4C.1 — Diagnóstico do contêiner

- Diagnóstico do ZIP custa ~0,8 s por entrada (um filho do sandbox por PDF). Aceitável no piloto; agrupar entradas num filho fica para 4F.8 (cache/reprocessamento).

### Revisão 4C

**Riscos e itens para etapas seguintes**

1. **Tempo de OCR.** 882 segundos por mil páginas digitalizadas com 4 lotes de 8 páginas. Um processo de 5.000 páginas majoritariamente digitalizado leva cerca de 75 minutos. Aceitável no piloto, mas o dimensionamento do worker (quantidade de filhos, CPU) precisa de decisão antes do uso real; registrar em 4F.9.
2. **Diagnóstico de ZIP lento**: 0,8 s por entrada. Com 878 entradas, 12 minutos só para diagnosticar. Investigar na 4E (provavelmente abrir cada PDF inteiro para ler o cabeçalho; basta ler as primeiras páginas).
3. **Teto por gabinete vale por réplica de worker.** Com várias réplicas, precisa de semáforo no Redis. Fica para quando houver mais de um worker.
4. **Reprocessamento automático ao mudar a versão do extrator** e cache por sha256 entre processos ficam para 4F.8, como previsto.
5. **Imagens decorativas opacas** (logotipo JPEG) em páginas nativas levam à abstenção e custam OCR. Sem perda de conteúdo. A calibração com o Projudi (4F.10) mede a frequência.
6. **Texto fora da página e girado** só vão ao OCR; a marcação é da 4D.1.

## Etapa 4D — Saneamento

### 4D.1 — Texto oculto

- Fundo de outra cor (texto da cor de um retângulo desenhado atrás): não detectado; a divergência OCR × nativo da 4C cobre parte. Comparar com a cor do pixel renderizado fica para quando houver caso real.

### 4D.2 — Metadados e anotações

- Links (URI) e JavaScript do PDF não são listados (também não entram no texto).

### 4D.6 — Idioma inesperado

**Limitações (registradas no YAML e em `docs/sistema/ingestao.md`)**

- Frases com menos de 8 palavras não são avaliadas; o espanhol divide muitas palavras com o português e só dispara em frase claramente espanhola; outros idiomas não são detectados.

### 4D.10 — Painel de flags e regressão

- Resumo por **peça** para o dossiê: peças só existem na 4E; o resumo por arquivo e por página está pronto.
- A migração 0005 não foi aplicada ao banco de desenvolvimento (que está na 0003): rodar `docker compose exec api alembic -c src/lupa/migrations/alembic.ini upgrade head` antes de usar o worker com ele. Os testes migram o banco de teste até a 0005.

## Etapa 4E — Fronteiras e índice

### 4E.1 — Sinais de fronteira

- Reinício de numeração e cabeçalho novo não ocorrem nos sintéticos (folhas contínuas,
  cabeçalho único); estão implementados e testados com páginas fabricadas.

### 4E.10 — Índice no modelo e na API

- Divergências do cenário com índice não chegam a zero (22/2.825): ver 4E.3.
- Calibração com processo real (Projudi) fica para 4F.10.
- O teste de API reprocessa o PDF sintético em cada um dos 4 testes (≈ 45 s cada); dá para
  compartilhar o processamento quando as fixtures de banco aceitarem escopo maior.

### Revisão 4E

**Observações sobre as métricas**

- Os dez processos não têm reinício de numeração nem cabeçalho novo entre peças; esses sinais estão implementados e testados só com páginas fabricadas. A calibração com o Projudi (4F.10) é onde eles serão exercitados de verdade.
- `tipo_data` coincide com o gabarito em 31%, porque o gabarito rotula como protocolo ou juntada datas que no texto só aparecem na assinatura. Não é critério; vale ajustar o gabarito na 4F ou aceitar a semântica do extrator.
- Os erros de data e origem vêm todos do nível forte de degradação do OCR. São os mesmos casos que o relatório da 4C.6 previu.

## Etapa 4F — Eventos e ponta a ponta

### 4F.1 — Padrões de data

- Datas sem ano ("15 de maio") e intervalos ("de 10 a 15/05/2014") não são datas para a
  extração; o segundo dá só `15/05/2014`.

### 4F.2 — Extratores por tipo de peça

- Causas de aumento e diminuição e concurso de crimes na pena máxima (limitação já documentada
  nas validações).
- Recurso do assistente de acusação e prazos especiais (o catálogo não conhece).

### 4F.3 — Evidência obrigatória

- `bbox` da evidência não é preenchida (as coordenadas por linha estão em
  `pagina.coordenadas`; a tela da Etapa 6 pode calcular).

### 4F.4 — Validação cruzada

- A reconferência não pega o erro de OCR que troca um dígito por outro (o literal errado está no
  texto). Foi a causa das 2 datas erradas da 4F.9 (semente_04, nível forte de degradação). Mitigação
  possível depois: cruzar a data com o dia da semana ou com a data da peça (4E.6).

### 4F.5 — Réus e pseudonimização

- Réu qualificado fora da denúncia (aditamento, termo de interrogatório) não é identificado.
- Cifragem de `reu_identidade` (fica para quando houver chave por gabinete, Etapa 1).

### 4F.6 — Gravação de fatos

- Gravação em lote com um único `INSERT` (cada fato usa `salvar_fato`, que já é a interface do
  domínio; o maior processo de referência tem 50 fatos).

### 4F.7 — Execução do catálogo

- Reexecução automática do catálogo quando o assessor corrige um fato (Etapa 6).

### 4F.8 — Cache e reprocessamento

- Reaproveitar páginas de uma entrada de ZIP igual a um PDF já enviado (o cache é pelo hash do
  arquivo enviado, não por entrada).

### 4F.9 — Ponta a ponta nos processos de referência

- OCR real dos processos 03 a 10 (reaproveitado, como descrito).
- Upload pela rota HTTP.

### 4F.10 — Calibração com o processo real

- A calibração em si (depende do arquivo real); a seção "Registro" está vazia.

## Etapa 5 — Agente e chat

### 5.1 — Contrato do agente

- Aprovação formal do contrato pelo responsável técnico.

### 5.2 — Ferramentas de leitura estruturada

- Evento `busca` por chamada de `buscar_texto`: a chamada já fica em `chamada_modelo` e o termo seria conteúdo.

### 5.3 — Ferramenta de cálculo

- Nada.

### 5.4 — Válvula de escape

- Imagem da página para o modelo (visão): fora do escopo.

### 5.5 — Montagem de contexto e prompts

- Pseudonimização só do nome completo e do CPF; nome parcial (só sobrenome) passa. Fica com a anonimização na origem (TODO da seção 11 dos requisitos).

### 5.6 — Conferência de citações

- Marcar o processo `em revisão` no incidente (prompt-injection.md §8): o status do processo é da ingestão; fica para o painel da Etapa 6.

### 5.7 — Política de recusa

- Classificador por modelo: fora; as regras atingem as metas e são determinísticas.

### 5.8 — Suíte de injeção do agente

- Rodar a suíte com o modelo real (exige credencial).

### 5.9 — Registro e custo

- Custo em dinheiro por chamada (`total_cost_usd`): não gravado; os tokens bastam para o relatório de uso.

### 5.10 — Dossiê gerado

- Resumo narrativo do processo inteiro: fora (só por peça).

## Etapa 6 — Interface web

### 6.1 — Esqueleto do front

**Fora do escopo desta subetapa**

CSP, HSTS e demais cabeçalhos de segurança completos (6.10; já há `nosniff`, `Referrer-Policy`,
`X-Frame-Options`). Alternância manual de tema (só segue o sistema).

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

### 6.3 — Gestão de usuários

**Fora do escopo**

Editar nome de usuário ou mudar papel (a API não oferece); listar sessões ativas; confirmação
antes de desativar (a ação é reversível pela reativação e auditada).

### 6.4 — Lista e upload de processos

**Fora do escopo**

Arrastar e soltar; vários arquivos em paralelo (um envio por vez); retomar envio interrompido
(o envio é refeito do zero; o SHA-256 evita duplicar o conteúdo já lacrado); websockets (o
polling para quando nada está em processamento). O processo novo fica com `status=criado` até o
worker atualizá-lo; a situação mostrada vem de `job_ingestao`.

### 6.5 — Dossiê e linha do tempo

**Fora do escopo**

Edição da ficha; exportação do dossiê em PDF; filtro da linha do tempo por tipo.

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

### 6.7 — Tela de validações

**Fora do escopo**

Desfazer correção (corrige-se de novo o fato vigente); editar ou apagar anotação; correção de
fato que não tenha evidência (todo fato tem ao menos uma); escolha da data de referência das
validações na tela (usa a data do dia).

### 6.8 — Chat (com o item 3 da revisão 5)

- Teto por chamada continua com status `descartada` (contrato da Etapa 5); a interface mostra o
  texto do limite. O rótulo "Limite de uso atingido" aparece no teto de conversa/processo.
- Depois do E2E a API fica com o cliente falso até a próxima subida sem a variável.

### 6.9 — Tela de auditoria (com o item 5 da revisão 5)

- Seleção de usuário/processo por nome (a API de auditoria trabalha com ids).
- Custo dos resumos do dossiê não entra no relatório por usuário (não têm conversa).

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

## Etapa 7 — Criptografia, backup e guias

### 7.1 — Decisão do object storage

- Assinatura do responsável técnico.
- Teste de compatibilidade do `ArmazenamentoS3` contra Garage/RustFS (só se o plano C for adotado).

### 7.2 — Cofre de chaves (HashiCorp Vault)

- TLS no listener, auto-unseal e repartição das chaves de unseal (produção; ver
  `docs/sistema/criptografia.md`). Reiniciar o Vault sela o cofre: rodar o script de novo.

### 7.3 — Chave de dados por processo

- Zerar a memória da DEK: em Python `bytes` é imutável; o contexto só descarta a referência.
- Nos testes antigos que criam vários processos numa sessão e depois gravam páginas, o processo
  ativo é o último criado (as páginas abrem normalmente; em produção o processo ativo é sempre o do
  caminho ou do job).

### 7.4 — Cifra dos originais

- Objetos gravados em claro antes da 7.4 no MinIO de desenvolvimento não foram recifrados (são
  lidos como legado); reenvio ou descarte resolve.
- `ArmazenamentoS3.ler` continua lendo o objeto inteiro em memória (comportamento anterior).

### 7.5 — Cifra de colunas

- Busca por índice (sem ILIKE não há índice de texto; o teto limita o custo em processos grandes).
- `hash_texto`/`hash_trecho` continuam em claro (SHA-256 necessário às citações).

### 7.6 — Identidades dos réus

- `identidade_lida` sem `usuario_id` (o pseudonimizador não recebe o ator); o processo e o
  instante identificam a requisição na trilha.

### 7.7 — Exclusão criptográfica

- Backups do banco anteriores ao descarte ainda guardam o envelope da DEK (a política de
  retenção da 7.8 decide quando somem).
- A listagem do cache de renderização percorre o prefixo `renderizacao/` inteiro (aceitável no piloto).

### 7.8 — Backup cifrado

**Fora de escopo / pendente**

- Teste automático do caminho de recusa por falta de espaço (não há como simular disco cheio
  com bind mount sem tocar o host); conferido por leitura e pelo log.
- A imagem `lupa-backup:local` ainda cria `/trabalho` (inofensivo, não é mais usado); remover no
  próximo rebuild.
- Ligar o snapshot do Vault quando o serviço existir.

### 7.9 — Guias do assessor e do desembargador

**Pendente**

- Leitura por um assessor humano de fora do projeto (critério do roteiro) continua a fazer no piloto.

### 7.10 — Documentação de operação

- Exclusão dos 344 objetos órfãos em claro (decisão do responsável técnico).
- Backup real do Vault e ensaio de restauração do Vault.
- TLS no Vault, auto-unseal, divisão das partes, TLS entre serviços, certificado real: pendências
  de produção documentadas (8.1).
- Revisão 7.1-7.9, item 6 (tela do valor corrigido) e item 8 (leitura dos guias por assessor
  externo): Etapa 8.

### Revisão 7.10

**Decisões e pendências para Victor antes do piloto**

1. **344 objetos órfãos em claro no storage de desenvolvimento**, de processos sintéticos já removidos do banco. Não há chave para recifrá-los e a exclusão é irreversível, por isso o executor não apagou. Recomendação: apagar antes do piloto; são só dados sintéticos. O script de descarte não os alcança porque não há processo; basta um `mc rm` ou um pequeno script com lista por prefixo.
2. **Vault em produção**: TLS, auto-unseal ou divisão das partes de unseal entre pessoas, backup frio do volume (o Vault usa storage em arquivo, então `raft snapshot` não se aplica). Tudo documentado como pendente para 8.1.
3. **Certificado real no proxy** e porta direta da API não publicada (8.1).
4. **Prazos de comunicação de incidente**: o manual não cita artigos nem prazos porque `requisitos-v1.md` não os fixa; manda avisar Victor e o desembargador no mesmo dia e remete aos documentos de conformidade da 8.2.
5. Assinatura da decisão do object storage (`docs/decisoes/object-storage.md`).

## Etapa 8 — Piloto

### 8.1 — Ambiente de piloto

**Fora do escopo ou pendente**

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

- Termos atuais da API da Anthropic (treino, retenção, local de processamento): não consultados; ficam no checklist (item 6).
- Se a pseudonimização cobre nomes de vítimas e testemunhas além do réu: registrado como verificação técnica no aviso.
- Os PDFs de pesquisa da raiz não foram necessários para os fundamentos citados.
