# ADR 0003 — Sandbox de parsing por subprocesso com limites

| Status | Data | Responsável |
| --- | --- | --- |
| Aceito | `{{data exata da decisão}}` (até 2026-10-22, data do primeiro commit) | Executor da Etapa 4A; endossada na revisão 4A |

## Contexto

PDF e OCR são a superfície de ataque mais antiga do sistema. Um arquivo malicioso não pode alcançar banco, storage nem credenciais.

## Restrições

- O worker precisa de banco, storage e Redis para gravar; o parser não.
- `python -I` ignora `PYTHONPATH`.

## Alternativas consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| gVisor ou bubblewrap | Sugeridos no desenho original. O registro não traz o motivo do descarte: `{{motivo de descartar gVisor e bubblewrap}}`. |
| `--network none` | Não se aplica a subprocesso, só a contêiner. |
| Contêiner próprio do parser, sem rede | Adiado. Fica para quando a decifragem por processo exigir um worker de decifragem separado. |

## Decisão

`sandbox.executar` roda `python -I` num subprocesso com `RLIMIT_AS`, `RLIMIT_CPU`, `RLIMIT_FSIZE = 0`, `RLIMIT_NOFILE = 64`, tempo de parede imposto pelo pai, ambiente sem variáveis `LUPA_*` e criação de sockets desabilitada. O resultado sai só por JSON em stdout. O isolamento de rede vem do contêiner `worker`, que fica só na rede `ingestao` (`internal: true`).

## Consequências

- Limitação conhecida: o filho ainda alcança `db`, `minio` e `redis` na rede interna, mas sem credenciais e sem sockets.
- Estouro de memória vira `limite_memoria`; de CPU, `limite_cpu`; de tempo, `tempo_esgotado`. Todos levam o job a `falho`.
- stderr do parser é descartado e nunca vai ao log.

## Fontes

- [decisoes/registro.md](../decisoes/registro.md), 4A.4
- [sistema/ingestao.md](../sistema/ingestao.md), "Sandbox de parsing"
- `src/lupa/ingestao/sandbox.py`
