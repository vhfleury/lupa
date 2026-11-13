# Como contribuir com o Lupa

As convenções de código, de testes e de banco estão no [CLAUDE.md](CLAUDE.md). Este documento
descreve o caminho de uma alteração. A convivência segue o
[código de conduta](CODE_OF_CONDUCT.md).

## Estado da CI

O repositório não tem pipeline de CI (não existe `.github/workflows/`). A verificação roda na
máquina de quem altera, com os comandos abaixo, e o resultado vai no corpo do PR. Os três PRs
integrados até aqui (`vhfleury/lupa1.1#1`, `#2` e `#3`) seguiram esse formato.

## Caminho de uma alteração

1. Parta de `develop`. Os PRs integrados têm `develop` como base. A branch `main` está parada no
   commit inicial; a regra de promoção de `develop` para `main` é
   `{{regra de promoção de develop para main e quem a executa}}`.
2. Crie a branch com prefixo de tipo, como nas existentes: `chore/organiza-docs`,
   `chore/simplifica-deps-scripts`, `chore/organiza-front`.
3. Issue: o repositório não tem issues abertas nem fechadas. Vincule uma issue quando
   `{{critério para abrir e vincular issue}}`. Mudança com plano cita o arquivo de `docs/planos/`.
4. Escreva o teste antes do código ([CLAUDE.md](CLAUDE.md), "Desenvolvimento orientado a testes").
5. Rode as verificações da seção seguinte.
6. Abra o PR para `develop` com o checklist preenchido.

### Onde fica cada coisa

| O quê | Onde |
| --- | --- |
| Código do back | `src/lupa/<pacote>/` |
| Migrações | `src/lupa/migrations/versions/vNNNN_<tema>.py` |
| Testes do back | `tests/<pacote>/test_<modulo>.py` (espelha `src/lupa/`); `tests/unit/` para `config.py`, `logging.py` e scripts |
| Código do front | `front/src/routes/` (telas) e `front/src/lib/` (lógica e componentes) |
| Testes do front | `front/src/lib/**/<nome>.test.ts` (Vitest) e `front/e2e/testes/` (Playwright) |
| Dados de exemplo versionados | `tests/validacoes/fatos_exemplo.json`; PDFs e ZIPs gerados em código por `tests/ingestao/arquivos.py` |
| Autos sintéticos (fora do git) | `.sinteticos/`, gerados por `scripts/gerar_autos.py` ([docs/sistema/sinteticos.md](docs/sistema/sinteticos.md)) |
| Dados jurídicos versionados | YAML em `src/lupa/validacoes/dados/` e `src/lupa/ingestao/dados/` |
| Documentação | `docs/` ([índice](docs/README.md)) |

Todos os dados de teste são sintéticos. Nunca use número de processo, nome ou trecho de autos reais.

## Testes locais (sem serviços)

Rodam na raiz do repositório, sem banco, MinIO, Redis nem Vault.

| Comando | Pré-requisitos | Sucesso quando |
| --- | --- | --- |
| `python -m ruff check src tests` | `ruff` 0.8.4 num `.venv` de Python 3.12 | imprime `All checks passed!` |
| `python -m ruff format --check src tests` | o mesmo `.venv` | nenhum arquivo em `Would reformat` |
| `python -m compileall -q src tests scripts` | Python 3.12 | sem saída e código 0 (mínimo quando a suíte não pode rodar) |
| `docker compose run --rm --no-deps api python -m pytest --no-cov tests/validacoes` | Docker; imagem `api` construída | todos passam (hoje 73 passam e 1 é pulado: a comparação com `docs/exemplos`, pasta removida) |
| `docker build --target verificacao front` | Docker | a imagem é construída: lint (Prettier e ESLint), `svelte-check` e Vitest passaram |

O `mypy` e a suíte completa rodam no contêiner `api`, que tem todas as dependências (seção
seguinte). Sem os serviços, os testes marcados `integracao` são pulados. Teste pulado não conta
como verde.

## Testes com serviços

