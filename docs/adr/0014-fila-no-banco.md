# ADR 0014 — Fila de arquivos no PostgreSQL

| Status | Data de registro | Referência |
| --- | --- | --- |
| Aceito | 2026-11-14 | Especificação e plano 0.2 aprovados pelo responsável pelo projeto |

## Contexto

A situação do arquivo e a retomada já dependem do PostgreSQL. A carga prevista para o gabinete permite um consumidor de ingestão por implantação.

## Alternativa considerada

O modelo anterior de broker Redis com RQ exigia conciliar o estado da mensagem e os dados de recuperação da ingestão.

## Decisão

Consumir a view da fila em ordem de recebimento. O worker mantém um advisory lock de sessão até a saída e usa a conexão física que detém o lock. Confirma o contador de tentativas antes de processar, registra o estado e interrompe o consumo se a conexão mudar.

## Consequências

A exclusividade é liberada pelo próprio PostgreSQL quando a conexão fecha. As páginas já concluídas dão suporte à retomada. O healthcheck verifica o banco e a implantação dispensa o serviço externo da fila.

## Referências

Substitui o [ADR 0002](0002-fila-rq-com-banco-como-fonte-da-verdade.md). [Ingestão](../sistema/ingestao.md). [Plano 0.2](../planos/plano_0.2.md).
