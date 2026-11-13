# ADR 0012 — Dado em claro é recusado na leitura

| Status | Data | Responsável |
| --- | --- | --- |
| Aceito | 2026-11-06 | Victor Hugo Fleury Barreto |

## Contexto

Substitui o [ADR 0011](0011-leitura-de-legado-em-claro.md). Aceitar dado em claro servia só como caminho de migração e escondia gravação sem cifra.

## Restrições

- Não há dado real anterior à 7.4.

## Alternativas consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| Manter a leitura de legado | Esconde gravação sem cifra; o caminho de migração não tem mais uso. |
| Manter `scripts/recifrar_objetos_legado.py` | Sem legado aceito, o script não tem o que recifrar; os objetos órfãos de desenvolvimento são apagados com o bucket. |

## Decisão

Objeto sem cabeçalho `LUPAOBJ` e campo sem prefixo `lupa1:` geram `CifraInvalidaError`; identidade sem token do cofre gera `TokenInvalidoError`. A migração `0012` tira o `DEFAULT '[]'` em claro de `pagina.trechos_ocultos` e `pagina.trechos_suspeitos`.

## Consequências

- Dado em claro no banco ou no bucket passa a ser incidente ([operacao/operacao.md](../operacao/operacao.md), seção 10).
- O bucket de desenvolvimento é recriado antes do piloto ([piloto/roteiro-piloto.md](../piloto/roteiro-piloto.md), passo 0.4).
- Ação para quem opera: aplique a migração `0012` com `alembic upgrade head`.

## Fontes

- [decisoes/registro.md](../decisoes/registro.md), "Decisões posteriores à v1"
- PR `vhfleury/lupa1.1#2`
- `tests/seguranca/test_dado_em_claro_recusado.py`
