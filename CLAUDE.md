# Lupa — Convenções do projeto

Regras que valem para todo código do repositório. As seções de "Linguagem e estilo" a "Segurança" vieram do plano de execução da v1; "Versão 0.2" e "Desenvolvimento" regem o trabalho atual.

## Versão 0.2

- A fonte da verdade é [a especificação da 0.2](docs/especificacao/0.2/especificacao.md); o código deriva dela. Divergência entre código e especificação é bug do código ou mudança de especificação aprovada antes.
- Ordem fixa, cada fase só começa com a anterior aprovada pelo usuário: especificação, plano (`docs/planos/`), tarefas (`docs/planos/tarefas_0.2.md`), implementação tarefa por tarefa com TDD.
- Cada tarefa cita o requisito que atende (`RF-<ÁREA>-NN` ou `RNF-NN`). Cada teste novo cita o requisito na docstring. Commit e PR citam a tarefa.
- Escopo: um único gabinete de desembargador, área cível. Não há `gabinete_id`, RLS por gabinete, papel administrador, pseudonimização, bloqueio de sigiloso, Redis, monitoramento nem backup; nada disso é reintroduzido sem mudança de especificação.
- Tudo do frontend e do back que o atende (API, acesso, auditoria, agente) fica em `intranet/`. Tudo da pipeline de dados (worker, ingestão, eventos, validações, modelo e migrations do Data Vault, sintéticos) fica em `pipeline/`.
- Transição: enquanto a tarefa do plano que move um diretório ou remove um componente não for concluída, os caminhos e comandos citados abaixo (`src/lupa/`, `tests/`, `front/`, `make verificar`) valem como estão. A tarefa que move ou remove atualiza este arquivo no mesmo commit.

## Linguagem e estilo

- Python 3.12. PEP 8 verificado por `ruff` com `line-length = 100`. Tipagem completa verificada por `mypy --strict`.
- Docstrings no estilo Google em todo módulo, classe e função pública, verificadas por `ruff` com a regra `D` e convenção `google`.
- Funções curtas com uma responsabilidade. Nomes em português para conceitos jurídicos (`peca`, `achado`, `evidencia`) e em inglês para infraestrutura (`repository`, `session`, `handler`). Sem comentários explicando o que o código faz; o nome e a docstring fazem isso.
- Sem lógica em `__init__.py`. Sem imports circulares. Sem `print`; logging estruturado em JSON.

## Testes

- `pytest` com cobertura mínima de 90% em `lupa`, medida por `pytest-cov`.
- Testes nomeados pelo comportamento: `test_apelacao_interposta_no_sexto_dia_e_intempestiva`.
- `scripts/verificar.sh` roda lint, formatação, tipagem e testes, parando no primeiro erro.

## Contêineres

- Tudo roda via `docker compose`. Nenhuma instrução de execução depende de instalação na máquina do desenvolvedor.
- Imagens com usuário não root, `python:3.12-slim` como base, dependências fixadas em `requirements.txt` com hashes.

## Segurança

- Segredos só por arquivo `.env` ignorado pelo git ou pelo Vault. Nunca em código ou em imagem.
- Nenhum conteúdo de autos, senha, token ou texto de pergunta entra em log.

## Entrega de cada tarefa

- Marque a tarefa em `docs/planos/tarefas_0.2.md` com o requisito atendido, o comando para rodar os testes e a saída resumida (vermelho inicial e verde final).
- Decisão que o plano não previa para a tarefa e volta ao usuário antes de seguir.
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
    operacao/       manual do responsável técnico, backup e runbooks
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

- Antes de escrever o plano, levante todas as decisões e pergunte todas ao usuário. O plano não
  sai com decisão "pendente: usuário (fase N)"; adiamento só por decisão explícita dele,
  registrada.
- O plano abre com a seção "O que muda": tabela `Objeto | Antes | Depois` (cada tabela, coluna,
  índice, função ou view do banco, com o tipo), tabela `Arquivo | Ação` e lista "O que
  não muda". No plano que recria o banco do zero a tabela é `Objeto | Depois`, e o que existia na
  0.1 entra numa lista única de objetos removidos.
- Cada fase do plano cita os requisitos da especificação que atende.
- Cada fato aparece uma vez. Problemas e decisões numerados; fases de uma linha que citam P/D.
  Sem seção de motivação, história, justificativa ou resultado previsto.
