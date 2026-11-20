# Front do Lupa

Interface web do Lupa: pacote Django `lupa_web` (templates renderizados no servidor, HTMX), servido
por uvicorn no serviço `front` atrás do Caddy. Não tem banco nem sessão própria: toda tela chama a
API por HTTP na rede interna. O documento principal é
[docs/sistema/front.md](../../docs/sistema/front.md); a decisão está no
[ADR 0019](../../docs/adr/0019-front-django-renderizado-no-servidor.md).

## Pastas

| Caminho | Conteúdo |
| --- | --- |
| `src/lupa_web/` | Configuração, ASGI, rotas, cliente da API (`cliente_api.py`), rótulos e envios pendentes |
| `src/lupa_web/telas/` | Views, uma por assunto (`acesso`, `processos`, `processo`, `envio`, `dossie`, `chat`...) |
| `src/lupa_web/templates/` | Templates Django das telas e dos fragmentos HTMX |
| `src/lupa_web/static/` | CSS, HTMX, scripts de tema, envio e visualizador, favicon e logos |
| `tests/` | `unit/`, `telas/` (API simulada com `respx`), `integracao/` e `e2e/` (`pytest-playwright`) |
| `e2e/` | Imagem e arquivo Compose da suíte ponta a ponta |
| `scripts/` | `e2e.sh` e `capturas.sh`, com o preparo comum em `preparar-e2e.sh` |
| `Dockerfile` | Imagem do serviço `front` (contexto na raiz do repositório) |

## Comandos

Tudo roda em contêiner. Os comandos abaixo partem da raiz do repositório, com a stack de pé
(`docker compose up -d --build --wait`).

```bash
docker compose exec front python -m pytest -c intranet/web/pyproject.toml intranet/web/tests
```

Roda os testes de `lupa_web` com cobertura; `bash scripts/verificar.sh` roda também ruff, format e
`mypy --strict`.

```bash
bash intranet/web/scripts/e2e.sh
```

Roda os testes ponta a ponta contra um projeto Compose temporário com usuários, processos e volumes sintéticos próprios.

```bash
bash intranet/web/scripts/capturas.sh
```

Gera as capturas de tela dos guias em `docs/imagens/`.
