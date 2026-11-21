---
description: Lista as fases de um plano aprovado como caixas em docs/planos/tarefas_0.2.md
argument-hint: <caminho do plano em docs/planos/>
---

Plano: $ARGUMENTS

Siga as seções "Versão 0.2", "Conteúdo obrigatório de um plano" e "Entrega de cada tarefa" do
`CLAUDE.md`. As tarefas são as fases do plano; este comando não cria tarefas novas.

1. Leia `CLAUDE.md`, o plano e `docs/planos/tarefas_0.2.md`. Sem caminho informado, pergunte qual
   plano usar.
2. Pare e avise o usuário se o plano não estiver aprovado, se alguma fase não tiver requisito,
   agente, arquivos, dependências, Vermelho (ou "revisão manual") e Pronto quando, ou se o plano
   tiver decisão pendente.
3. Acrescente em `docs/planos/tarefas_0.2.md` uma seção com o nome do plano, a branch e o PR
   únicos, e uma caixa por fase: `- [ ] **T<nn>.<n>** <resumo> — <requisito>. [F<n>](<plano>#f<n>)`,
   continuando a numeração do arquivo. O detalhe fica só no plano.
4. Responda com a lista de caixas e os grupos de fases que podem rodar em paralelo. Não comece a
   implementação.