Precisam da stack do `docker-compose.yml` (PostgreSQL, MinIO, Redis e Vault destravado). Suba antes,
na raiz:

```bash
docker compose up -d --build --wait api
```

O contêiner `api` copia `src/` e `tests/` no build. Sem o rebuild, ele testa código antigo.

| Comando | Pré-requisitos | Sucesso quando |
| --- | --- | --- |
| `make lint` e `make typecheck` (`ruff check` e `mypy` sobre `src tests`) | stack no ar | `All checks passed!` e `Success: no issues found` |
| `docker compose exec api python -m pytest` | stack no ar | todos passam e a cobertura de `lupa` fica em 90% ou mais |
| `make verificar` (ou `docker compose exec api bash scripts/verificar.sh`) | stack no ar; `.sinteticos/` com o corpus de injeção | o script chega ao fim; ele para no primeiro erro |
| `bash front/scripts/e2e.sh` | Docker no host; **reseta o administrador do banco de desenvolvimento** | a suíte Playwright passa |
| `LUPA_VERIFICAR_BACKUP=1 bash scripts/verificar.sh` | Docker no host; Vault destravado | o passo `backup cifrado e restauracao` passa |
| `docker compose exec api python -m pytest -m carga --no-cov -s` | stack no ar; cerca de 1 minuto | o teste de 1 milhão de eventos passa |
| `python -m pytest -m llm --no-cov tests/agente/test_smoke_llm.py` | `ANTHROPIC_API_KEY` só no ambiente, fora do contêiner | os testes `llm` passam; sem credencial são pulados |

O `scripts/verificar.sh` roda, nesta ordem: `ruff check`, `ruff format --check`, `mypy`, `pytest`
com cobertura, ponta a ponta da ingestão, regressão de injeção, verificação do front, cabeçalhos de
segurança do proxy e suíte de injeção do agente. E2E e backup entram com `LUPA_VERIFICAR_E2E=1` e
`LUPA_VERIFICAR_BACKUP=1`.

`make verificar` é obrigatório quando a mudança toca ingestão, agente, segurança, migrações ou proxy.

## Checklist do PR

Copie para o corpo do PR e preencha.

- [ ] **Comportamento anterior e novo:** o que o sistema fazia e o que passa a fazer.
- [ ] **Testes:** comandos rodados e a saída resumida (contagem de testes e cobertura). Mostre o
      teste vermelho inicial e o verde final.
- [ ] **Não verificado:** cada validação que não rodou, com o motivo.
- [ ] **Consumidores afetados:** rotas da API, `front/src/lib`, auditoria, backup, scripts e manuais.
- [ ] **Esquema:** migração nova (`vNNNN`), com teste de subida e descida; tabela nova com
      `gabinete_id` nasce com RLS; coluna com conteúdo de autos nasce cifrada.
- [ ] **Reprocessamento:** a mudança altera `VERSAO_EXTRATOR` (refaz as páginas), os YAML de
      eventos (regrava fatos e achados) ou exige reenvio de arquivos? Diga qual.
- [ ] **Documentação:** documento de `docs/sistema/` atualizado; decisão nova em `docs/adr/`;
      entrada no [CHANGELOG.md](CHANGELOG.md).
- [ ] **Segurança:** nenhum segredo, conteúdo de autos ou texto de pergunta em código, log ou fixture.
- [ ] `requirements*.txt` só mudou por `make lock`.

## Revisão e merge

- Revisores: os três PRs integrados não tiveram revisão registrada no GitHub; o autor
  (`vhfleury`) fez o merge. Revisor obrigatório: `{{revisor ou equipe revisora}}`.
- Regra de aprovação: `{{número de aprovações exigido}}`. A branch `main` não tem proteção
  configurada no GitHub.
- Critério de merge praticado: verificações desta página verdes, itens não verificados declarados
  no PR e merge por commit de merge em `develop`.
- Nunca apague teste, afrouxe asserção nem marque `skip` ou `xfail` para chegar ao verde.
