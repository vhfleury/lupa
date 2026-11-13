# ADR 0002 — Fila RQ com o banco como fonte da verdade

| Status | Data | Responsável |
| --- | --- | --- |
| Aceito | `{{data exata da decisão}}` (até 2026-10-22, data do primeiro commit) | Executor da Etapa 4A; endossada na revisão 4A |

## Contexto

A ingestão de um arquivo leva de segundos a mais de uma hora. Ela roda fora da requisição, num worker, e não pode perder job quando a fila ou o worker caem.

## Restrições

- Piloto num único host, com Docker Compose.
- O tribunal não participa do piloto nem oferece infraestrutura.
- Um job grande não pode travar um job pequeno de outro gabinete.

## Alternativas consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| Celery | Citado como opção no desenho original. O registro só diz "RQ escolhido"; motivo: `{{motivo de descartar o Celery}}`. |
| Airflow | O desenho original só o admitia se o tribunal já o tivesse. O tribunal não participa do piloto. |
| Redis com persistência como fonte do estado | Duplicaria o estado. O banco já guarda o job; a fila pode ser volátil. |
| Fila com prioridade | Exigiria mudar o RQ e conhecer o tamanho do job ao enfileirar. O round-robin de fatias dispensa os dois. |
| Worker com fork por job | O isolamento pesado já está no sandbox por subprocesso ([ADR 0003](0003-sandbox-de-parsing-por-subprocesso.md)); usa-se `SimpleWorker`. |

## Decisão

Redis 7.4 sem persistência e RQ carregam só `job_id` e `gabinete_id`. O estado fica em `job_ingestao`, com lease, heartbeat e `fencing_token`. O varredor do worker reenfileira jobs parados. Depois de `LUPA_EXTRACAO_FATIA_PAGINAS` páginas o job cede a vez e volta ao fim da fila.

## Consequências

- Mensagem perdida, Redis reiniciado ou falha de enfileiramento no upload não perdem job.
- Um worker que perdeu o lease recebe `LeasePerdidoError` e não grava.
- O semáforo por gabinete vale por processo worker; mais de uma réplica exige um semáforo no Redis (planejado).
- As métricas são calculadas do banco, não de contadores em memória.

## Fontes

- [decisoes/registro.md](../decisoes/registro.md), 4A.3, 4A.9 e 4C.8
- [sistema/ingestao.md](../sistema/ingestao.md), "Lease, heartbeat e fencing token"
- [especificacao/arquitetura.md](../especificacao/arquitetura.md), "Stack sugerida"
