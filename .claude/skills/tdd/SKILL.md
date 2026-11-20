---
name: tdd
description: Implementa uma mudança de código no Lupa em ciclo TDD (teste falhando, implementação mínima, verde, limpeza) com pytest nos contêineres worker e api ou front, delegando ao agente tdd. Use para toda lógica nova ou alterada em pipeline/ e intranet/, e para correção de bug.
argument-hint: "[tarefa de tarefas_0.2.md ou comportamento esperado]"
---

# TDD

Tarefa: $ARGUMENTS

O ciclo é executado pelo agente `tdd` (`.claude/agents/tdd.md`), como manda o `CLAUDE.md`. Esta
skill prepara a chamada e confere o retorno.

## Passo a passo

| # | Entrada | Ação | Saída |
|---|---|---|---|
| 1 | tarefa | Identificar requisito (`RF-<ÁREA>-NN`/`RNF-NN`), módulo, função alvo e critérios de aceite | alvo + tipo (unitário, integração, front) |
| 2 | alvo | Localizar o teste espelho e as fixtures (`apoio_comum`, `conftest.py` da área) | caminho do teste |
| 3 | tudo | Chamar o agente `tdd` com módulo, comportamento esperado, requisito e testes já desenhados (transcritos sem mudar entrada nem esperado) | relatório do agente |
| 4 | correção de bug | Passar o caso vermelho a quem implementa e devolver a mudança ao `tdd` para verificar verde e regressões | verde confirmado |
| 5 | relatório | Conferir vermelho pelo motivo certo, verde depois do rebuild, nenhum `skip`/`xfail` | ok ou devolução |
| 6 | ok | `/valida-pipeline` ou `/valida-intranet` | gates |

## Onde ficam os testes

| Código | Teste |
|---|---|
| `pipeline/src/lupa_pipeline/<sub>/<modulo>.py` | `pipeline/tests/<sub>/test_<modulo>.py` |
| `intranet/api/src/lupa_api/<sub>/<modulo>.py` ou rota | `intranet/api/tests/<sub>/test_<modulo>.py` |
| revisão Alembic | `test_migracao_NNNN.py` na área do assunto, com `migrar` |
| `config.py`, `logging.py`, scripts | `tests/unit/` do pacote |
| `intranet/web/src/lupa_web/<sub>/<modulo>.py` ou tela | `intranet/web/tests/<sub>/test_<modulo>.py` |

## Comandos

```bash
docker compose up -d --build --wait api worker
docker compose exec worker python -m pytest -c pipeline/pyproject.toml pipeline/tests/<sub>/test_<modulo>.py --no-cov -q
docker compose exec api python -m pytest -c intranet/api/pyproject.toml intranet/api/tests/<sub>/test_<modulo>.py --no-cov -q
docker compose exec front python -m pytest -c intranet/web/pyproject.toml intranet/web/tests/<sub>/test_<modulo>.py --no-cov -q
```

## Regras

- Rebuild antes de rodar: as imagens copiam o código.
- Cada teste novo cita o requisito na docstring; nome pelo comportamento.
- Dados sintéticos; tempo injetado (`relogio_fixo`); dublês existentes (`ResolvedorFalso`, cliente
  roteirizado).
- Teste existente só muda junto com a regra, no mesmo commit, com o motivo no plano.
- Teste pulado não é verde.

## Relatório final

- testes criados ou alterados e requisitos cobertos;
- vermelho inicial e verde final de cada execução;
- arquivos modificados;
- o que não pôde ser testado e por quê (revisão manual).