- Seção "Passo a passo do algoritmo": passos numerados, na ordem de execução, um por linha; cada
  passo informa entrada, ação e saída; desvios, condições de parada e tratamento de erro aparecem
  como passos próprios; um bloco por algoritmo. Fica no plano ou em
  `docs/planos/plano_<tema>_execucao.md`, junto com a lista de arquivos e o checklist de testes.
- Se o algoritmo mudar durante a implementação, atualize a seção.
- Execução (subida no servidor do piloto) em no máximo 3 etapas, por exemplo: commit e PR;
  `docker compose up -d --build --wait`; `alembic upgrade head` no contêiner `api`, na ordem de
  `docs/operacao/operacao.md` (Atualização de versão). Sem passo de conferência manual no banco;
  o risco real é coberto por teste de integração antes.
- Revisão de plano a partir de comentários do usuário: altere só os itens citados, mantendo a
  numeração e o restante.

### Banco de dados

- Migration só quando prevista no plano. Revisão Alembic em
  `src/lupa/migrations/versions/vNNNN_<tema>.py`, com `upgrade` e `downgrade`; quando as
  operações forem longas, ficam em `src/lupa/migrations/esquema_vNNNN.py`, como nas existentes.
  Toda revisão tem teste que sobe e desce com o auxiliar `migrar` de `tests/conftest.py`
  (exemplo: `tests/seguranca/test_migracao_0010.py`).
- No desenvolvimento a aplicação é feita pelo agente, nunca pelo usuário, no contêiner `api`
  depois do rebuild: `docker compose exec api alembic -c src/lupa/migrations/alembic.ini upgrade
  head`. No servidor do piloto, pelo responsável técnico, na ordem de `docs/operacao/operacao.md`.
- Modelagem em Data Vault 2.0: toda tabela é hub, link ou satélite, inclusive autenticação,
  estado da ingestão e auditoria. Chave por hash da chave de negócio; só raw vault; a API lê por
  views. Correção de fato ou de peça é linha nova de satélite, nunca `UPDATE`.
- Não há `gabinete_id` nem RLS. A aplicação opera sob o papel `lupa_app`, só com DML; os
  privilégios seguem `docs/sistema/modelo-de-dados.md`.
- Coluna nova com conteúdo de autos, identidade de parte ou mensagem do chat é cifrada conforme
  `docs/sistema/criptografia.md`; nunca em claro.
- Ao escrever SQL, priorize queries legíveis e evite `SELECT *` quando não for necessário.
- Os nomes de tabelas, colunas e views são os do plano aprovado da 0.2; depois de criados, só
  mudam por plano.
- Antes de alterar um modelo, uma view ou uma consulta existente, verifique quem consome o
  resultado: rotas da API, `front/src/lib` e auditoria.

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
  `Dockerfile`, `Caddyfile`, `eslint.config.js`) sem necessidade; a reestruturação prevista no
  plano da 0.2 é necessidade, limitada ao que o plano lista. Nunca baixe o mínimo de
  cobertura nem use `# type: ignore`, `# noqa` ou exclusão de cobertura para silenciar um erro que
  o código deveria resolver.

#### Idioma

- Código: conforme "Linguagem e estilo" (português para conceitos jurídicos, inglês para
  infraestrutura).
- Documentação em português: todos os arquivos `.md`.
- Mensagens de log, de erro e textos da interface em português. No front, `describe` e `it` em
  português.

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

- SvelteKit 2 com Svelte 5 e TypeScript. Prettier e ESLint sem avisos, `svelte-check` com
  `--fail-on-warnings`.
- Lógica reaproveitada fica em `front/src/lib/`, por assunto; componente usado por mais de uma
  tela, em `front/src/lib/componentes/`. Tela só em `front/src/routes/`.

### Padrão de script

- Script novo em `scripts/` segue os existentes: docstring de módulo com o uso (`python
  scripts/<nome>.py ...`, no contêiner `api`), recusa a rodar fora do `LUPA_AMBIENTE` que lhe
  cabe quando apaga ou altera dados, saída com contagens e nunca com conteúdo de autos. Teste em
  `tests/unit/`.

### Desenvolvimento orientado a testes

- O agente principal chama o agente `tdd` (`.claude/agents/tdd.md`) para desenhar, escrever,
  executar ou revisar os testes. Envie o módulo e o comportamento esperado, ou o diff e a falha
  observada. Em uma correção, passe o caso vermelho ao responsável pela implementação e devolva a
  mudança ao `tdd` para verificar o verde e as regressões.
- Ciclo TDD: teste falhando, código mínimo para passar, limpeza; o relatório final mostra o
  vermelho inicial e o verde final.
