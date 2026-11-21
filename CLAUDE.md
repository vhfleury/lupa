# Lupa — Convenções do projeto

Regras que valem para todo código do repositório. As seções de "Linguagem e estilo" a "Segurança" vieram do plano de execução da v1; "Versão 0.2" e "Desenvolvimento" regem o trabalho atual.

## Versão 0.2

- A fonte da verdade é [a especificação da 0.2](docs/especificacao/0.2/especificacao.md); o código deriva dela. Divergência entre código e especificação é bug do código ou mudança de especificação aprovada antes.
- Ordem fixa, cada fase só começa com a anterior aprovada pelo usuário: especificação, plano (`docs/planos/`, uma fase por tarefa), lista de tarefas (`docs/planos/tarefas_0.2.md`), implementação fase por fase com TDD, num único PR por plano.
- Cada tarefa cita o requisito que atende (`RF-<ÁREA>-NN` ou `RNF-NN`). Cada teste novo cita o requisito na docstring. Commit e PR citam a tarefa.
- Escopo: um único gabinete de desembargador, área cível. Não há `gabinete_id`, RLS por gabinete, papel administrador, pseudonimização, bloqueio de sigiloso, Redis, monitoramento nem backup; nada disso é reintroduzido sem mudança de especificação.
- Tudo do frontend e do back que o atende (API, acesso, auditoria, agente) fica em `intranet/`. Tudo da pipeline de dados (worker, ingestão, eventos, validações, modelo e migrations do Data Vault, sintéticos) fica em `pipeline/`.
- A fila é `v_fila_ingestao`. O advisory lock de sessão e o processamento usam a mesma conexão física. A verificação de responsáveis usa `link_processo_responsavel`, `v_responsavel` e as rotas da intranet.

## Linguagem e estilo

- Python 3.12. PEP 8 verificado por `ruff` com `line-length = 100`. Tipagem completa verificada por `mypy --strict`.
- Docstrings no estilo Google em todo módulo, classe e função pública, verificadas por `ruff` com a regra `D` e convenção `google`.
- Funções curtas com uma responsabilidade. Nomes em português para conceitos jurídicos (`peca`, `achado`, `evidencia`) e em inglês para infraestrutura (`repository`, `session`, `handler`). Sem comentários explicando o que o código faz; o nome e a docstring fazem isso.
- Sem lógica em `__init__.py`. Sem imports circulares. Sem `print`; logging estruturado em JSON.

## Testes

- `pytest` com cobertura mínima de 90% em cada pacote (`lupa_pipeline`, `lupa_api` e `lupa_web`), medida
  por `pytest-cov`.
- Testes nomeados pelo comportamento: `test_apelacao_interposta_no_sexto_dia_e_intempestiva`.
- `scripts/verificar.sh` roda no host lint, formatação, tipagem e testes dos dois pacotes nos
  contêineres, parando no primeiro erro.

## Contêineres

- Tudo roda via `docker compose`. Nenhuma instrução de execução depende de instalação na máquina do desenvolvedor.
- Imagens com usuário não root, `python:3.12-slim` como base, dependências fixadas em `pipeline/requirements*.txt` e `intranet/api/requirements*.txt` com hashes.

## Segurança

- Segredos só por arquivo `.env` ignorado pelo git. Nunca em código ou em imagem.
- Nenhum conteúdo de autos, senha, token ou texto de pergunta entra em log.

## Entrega de cada tarefa

- Cada tarefa é uma fase do plano. Ao concluir, preencha o "Entregue" da fase no plano com o comando para rodar os testes e a saída resumida (vermelho inicial e verde final), e marque a caixa da tarefa em `docs/planos/tarefas_0.2.md`.
- Decisão que o plano não previa para a fase volta ao usuário antes de seguir e entra no plano, na seção de decisões.
- `docs/etapas/ETAPAS.md` é o histórico da v1 e não recebe entregas novas.

## Desenvolvimento

### Estrutura da documentação

