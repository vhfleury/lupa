# ADR 0016 — Pacotes de pipeline e intranet

| Status | Data de registro | Referência |
| --- | --- | --- |
| Substituído pelo [ADR 0019](0019-front-django-renderizado-no-servidor.md) quanto aos pacotes | 2026-11-14 | Especificação e plano 0.2 aprovados pelo responsável pelo projeto |

## Contexto

Os parsers e a ingestão de documentos operam em rede interna. A API expõe rotas, controla sessões e precisa acessar o fornecedor do modelo. Essas responsabilidades têm ciclos de verificação distintos.

## Alternativa considerada

A distribuição única da 0.1 colocava o agente e as dependências da intranet na mesma unidade da pipeline.

## Decisão

Organizar `pipeline/` com `lupa_pipeline` e `intranet/api/` com `lupa_intranet`. A intranet importa a pipeline. O worker instala o primeiro pacote e a API instala ambos. O front e o proxy ficam em `intranet/web/` e `intranet/proxy/`.

## Consequências

Cada pacote Python tem seu próprio manifesto, lock e cobertura mínima de 90%. As fixtures compartilhadas ficam em `pipeline/tests/apoio/`. O Compose mantém a rede do worker interna e a saída do modelo ligada à intranet.

## Referências

[Estrutura do repositório](../../README.md) e [contribuição](../../CONTRIBUTING.md). [Plano 0.2](../planos/plano_0.2.md).
