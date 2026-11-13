# ADR 0009 — Dependências Python com `pip-compile` a partir de arquivos `.in`

| Status | Data | Responsável |
| --- | --- | --- |
| Substituído por [ADR 0010](0010-dependencias-no-pyproject-com-uv.md) | `{{data exata da decisão}}` (até 2026-10-22, data do primeiro commit) | Executor da Etapa 0 |

## Contexto

A imagem instala dependências com `--require-hashes`. Era preciso gerar `requirements.txt` com hashes.

## Restrições

- Não havia `uv` na máquina na Etapa 0.
- Gerar no Windows trazia pacotes que o Linux não usa.

## Alternativas consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| `uv` | Não estava instalado na máquina naquele momento. |

## Decisão

`requirements.txt` e `requirements-dev.txt` gerados por `pip-compile --generate-hashes` a partir de `requirements.in` e `requirements-dev.in`, com as versões espelhadas no `pyproject.toml`. A partir da 4A, a geração passou a rodar dentro do contêiner.

## Consequências

- A mesma lista ficava em três arquivos.
- A geração dependia de contêiner para não trazer `tzdata` e `colorama` do Windows.
- Substituído em 2026-11-06 pelo [ADR 0010](0010-dependencias-no-pyproject-com-uv.md).

## Fontes

- [decisoes/registro.md](../decisoes/registro.md), Etapa 0, item 1, e "Endossadas na revisão 4A"
