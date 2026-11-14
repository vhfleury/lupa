# Documentação do Lupa

## Usar e operar

- [Guia do assessor](guias/guia-assessor.md) e [guia do desembargador](guias/guia-desembargador.md).
- [Operação do ambiente de desenvolvimento](operacao/operacao.md) e [procedimentos operacionais](runbooks/README.md).
- [Termos, aviso de tratamento, resposta a incidentes e relatório ao tribunal](conformidade/CONFORMIDADE.md).

## Como funciona

| Documento | Abrangência |
| --- | --- |
| [Arquitetura](arquitetura.md) | Componentes e percurso dos autos até a página de evidência |
| [Modelo de dados](sistema/modelo-de-dados.md) | Hubs, links, satélites, views e responsabilidades |
| [Ingestão](sistema/ingestao.md) | Recepção, fila no PostgreSQL, extração, classificação e rastreabilidade |
| [Validações](sistema/validacoes.md) | Regras por classe e reprodução da conta |
| [Agente](sistema/agente.md) | Dossiê, escopo, fontes, tetos e revisão |
| [Auditoria](sistema/auditoria.md) | Cadeia única e relatórios de uso |
| [Criptografia](sistema/criptografia.md) | Cifra por processo e descarte |
| [Interface](sistema/front.md) | Telas por papel, sessão e proxy |
| [Sintéticos](sistema/sinteticos.md) | Gerador de cinco classes, evidências conhecidas e medição |

## Especificação, plano e decisões

- [Especificação da 0.2](especificacao/0.2/especificacao.md).
- [Plano da 0.2](planos/plano_0.2.md), [algoritmos e checklist](planos/plano_0.2_execucao.md) e [tarefas com evidências](planos/tarefas_0.2.md).
- [ADRs](adr/README.md) e [registro das decisões](decisoes/registro.md).
- [Defesas contra instruções presentes nos autos](especificacao/prompt-injection.md) e [decisão sobre o object storage](decisoes/object-storage.md).

## Histórico da 0.1

O [histórico das etapas](etapas/ETAPAS.md), os [requisitos anteriores](especificacao/requisitos-v1.md), o [desenho inicial](especificacao/arquitetura.md) e o [catálogo criminal anterior](especificacao/catalogo-validacoes.md) documentam a versão de origem. A decisão de preservar as duas falhas históricas de T1.7 e a verificação dos responsáveis na 0.2 estão no [quadro de tarefas](planos/tarefas_0.2.md).

Na raiz estão o [README](../README.md), o [guia de contribuição](../CONTRIBUTING.md) e o [changelog](../CHANGELOG.md).