```
docs/
    README.md       índice de tudo que está em docs/; todo documento novo entra nele
    arquitetura.md  limite do sistema, componentes e uma execução de ponta a ponta, como está hoje
    adr/            registros de decisão de arquitetura, um arquivo NNNN-titulo.md por decisão
    runbooks/       procedimentos operacionais, um arquivo <verbo>-<objeto>.md por operação
    planos/         planos de mudança, escritos antes da implementação; tarefas_0.2.md
    especificacao/  0.2/especificacao.md é a vigente; os demais arquivos são da v1
    sistema/        como cada parte funciona hoje (modelo de dados, ingestão, agente, front...)
    decisoes/       registro.md: decisões tomadas e o que cada uma substitui
    dividas/        análises de bugs e dívidas técnicas e os registros das correções
    analises/       análises exploratórias, levantamentos e relatórios datados (md ou pdf)
    incidentes/     post-mortems: data, sintoma, causa, correção e pendências
    operacao/       manual do responsável técnico e runbooks
    etapas/         ETAPAS.md reúne relatórios, pendências e conformidade por etapa da v1
    conformidade/   CONFORMIDADE.md reúne as minutas LGPD e Res. CNJ 615/2025
    guias/          guias dos usuários; capturas de tela em imagens/
    contexto/       pesquisa usada no desenho
```

- Todo plano novo deve ser criado em `docs/planos/`.
- Criar um plano não abre branch, commit nem PR: o arquivo fica na branch atual, sem commit;
  branch e PR só na implementação.
- Requisito novo ou alterado entra em `docs/especificacao/0.2/especificacao.md`, com
  identificador e critério de aceite, e é aprovado pelo usuário antes do plano. Documento de
  desenho novo: em `docs/especificacao/0.2/` quando define requisito, em `docs/sistema/` quando
  descreve como uma parte funciona. Mudança em comportamento já descrito
  atualiza o documento de `docs/sistema/` correspondente.
- Decisão nova vai em `docs/decisoes/registro.md`, na seção de decisões posteriores à v1, dizendo
  o que substitui. Decisão que define a arquitetura ganha também um ADR em
  `docs/adr/NNNN-titulo.md`, no modelo de `docs/adr/README.md`; quando substitui outra, é um ADR
  novo ligado ao anterior.
- Toda análise de dívida técnica ou registro de correção novo deve ser criado em `docs/dividas/`.
- Toda análise de dados, levantamento ou relatório novo deve ser criado em `docs/analises/`, com a
  data no nome do arquivo.
- Todo incidente novo deve ser registrado em `docs/incidentes/`, com a data no nome do arquivo. Os
  procedimentos de resposta continuam em `docs/operacao/operacao.md`.
- Todo runbook novo deve ser criado em `docs/runbooks/`, com verbo e objeto no nome, no formato
  descrito em `docs/runbooks/README.md`. Os manuais do responsável técnico continuam em
  `docs/operacao/`.
- Mudança de componente, de chave ou de comportamento em falha atualiza `docs/arquitetura.md`.
  Mudança que o usuário ou o operador percebe entra em `CHANGELOG.md`, na seção `Não publicado`.

### Conteúdo obrigatório de um plano

- Antes de escrever o plano, levante todas as decisões e pergunte todas ao usuário, inclusive
  as que só apareceriam durante uma fase (efeito em dados gravados, versões, ids, contratos entre
  pacotes). O plano não sai com decisão "pendente: usuário (fase N)"; adiamento só por decisão
  explícita dele, registrada. Para cada risco que uma fase pode revelar, o plano já diz o que
  fazer (por exemplo: "se o teste de igualdade falhar, a fase sai do plano e vira dívida").
- Cada tarefa é uma fase do plano, numerada `F<n>` na ordem de execução. Não há quebra posterior
  em tarefas: `docs/planos/tarefas_0.2.md` recebe só a lista de caixas que aponta para as fases.
- O plano é montado para distribuir as fases entre agentes. Cada fase traz, numa linha cada:
  requisito; agente que implementa (`executor`, `tdd` ou especialista) e agentes que revisam;
  arquivos que toca; fases de que depende; fases com que pode rodar em paralelo (sem arquivo em
  comum e sem depender do resultado); Vermelho (`<arquivo>::<teste>`); Verde; Pronto quando; e
  "Entregue", preenchido ao concluir.
- O plano abre com a seção "O que muda": tabela `Objeto | Antes | Depois` (cada tabela, coluna,
  índice, função ou view do banco, com o tipo), tabela `Arquivo | Ação` e lista "O que
  não muda". No plano que recria o banco do zero a tabela é `Objeto | Depois`, e o que existia na
  0.1 entra numa lista única de objetos removidos.
- Cada fato aparece uma vez. Problemas e decisões numerados; cada fase cita os P/D e os
  requisitos que atende.
  Sem seção de motivação, história, justificativa ou resultado previsto.
- Seção "Passo a passo do algoritmo": passos numerados, na ordem de execução, um por linha; cada
  passo informa entrada, ação e saída; desvios, condições de parada e tratamento de erro aparecem
  como passos próprios; um bloco por algoritmo. Fica no plano ou em
  `docs/planos/plano_<tema>_execucao.md`, junto com a lista de arquivos e o checklist de testes.
