# ADR 0011 — Leitura de dado legado em claro

| Status | Data | Responsável |
| --- | --- | --- |
| Substituído por [ADR 0012](0012-recusa-de-dado-em-claro.md) | `{{data exata da decisão}}` (até 2026-10-22, data do primeiro commit) | Executor da Etapa 7.4 |

## Contexto

A cifra dos originais entrou na Etapa 7.4. O MinIO de desenvolvimento já tinha objetos gravados em claro.

## Restrições

- Não havia dado real anterior à 7.4, só sintéticos.

## Alternativas consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| Recifrar os objetos antigos na 7.4 | Não foi feito na etapa; reenvio ou descarte resolvia. Um script de recifragem veio na 7.10. |

## Decisão

A leitura aceitava objeto sem cabeçalho `LUPAOBJ` e campo sem prefixo `lupa1:`, com o aviso `objeto_legado_em_claro`.

## Consequências

- Uma gravação sem cifra passava despercebida na leitura.
- Substituído em 2026-11-06 pelo [ADR 0012](0012-recusa-de-dado-em-claro.md).

## Fontes

- [etapas/ETAPAS.md, 7.4](../etapas/ETAPAS.md#etapa-7-4)
- [decisoes/registro.md](../decisoes/registro.md), "Decisões posteriores à v1"
