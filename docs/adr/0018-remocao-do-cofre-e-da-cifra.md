# ADR 0018 — Remoção do cofre e da cifra da aplicação

| Status | Data | Responsável |
| --- | --- | --- |
| Aceito | 2026-11-15 | Projeto Lupa |

Substitui os ADRs [0007](0007-cifra-na-aplicacao-com-dek-por-processo.md),
[0011](0011-leitura-de-legado-em-claro.md) e [0012](0012-recusa-de-dado-em-claro.md).

## Contexto

A 0.2 cifrava na aplicação o conteúdo dos autos, os nomes das partes e o chat com uma chave de dados por processo, envolvida pelo Vault Transit. O Vault exigia inicialização, destravamento após cada reinício e um runbook próprio, e a saúde da API dependia dele.

## Restrições

A implantação é de desenvolvimento, de um único gabinete, com PostgreSQL e MinIO em rede interna. A especificação da 0.2 (decisões 40 a 45 e RF-SEG-01) passou a dispensar a cifra da aplicação.

## Alternativas consideradas

Manter o Vault e a cifra por processo. Trocar o Vault por chave em arquivo local, o que mantinha a cifra com proteção menor que a do cofre.

## Decisão

O serviço `vault`, sua configuração e toda a cifra da aplicação saem do sistema. Autos, nomes de partes e mensagens ficam em claro no PostgreSQL e no MinIO. `hub_parte.chave_nome` é o SHA-256 do nome normalizado e o `hash_diff` é sempre SHA-256. A rota de saúde verifica só `api`, `db` e `minio`. A revisão `v0003` remove `sat_processo_chave` e `v_processo.chave_dados_cifrada`. O descarte apaga os satélites de conteúdo e os objetos; o evento `processo_descartado` tem `objeto_tipo` `processo` e `objeto_id` igual ao identificador do processo. Não há rotação de chave.

## Consequências

Os dados gravados com cifra não são migrados: a atualização recria banco, MinIO e o volume do Vault e reenvia os processos. A proteção em repouso passa a depender do host e dos volumes. Subida e reinício dispensam destravamento.

## Fontes

- [Especificação da 0.2, decisões 40 a 45](../especificacao/0.2/especificacao.md)
- [Plano da remoção do Vault e da cifra](../planos/plano_remocao_vault.md)
- [Registro de decisões](../decisoes/registro.md)
