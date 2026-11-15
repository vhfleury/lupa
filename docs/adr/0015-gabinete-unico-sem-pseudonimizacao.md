# ADR 0015 — Gabinete único e nomes das partes

| Status | Data de registro | Referência |
| --- | --- | --- |
| Aceito | 2026-11-14 | Especificação e plano 0.2 aprovados pelo responsável pelo projeto |

## Contexto

A equipe de um gabinete cível precisa reconhecer polo, qualidade e nome da parte para conferir recurso, mandato e prova com a página original.

## Alternativa considerada

O desenho de múltiplos gabinetes e pseudônimos para réus exigia escopo por tenant e substituição de nomes nos trechos e não atendia ao fluxo cível aprovado.

## Decisão

Manter dois papéis e um acervo comum ao gabinete. Cifrar os nomes em repouso e usá-los no dossiê, nas evidências e no contexto do modelo. Usar HMAC do nome normalizado para a identidade interna da parte. Permitir o cadastro independentemente de sigilo.

## Consequências

O desembargador administra os assessores. A marca de responsável distribui trabalho. Dados identificáveis, inclusive de autos sigilosos, podem chegar ao fornecedor externo. A revisão jurídica e institucional avalia a permissão e as salvaguardas para o uso real.

## Referências

[Conformidade](../conformidade/CONFORMIDADE.md) e [criptografia](../sistema/criptografia.md). [Plano 0.2](../planos/plano_0.2.md).