- Se o algoritmo mudar durante a implementação, atualize a seção.
- Um plano, um PR: a branch do plano reúne um commit por fase e o PR para a `develop` é aberto
  na primeira fase e atualizado a cada uma.
- Execução (subida no servidor do piloto) em no máximo 3 etapas, por exemplo: merge do PR do plano;
  `docker compose up -d --build --wait`; `alembic -c pipeline/src/lupa_pipeline/migrations/alembic.ini
  upgrade head` no contêiner `api`, na ordem de
  `docs/operacao/operacao.md` (Atualização de versão). Sem passo de conferência manual no banco;
  o risco real é coberto por teste de integração antes.
- Revisão de plano a partir de comentários do usuário: altere só os itens citados, mantendo a
  numeração e o restante.

### Banco de dados

- Migration só quando prevista no plano. Revisão Alembic em
  `pipeline/src/lupa_pipeline/migrations/versions/vNNNN_<tema>.py`, com `upgrade` e `downgrade`;
  quando as operações forem longas, ficam em
  `pipeline/src/lupa_pipeline/migrations/esquema_vNNNN.py`, como nas existentes. Toda revisão tem
  teste que sobe e desce com o auxiliar `migrar` de `pipeline/tests/apoio/apoio_comum.py`
  (exemplo: `pipeline/tests/dominio/test_migracao_0001.py`).
- No desenvolvimento a aplicação é feita pelo agente, nunca pelo usuário, no contêiner `api`
  depois do rebuild: `docker compose exec api alembic -c
  pipeline/src/lupa_pipeline/migrations/alembic.ini upgrade head`. No servidor do piloto, pelo
  responsável técnico, na ordem de `docs/operacao/operacao.md`.
- Modelagem em Data Vault 2.0: toda tabela é hub, link ou satélite, inclusive autenticação,
  estado da ingestão e auditoria. Chave por hash da chave de negócio; só raw vault; a API lê por
  views. Correção de fato ou de peça é linha nova de satélite, nunca `UPDATE`.
- Não há `gabinete_id` nem RLS. A aplicação opera sob o papel `lupa_app`, só com DML; os
  privilégios seguem `docs/sistema/modelo-de-dados.md`.
- Ao escrever SQL, priorize queries legíveis e evite `SELECT *` quando não for necessário.
- Os nomes de tabelas, colunas e views são os do plano aprovado da 0.2; depois de criados, só
  mudam por plano.
- Antes de alterar um modelo, uma view ou uma consulta existente, verifique quem consome o
  resultado: rotas da API, `intranet/web/src/lib` e auditoria.

### Qualidade do código

- Prefira alterações pequenas e objetivas.
- Não crie abstrações desnecessárias.
- Utilize nomes de variáveis claros.
- Sem comentário inline. A docstring Google é obrigatória (regra `D` do `ruff`) e descreve o
  código atual, conferida afirmação por afirmação; divergência entre texto e código é sinalizada
  como possível bug. A justificativa de uma mudança vai no plano ou na mensagem de commit, não no
  código.
- Não remova código aparentemente não utilizado sem verificar suas dependências.
- Não modifique configurações globais do projeto (`pyproject.toml`, `docker-compose*.yml`,
  `Dockerfile`, `Caddyfile`) sem necessidade; a reestruturação prevista no
  plano da 0.2 é necessidade, limitada ao que o plano lista. Nunca baixe o mínimo de
  cobertura nem use `# type: ignore`, `# noqa` ou exclusão de cobertura para silenciar um erro que
  o código deveria resolver.

#### Idioma

- Código: conforme "Linguagem e estilo" (português para conceitos jurídicos, inglês para
  infraestrutura).
- Documentação em português: todos os arquivos `.md`.
- Mensagens de log, de erro e textos da interface em português.

#### PEP 8

- Siga a PEP 8 em todo código Python novo ou alterado; limite de 100 caracteres, conforme
  `pyproject.toml`.
- Nomes: `snake_case` para funções e variáveis, `PascalCase` para classes, `MAIUSCULAS` para
  constantes.
- Imports no topo do arquivo, agrupados em biblioteca padrão, terceiros e projeto (regra `I` do
  `ruff`); sem `import *`.
- Não reformate código legado fora do escopo da tarefa só para adequar à PEP 8.

#### Clean code

