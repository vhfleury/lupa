# ADR 0008 — Imagem do object storage

| Status | Data | Responsável |
| --- | --- | --- |
| Proposto | `{{data da assinatura}}` | `{{responsável técnico que assina}}` |

## Contexto

A MinIO Inc. deixou de publicar imagens comunitárias atualizadas em 2025. O piloto precisa de um armazenamento S3 local. A análise completa e a linha de assinatura estão em [decisoes/object-storage.md](../decisoes/object-storage.md).

## Restrições

- Receber correções de segurança.
- Imagem fixável por digest.
- Rodar sem root.
- Trazer o cliente `mc`, usado no healthcheck, no `minio-init` e no serviço `backup`.
- Falar S3 com o `boto3` sem mudar `ArmazenamentoS3`.

## Alternativas consideradas

| Alternativa | Por que foi descartada |
| --- | --- |
| `cgr.dev/chainguard/minio` | Não traz `mc`: quebra healthcheck, `minio-init` e `backup`. Só a tag `latest` é gratuita. Fica como plano B, com uma segunda imagem só para o `mc`. |
| Garage | Serviço, operação e migração de dados diferentes; cobre só um subconjunto da API S3. Fica como plano C. |
| RustFS | Projeto jovem; maturidade e licença a acompanhar. |

## Decisão

Proposta: manter `pgsty/minio` fixado por digest como padrão, parametrizado por `STORAGE_IMAGEM`, e revisar o digest a cada mês ou a cada CVE do MinIO. Enquanto não houver assinatura, vale esse padrão.

## Consequências

- Depende de um mantenedor comunitário.
- Como os objetos já saem cifrados da aplicação ([ADR 0007](0007-cifra-na-aplicacao-com-dek-por-processo.md)), trocar de storage é `mc mirror`, sem recifrar.
- Pendência 3 de pendências do piloto (removido; ver histórico do Git) até a assinatura.

## Fontes

- [decisoes/object-storage.md](../decisoes/object-storage.md)
- [decisoes/registro.md](../decisoes/registro.md), Etapa 0, item 2
