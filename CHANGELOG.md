# Changelog

Todas as mudanças relevantes do Lupa ficam registradas aqui.

O formato segue o [Keep a Changelog 1.1.0](https://keepachangelog.com/pt-BR/1.1.0/). As datas usam
`AAAA-MM-DD`.

## Como as versões funcionam

- A versão é do monorepo inteiro: back, front, proxy e scripts sobem juntos. O `pyproject.toml` e o
  `front/package.json` declaram a mesma versão, `0.0.1`.
- O repositório ainda não tem tags nem releases no GitHub. Por isso tudo está em `Não publicado`.
- Ao publicar: crie a tag, mova as entradas para uma seção `## [X.Y.Z] - AAAA-MM-DD` e atualize as
  duas declarações de versão. Esquema de numeração: `{{esquema de versão e quem publica a tag}}`.

## [Não publicado]

### Adicionado

- Documentação de entrada do repositório: [CONTRIBUTING.md](CONTRIBUTING.md),
  [docs/arquitetura.md](docs/arquitetura.md), [ADRs](docs/adr/README.md),
  [runbooks](docs/runbooks/README.md), este changelog e o [código de conduta](CODE_OF_CONDUCT.md).
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
