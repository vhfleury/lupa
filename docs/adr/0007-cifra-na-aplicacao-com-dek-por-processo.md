# ADR 0007 — Cifra na aplicação com DEK por processo

| Status | Data | Responsável |
| --- | --- | --- |
| Aceito | `{{data exata da decisão}}` (até 2026-10-22, data do primeiro commit) | Executor da Etapa 7; endossada na revisão 7.1-7.9 |

## Contexto

Os requisitos pedem criptografia em repouso com chave por processo derivada da chave do gabinete, para impedir vazamento do servidor ou do storage, e exclusão do processo pela destruição da chave. Eles previam a criptografia nativa do MinIO com chaves no Vault.

## Restrições

- Texto extraído e índices também cifrados, não só o PDF.
- O arquivo é cifrado antes de qualquer parser abrir.
- A imagem do object storage pode ser trocada ([ADR 0008](0008-imagem-do-object-storage.md)).

## Alternativas consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| Criptografia nativa do MinIO (SSE com KMS) | Prende a cifra ao servidor de storage. Com a cifra na aplicação, o storage é substituível por configuração e uma troca é cópia de bytes opacos. |
| Cifrar só as colunas da lista do roteiro | `texto_nativo` e `texto_ocr` guardam o mesmo texto da página; sem eles o dump ainda mostraria os autos. |
| Índice HMAC para a busca do agente | Descartado no piloto: a busca é sempre por um processo; decifra em memória com teto (`LUPA_BUSCA_MAX_PAGINAS`). |

## Decisão

Cada processo tem uma DEK, gerada na inserção e envelopada pela chave do gabinete no Vault (Transit). Campos usam o formato `lupa1:` e objetos o cabeçalho `LUPAOBJ` (AES-256-GCM). As identidades dos réus vão direto ao Transit, com chave própria. O descarte destrói a DEK.

## Consequências

- Sem o Vault destravado nada dos autos é lido nem gravado: `/saude` responde 503 ([runbook](../runbooks/destravar-vault.md)).
- A rotação da chave do gabinete reenvelopa as DEKs sem recifrar os dados.
- O texto cifrado não aceita `ILIKE`.
- O backup copia os bytes cifrados; a restauração exige o Vault com as chaves da época.
- Custo medido por mil páginas: +0,1 a +0,3 s na gravação e +0,05 a +0,08 s na leitura.

## Fontes

- [especificacao/requisitos-v1.md](../especificacao/requisitos-v1.md), seção 6
- [decisoes/registro.md](../decisoes/registro.md), "Endossadas na revisão 7.1-7.9"
- [sistema/criptografia.md](../sistema/criptografia.md)
