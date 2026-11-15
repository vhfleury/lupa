# Contribuir com o Lupa

A especificação vigente é a [0.2](docs/especificacao/0.2/especificacao.md). Antes de alterar um fluxo, confira a tarefa, o requisito e o algoritmo no [plano de execução](docs/planos/plano_0.2_execucao.md). Formule um teste que falhe sobre o comportamento, implemente a mudança e registre o resultado observado no [quadro de tarefas](docs/planos/tarefas_0.2.md). As convenções de código, documentação e segurança ficam em [CLAUDE.md](CLAUDE.md).

## Organização

- Python 3.12. A pipeline vive em `pipeline/src/lupa_pipeline/` e a intranet em `intranet/api/src/lupa_intranet/`. Cada pacote tem seu próprio `pyproject.toml`, dependências travadas e testes. A API pode importar a pipeline.
- SvelteKit e TypeScript vivem em `intranet/web/`. Testes Vitest ficam junto ao código de interface, e os fluxos com navegador ficam em `intranet/web/e2e/`.
- O banco usa a revisão do Data Vault na pipeline. As views, contratos de gravação e evidências são descritos em [modelo de dados](docs/sistema/modelo-de-dados.md).
- Todo teste usa dados inventados. As fixtures comuns ficam em `pipeline/tests/apoio/`. Os testes com serviços usam bases sintéticas. Dados de autos reais, material do Vault e credenciais da instalação ficam fora de testes, logs e commits.

## Verificar

Execute na raiz com a instalação de desenvolvimento pronta e imagens construídas com o código que deseja testar.

| Comando | Verificação |
| --- | --- |
| `make lint` e `make typecheck` | Ruff e mypy nos dois pacotes |
| `make test` | Pytest e cobertura mínima de 90% por pacote |
| `docker build --target verificacao intranet/web` | Prettier, ESLint, svelte-check e Vitest |
| `bash scripts/verificar.sh` | Verificações dos pacotes, serviços, corpus de injeção e suíte do agente |
| `bash intranet/web/scripts/e2e.sh` | Playwright contra serviços e contas sintéticos isolados em um projeto Compose temporário |
| `bash intranet/web/scripts/capturas.sh` | Capturas reais dos fluxos sintéticos para os guias |
| `make lock` | Regenera os quatro locks com hashes, para Python 3.12 e a plataforma Linux do projeto |

Para iterar em uma regra, rode `docker compose exec worker python -m pytest -c pipeline/pyproject.toml pipeline/tests/validacoes/test_preparo.py --no-cov -q`. O teste de uma rota usa a imagem da API e o manifesto da intranet. As suítes de regressão usam cliente roteirizado. O marcador `llm` identifica a chamada real com credencial externa. Quando houver uma etapa não executada, informe o teste e a dependência real que faltou.

## Revisar e entregar

Confira o caminho público afetado, reexecução e dados anteriores aceitos pela versão. Preserve revisão humana e referências de fonte. Alterações de dados, acesso, armazenamento ou modelo precisam dos testes correspondentes e de documentação sobre o comportamento observado. No PR, cite a tarefa, o requisito, o teste vermelho e os testes verdes com a cobertura quando aplicável. Registre limites ou verificações pendentes. As decisões e o histórico ficam em [docs/](docs/README.md).