- Correção de bug começa por um teste que reproduz o bug.
- Toda lógica nova ou alterada tem teste. Exceções admitidas: componente Svelte só de
  apresentação, chamada real ao modelo (marcador `llm`), teste de carga (marcador `carga`) e fluxo
  E2E do Playwright; cada uma entra em "revisão manual" do relatório final.
- Teste unitário valida o comportamento de função pura, sem rede, banco, Redis, MinIO, Vault nem
  modelo.
- Teste de integração (marcador `integracao`) valida o fluxo inteiro com os serviços do
  `docker-compose.yml`: PostgreSQL e MinIO reais; modelo, cofre e resolução de nomes por dublês
  que já existem (cliente roteirizado do agente, cofre em memória, `ResolvedorFalso`).
- Todos os dados são sintéticos. Nunca número de processo, nome ou trecho de autos reais em teste
  ou fixture; nunca ler `.env`, `.segredos/`, `.vault-dev/`, `.backups/`, `.backup-chaves/` ou
  `dados/` (processos reais, fora do git).
- Tempo é injetado (`relogio_fixo`, datas fixas), nunca esperado com `sleep` ou relógio real.

#### Onde ficam

- Os testes espelham `src/lupa/`: `tests/<pacote>/test_<modulo>.py`. `tests/unit/` guarda os
  testes de `config.py`, `logging.py` e dos scripts.
- Teste de migration fica na área do assunto, como `test_migracao_NNNN.py`. Backup e restauração
  em `tests/backup/` (marcador `backup`, só com `LUPA_VERIFICAR_BACKUP=1`).
- Front: unitários ao lado do módulo, `front/src/lib/**/<nome>.test.ts`; ponta a ponta em
  `front/e2e/testes/`, fora do ciclo.
- Fixtures e auxiliares compartilhados ficam em `tests/conftest.py` e no `conftest.py` da área
  (`fabrica_fato`, `fabrica_processo`, `sessao`, `cliente`/`app_teste`, `logar`,
  `gerar_numero_cnj`, `criar_pagina`, `relogio_fixo`, `resolvedor_falso`); ponto de partida
  obrigatório antes de criar outro.
- Marcadores: `integracao`, `injecao`, `agente`, `carga`, `llm`, `backup`. A configuração padrão
  exclui `carga` e `llm`.

#### Regras

- Cada arquivo de teste passa rodando sozinho com `--no-cov`; a cobertura mínima de 90% é medida
  só na suíte completa.
- Teste pulado não é verde. No `scripts/verificar.sh` as suítes com serviço rodam com
  `LUPA_EXIGIR_INTEGRACAO=1`, sem skip.
- Interpretador: Python 3.12 único. O ambiente completo é o contêiner `api`, que copia `src/` e
  `tests/` no build: `docker compose up -d --build --wait api` antes de rodar, senão o contêiner
  testa código antigo. O `.venv` local serve só a testes sem banco.
- Nunca apagar teste, afrouxar asserção, marcar `skip` ou `xfail` para chegar ao verde. Teste de
  funcionalidade que o plano aprovado remove sai no mesmo commit do código removido, citando a
  tarefa.
- Teste existente só muda junto com a regra que ele fixa, no mesmo commit, com o motivo no plano;
  divergência sem mudança de regra é bug e para a tarefa.

### Validação obrigatória

Antes de concluir uma tarefa:

1. Revise o diff completo.
2. Verifique se apenas arquivos relacionados ao escopo foram alterados.
3. Confirme que não foram criadas migrations acidentalmente em `src/lupa/migrations/` e que
   `requirements*.txt` só mudou por `make lock`.
4. Quando alterar `src/` ou `tests/`, rode no contêiner `api`, depois do rebuild: `ruff check`,
   `ruff format --check` e `mypy` sobre `src tests` e `python -m pytest` com cobertura, incluindo
   os testes criados na tarefa. `make verificar` (integração, injeção, front e cabeçalhos) é
   obrigatório quando a mudança toca ingestão, agente, segurança, migrations ou proxy.
5. Quando alterar `front/`, rode `docker build --target verificacao front` (ou `npm run verificar`
   em `front/`); quando alterar uma tela, reinicie o preview e confira no navegador; quando alterar
   fluxo coberto pelo E2E, `bash front/scripts/e2e.sh` (reseta o administrador do banco de
   desenvolvimento).
6. Quando alterar Python e a suíte não puder rodar, execute ao menos
   `python -m compileall -q src tests scripts`.
7. Informe claramente qualquer validação que não pôde ser executada.
