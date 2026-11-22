# Changelog

Todas as mudanças relevantes do Lupa ficam registradas aqui.

O formato segue o [Keep a Changelog 1.1.0](https://keepachangelog.com/pt-BR/1.1.0/). As datas usam
`AAAA-MM-DD`.

## Como as versões funcionam

- A versão é do monorepo inteiro: back, front, proxy e scripts sobem juntos. Os manifestos de `pipeline/`, `intranet/api/` e `intranet/web/` declaram a mesma versão, `0.2.0`.
- Esquema de numeração: [SemVer 2.0](https://semver.org/lang/pt-BR/). Enquanto a versão for `0.x`,
  uma versão menor pode quebrar compatibilidade.
- Ao publicar: num PR para o `develop`, mova as entradas de `Não publicado` para uma seção
  `## [X.Y.Z] - AAAA-MM-DD` e atualize as declarações de versão; depois do PR `develop` → `main`,
  o responsável técnico cria a tag `vX.Y.Z` no `main` e a release no GitHub.

## [Não publicado]

### Alterado

- A extração das páginas passa a rodar até dois lotes ao mesmo tempo, cada um em um processo isolado
  (`LUPA_EXTRACAO_LOTES_POR_JOB=2`; `1` volta à extração em série). A gravação das páginas de um lote
  passa a ser feita de uma vez.
- O catálogo de validações sobe para a `0.3.0` (dispensas de preparo e de mandato em
  `dispensas.yaml`). O reprocessamento regrava uma vez os fatos e os achados dos arquivos já
  processados, com o mesmo resultado e o mesmo texto. Ação: `docker compose up -d --build --wait`.
- A intranet adota o padrão visual: paleta verde (primária `#00613b`, `#4cc489` no tema escuro),
  fontes Source servidas pelo próprio front, botões, tabelas, avisos e etiquetas iguais em todas
  as telas. O estado do processamento aparece numa etiqueta neutra, e o resultado de cada
  validação num selo com tarja no tom do resultado. Em telas estreitas a tabela rola sozinha.
  O serviço `front` passa a receber `LUPA_AMBIENTE`; a página de catálogo `/padrao` só abre em
  `desenvolvimento`. Ação: `docker compose up -d --build --wait`.
- A intranet passa a ser renderizada no servidor por um front Django (`lupa_web`) com HTMX, com o
  mesmo visual. O navegador só fala com o front, e o proxy deixa de expor `/api`. O pacote da API
  passa a se chamar `lupa_api`, e as linhas novas de auditoria usam o prefixo `api.`; as antigas
  mantêm `intranet.`. Ação: `docker compose up -d --build --wait --remove-orphans`.
- A suíte ponta a ponta (`bash intranet/web/scripts/e2e.sh`) e as capturas dos guias passam a usar
  `pytest-playwright`.
- `bash scripts/verificar.sh` roda lint, tipagem e testes de `lupa_web` no contêiner `front` e
  funciona numa stack nova, sem desembargador cadastrado.

### Removido

- A variável `LUPA_EXTRACAO_LOTES_POR_GABINETE`. Se ainda estiver no `.env`, é ignorada.
- A opção "Visualizar como assessor" do desembargador.
- O SvelteKit e toda a cadeia Node do front (Vitest, Playwright em TypeScript, Prettier, ESLint e
  `npm`).

## [0.2.0] - 2026-11-15

### Adicionado

- Dossiê cível com qualificação das partes, evidências de página, histórico de fatos e achados e conferência individual de cada recorrente.
- Catálogo de tempestividade, preparo, representação e cabimento para apelações, agravos e embargos. As cinco classes, inclusive ação originária, têm autos sintéticos com gabarito.
- Data Vault no PostgreSQL, descarte com retomada de objetos pendentes e auditoria em cadeia única.
- Cadastro do processo pelo envio do PDF ou ZIP dos autos, que identifica número CNJ e classe e pede só o campo que faltar. Um novo arquivo de um número já cadastrado entra no mesmo processo (`POST /api/processos/arquivos`).
- Ficha do processo com partes, polos, relator, órgão julgador, assunto, valor da causa, juízo de origem e distribuição, cada um com sua fonte. A classe pode ser corrigida, com a alteração registrada e os achados recalculados.

### Alterado

- A intranet e a pipeline têm pacotes e suítes próprios. O processamento usa uma fila no PostgreSQL e retoma páginas e lotes já concluídos.
- Desembargador e assessores compartilham o acervo de um gabinete. Os nomes das partes permanecem nos trechos consultados. A aplicação aceita autos sigilosos e documenta o tratamento no serviço externo do modelo.

### Removido

- Módulos criminais do piloto, administrador e isolamento por gabinete, Redis/RQ, backup, monitoramento e configuração de produção da 0.1.
- Vault e cifra da aplicação. Autos, nomes de partes e mensagens do chat ficam em claro no PostgreSQL e no MinIO, e `/api/saude` informa só `api`, `db` e `minio`. A atualização não converte dados antigos: apague os volumes do banco, do MinIO e `vault-dados`, refaça a instalação e reenvie os processos.

## [0.1.0] - 2026-11-13

### Adicionado

- Documentação de entrada do repositório: [CONTRIBUTING.md](CONTRIBUTING.md),
  [docs/arquitetura.md](docs/arquitetura.md), [ADRs](docs/adr/README.md),
  [runbooks](docs/runbooks/README.md), este changelog e o [código de conduta](CODE_OF_CONDUCT.md)
  (`vhfleury/lupa1.1#4`).
- 2026-11-07: o lint do front passa a conferir a formatação com Prettier. Um arquivo fora do padrão
  impede a geração da imagem do front. Ação: rode `npm run format` num contêiner Node antes do
  build (`vhfleury/lupa1.1#3`).
- 2026-11-06: `README` do front com o mapa das pastas e os comandos (`vhfleury/lupa1.1#3`).
- 2026-11-06: alvo `make lock`, que gera `requirements.txt` e `requirements-dev.txt` a partir do
  `pyproject.toml` (`vhfleury/lupa1.1#2`).
- 2026-11-06: `scripts/verificar.sh` ganha os passos opcionais de E2E (`LUPA_VERIFICAR_E2E=1`) e de
  backup (`LUPA_VERIFICAR_BACKUP=1`) (`vhfleury/lupa1.1#2`).
- 2026-11-06: índice da documentação em [docs/README.md](docs/README.md) (`vhfleury/lupa1.1#1`).
- 2026-10-22: primeira versão no repositório, com as Etapas 0 a 8.2: ingestão de PDF e ZIP, três
  validações determinísticas, agente e chat com citações conferidas, interface web, autenticação
  com TOTP, auditoria encadeada, criptografia em repouso, backup cifrado, monitoramento e guias dos
  usuários. Histórico em [docs/etapas/ETAPAS.md](docs/etapas/ETAPAS.md).

### Modificado

- 2026-11-06: as dependências Python passam a ser declaradas só no `pyproject.toml`. Ação: para
  mudar uma versão, edite o `pyproject.toml` e rode `make lock`; não edite `requirements*.txt` à
  mão ([ADR 0010](docs/adr/0010-dependencias-no-pyproject-com-uv.md)).
- 2026-11-06: a documentação foi reorganizada em pastas por assunto dentro de `docs/`. Ação:
  atualize links antigos para `docs/` (`vhfleury/lupa1.1#1`).

### Obsoleto

- Nada.

### Removido

- 2026-11-06: os oito scripts `.ps1`. Ação: no Windows, rode os `.sh` pelo Git Bash
  (`vhfleury/lupa1.1#2`).
- 2026-11-06: `requirements.in` e `requirements-dev.in` (`vhfleury/lupa1.1#2`).
- 2026-11-06: `scripts/recifrar_objetos_legado.py` (`vhfleury/lupa1.1#2`).
- 2026-11-06: relatórios de etapa sem citação, revisões e roteiros antigos de `docs/`. O texto
  continua no histórico do Git (commits `58e9774` e `54219a2`) (`vhfleury/lupa1.1#1`).

### Corrigido

- 2026-11-07: o aviso de expiração da sessão no front (`vhfleury/lupa1.1#3`).

### Segurança

- 2026-11-06: dado em claro é recusado na leitura. Objeto sem cabeçalho `LUPAOBJ` e campo sem
  prefixo `lupa1:` geram `CifraInvalidaError`. Ação: aplique a migração `0012`
  (`docker compose exec api alembic -c src/lupa/migrations/alembic.ini upgrade head`) e recrie o
  bucket de desenvolvimento, que guarda objetos antigos em claro
  ([ADR 0012](docs/adr/0012-recusa-de-dado-em-claro.md)).

[Não publicado]: https://github.com/vhfleury/lupa/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/vhfleury/lupa/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/vhfleury/lupa/releases/tag/v0.1.0
