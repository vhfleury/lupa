# ADR 0010 — Dependências declaradas só no `pyproject.toml`, travadas com `uv`

| Status | Data | Responsável |
| --- | --- | --- |
| Aceito | 2026-11-06 | Victor Hugo Fleury Barreto |

## Contexto

Substitui o [ADR 0009](0009-dependencias-com-pip-compile.md). A lista de dependências estava em `pyproject.toml`, `requirements.in` e `requirements-dev.in`, e a geração exigia contêiner.

## Restrições

- A imagem continua instalando com `--require-hashes`.
- As versões e os hashes de produção não podiam mudar na troca.

## Alternativas consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| Manter os arquivos `.in` com `pip-compile` | Três fontes para a mesma lista; gerar no Windows trazia `tzdata` e `colorama`. |
| Gerar dentro de contêiner | Desnecessário: mirar a plataforma (`x86_64-manylinux_2_28`, Python 3.12) resolve sem contêiner. |

## Decisão

O `pyproject.toml` é a única fonte (`dependencies` e o extra `dev`). `make lock` roda `uv pip compile` e gera `requirements.txt` e `requirements-dev.txt` com hashes. O `requirements-dev.txt` traz produção mais desenvolvimento.

## Consequências

- Para mudar uma versão: edite o `pyproject.toml` e rode `make lock`.
- `requirements*.txt` só muda por `make lock`.
- A troca manteve 68 pacotes e 2.082 hashes de produção idênticos.

## Fontes

- [decisoes/registro.md](../decisoes/registro.md), "Decisões posteriores à v1"
- PR `vhfleury/lupa1.1#2`
- `Makefile`