- Funções curtas, com uma única responsabilidade.
- Nomes que revelam a intenção; sem abreviações obscuras nem números mágicos.
- Prefira retorno antecipado a condicionais aninhadas.
- Não duplique lógica; extraia para função quando houver repetição real.
- Não capture exceções genéricas em silêncio.
- Não deixe código comentado nem sobras de depuração.

#### Front

- Django 5.2 com templates e HTMX, pacote `lupa_web` em `intranet/web/src/lupa_web/`; as mesmas
  regras de Python (ruff, mypy, docstring) valem para ele. O front fala com a API só por HTTP
  (`cliente_api.py`).
- Tela em `telas/` e `templates/`; CSS por assunto em `static/css/`. JavaScript próprio só em
  `static/js/envio.js`, `tema.js` e `visualizador.js`; sem script inline.

### Git

- Branches: `main` (versões publicadas) e `develop` (integração). Nenhum commit nem push direto
  em nenhuma das duas; tudo entra por PR.
- Branch de trabalho sai de `develop`. A de um plano é uma só, no formato `<tipo>/<tema-do-plano>`
  (exemplo: `refactor/limpeza-pipeline`); fora de plano, `<tipo>/<descricao-curta>`. Tipos:
  `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
- Commit em Conventional Commits, em português: `<tipo>(<escopo>): <resumo no imperativo>`, até
  72 caracteres na primeira linha; corpo com o porquê; rodapé `Tarefa: T<nn>` (a fase do plano)
  e, quando houver, `BREAKING CHANGE: <o que quebra>`.
- Um PR por plano, com o plano, as fases concluídas e os requisitos atendidos na descrição; sem
  PR por fase nem PRs empilhados. Mudança fora de plano é um PR de um assunto só. Merge em
  `develop` por squash, com a mensagem do squash em Conventional Commits.
- Versão: `release/x.y.z` sai de `develop`, atualiza o `CHANGELOG.md` e entra na `main` por merge
  commit; a `main` recebe a tag anotada `vx.y.z` (SemVer) e a `release` volta para `develop`.
- Sem force-push em `main`, `develop` ou branch com PR aberto de outra pessoa; sem reescrever
  histórico publicado.

### Padrão de script

- Script novo vai em `pipeline/scripts/` (quando só usa `lupa_pipeline`) ou em
  `intranet/api/scripts/` e segue os existentes: docstring de módulo com o uso (`python
  <pacote>/scripts/<nome>.py ...`, no contêiner `api`), recusa a rodar fora do `LUPA_AMBIENTE` que lhe
  cabe quando apaga ou altera dados, saída com contagens e nunca com conteúdo de autos. Teste em
  `tests/unit/` do pacote.

### Desenvolvimento orientado a testes

- O agente principal chama o agente `tdd` (`.claude/agents/tdd.md`) para desenhar, escrever,
  executar ou revisar os testes. Envie o módulo e o comportamento esperado, ou o diff e a falha
  observada. Em uma correção, passe o caso vermelho ao responsável pela implementação e devolva a
  mudança ao `tdd` para verificar o verde e as regressões.
- Ciclo TDD: teste falhando, código mínimo para passar, limpeza; o relatório final mostra o
  vermelho inicial e o verde final.
- Correção de bug começa por um teste que reproduz o bug.
- Toda lógica nova ou alterada tem teste. Exceções admitidas: template só de
  apresentação, chamada real ao modelo (marcador `llm`), teste de carga (marcador `carga`) e fluxo
  E2E do Playwright; cada uma entra em "revisão manual" do relatório final.
- Teste unitário valida o comportamento de função pura, sem rede, banco, MinIO nem
  modelo.
- Teste de integração (marcador `integracao`) valida o fluxo inteiro com os serviços do
  `docker-compose.yml`: PostgreSQL e MinIO reais; modelo e resolução de nomes por dublês
  que já existem (cliente roteirizado do agente, `ResolvedorFalso`).
- Todos os dados são sintéticos. Nunca número de processo, nome ou trecho de autos reais em teste
  ou fixture; nunca ler `.env`, `.segredos/`, `.vault-dev/`, `.backups/`, `.backup-chaves/` ou
  `dados/` (processos reais, fora do git).
- Tempo é injetado (`relogio_fixo`, datas fixas), nunca esperado com `sleep` ou relógio real.

#### Onde ficam

- Os testes espelham o pacote: `pipeline/tests/<subpacote>/test_<modulo>.py` para
  `lupa_pipeline` e `intranet/api/tests/<subpacote>/test_<modulo>.py` para `lupa_api`. Teste
  que exercita rota da API ou login fica em `intranet/api/tests/`, mesmo quando o assunto é da
  pipeline. O `tests/unit/` de cada pacote guarda os testes de `config.py`, `logging.py` e dos
  scripts.
- `lupa_api` importa `lupa_pipeline`; o contrário é proibido e
  `pipeline/tests/unit/test_dependencias.py` falha se acontecer. `lupa_web` não importa nenhum
  dos dois.
- Teste de migration fica na área do assunto, como `test_migracao_NNNN.py`.
- Front: `intranet/web/tests/` (pytest, `respx`, `pytest-django`); ponta a ponta em
  `intranet/web/tests/e2e/` (pytest-playwright, via `bash intranet/web/scripts/e2e.sh`), fora do
  ciclo.
- Fixtures e auxiliares comuns aos dois pacotes ficam em `pipeline/tests/apoio/` (no `pythonpath`
  do pytest de ambos: `apoio_comum`, `apoio_ingestao`, `apoio_arquivos`); os da intranet, em
  `intranet/api/tests/conftest.py`; depois vem o `conftest.py` da área (`fabrica_fato`,
  `fabrica_processo`, `sessao`, `cliente`/`app_teste`, `logar`, `gerar_numero_cnj`,
  `criar_pagina`, `relogio_fixo`, `resolvedor_falso`); ponto de partida obrigatório antes de criar
  outro.
- Marcadores: `integracao`, `injecao`, `agente`, `carga`, `llm`. A configuração padrão
  exclui `carga` e `llm`.

#### Regras

- Cada arquivo de teste passa rodando sozinho com `--no-cov`; a cobertura mínima de 90% é medida
  só na suíte completa.
- Teste pulado não é verde. No `scripts/verificar.sh` as suítes com serviço rodam com
  `LUPA_EXIGIR_INTEGRACAO=1`, sem skip.
- Interpretador: Python 3.12 único. Os testes da pipeline rodam na imagem do `worker` e os da
  intranet na da `api`, a partir de `/app` e com o `pyproject.toml` do pacote (`python -m pytest -c
  pipeline/pyproject.toml pipeline/tests`; `-c intranet/api/pyproject.toml intranet/api/tests`). As
  imagens copiam o código no build: `docker compose up -d --build --wait api worker` antes de
  rodar, senão o contêiner testa código antigo. O `.venv` local serve só a testes sem banco.
- Nunca apagar teste, afrouxar asserção, marcar `skip` ou `xfail` para chegar ao verde. Teste de
  funcionalidade que o plano aprovado remove sai no mesmo commit do código removido, citando a
  tarefa.
- Teste existente só muda junto com a regra que ele fixa, no mesmo commit, com o motivo no plano;
  divergência sem mudança de regra é bug e para a tarefa.

### Validação obrigatória

Antes de concluir uma tarefa:

1. Revise o diff completo.
2. Verifique se apenas arquivos relacionados ao escopo foram alterados.
3. Confirme que não foram criadas migrations acidentalmente em
   `pipeline/src/lupa_pipeline/migrations/` e que os `requirements*.txt` só mudaram por `make lock`
   (ou pelos mesmos `uv pip compile` do alvo `lock`, onde não houver `make`).
4. Quando alterar `pipeline/` ou `intranet/api/`, rode depois do rebuild, no contêiner do pacote
   (`worker` para a pipeline, `api` para a intranet): `ruff check`, `ruff format --check` e `mypy
   --config-file <pacote>/pyproject.toml` sobre `src` e `tests` do pacote, e `python -m pytest -c
   <pacote>/pyproject.toml <pacote>/tests` com cobertura, incluindo os testes criados na tarefa.
   Mudança na pipeline também roda a suíte da intranet, que a importa. `bash scripts/verificar.sh`
   (ou `make verificar`: integração, injeção, front e cabeçalhos) é obrigatório quando a mudança
   toca ingestão, agente, segurança, migrations ou proxy.
5. Quando alterar `intranet/web/`, rode depois do rebuild, no contêiner `front`: `ruff check`,
   `ruff format --check` e `mypy --config-file intranet/web/pyproject.toml` sobre `src` e `tests`,
   e `python -m pytest -c intranet/web/pyproject.toml intranet/web/tests`; quando alterar uma
   tela, confira no navegador; quando alterar fluxo coberto pelo E2E, `bash intranet/web/scripts/e2e.sh` (cria um projeto Compose temporário com contas e processos sintéticos).
6. Quando alterar Python e a suíte não puder rodar, execute ao menos
   `python -m compileall -q pipeline intranet/api`.
7. Informe claramente qualquer validação que não pôde ser executada.
