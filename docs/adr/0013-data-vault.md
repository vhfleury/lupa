# ADR 0013 — Data Vault e histórico de leitura

| Status | Data de registro | Referência |
| --- | --- | --- |
| Aceito | 2026-11-14 | Especificação e plano 0.2 aprovados pelo responsável pelo projeto |

## Contexto

Os processos, peças, fatos, responsabilidades e achados precisam de identidade estável e histórico consultável após reexecução ou revisão. A implantação atende um único gabinete e mantém os atos registrados mesmo ao descartar conteúdo.

## Alternativa considerada

A 0.1 usava tabelas mutáveis e isolamento por gabinete com RLS. O histórico necessário exigiria rastreamento distribuído de versões nesse desenho.

## Decisão

Adotar hubs identificados por SHA-256, links de relação e satélites de mudança em PostgreSQL. O banco atribui a data de carga e as views resolvem a vigência. Campos sensíveis e seus hashes de comparação seguem as regras da chave do processo. O papel de aplicação escreve pelas operações autorizadas e lê as views.

## Consequências

O número CNJ normalizado identifica o hub do processo. A API publica chaves de 64 dígitos hexadecimais. A correção registra outra versão e mantém as evidências. A view adicional `v_achado_historico` permite abrir os resultados anteriores na UI por um caminho de leitura estável. O esquema da 0.2 é instalado em banco novo.

## Referências

Substitui o [ADR 0001](0001-isolamento-por-gabinete-com-rls.md). [Modelo vigente](../sistema/modelo-de-dados.md). [Plano 0.2](../planos/plano_0.2.md).
