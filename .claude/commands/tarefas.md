---
description: Quebra um plano aprovado em tarefas de TDD em docs/planos/tarefas_0.2.md, cada uma ligada a um requisito
argument-hint: <caminho do plano em docs/planos/>
---

Plano: $ARGUMENTS

Siga as seções "Versão 0.2", "Entrega de cada tarefa" e "Desenvolvimento orientado a testes" do
`CLAUDE.md`.

1. Leia `CLAUDE.md`, o plano, o `_execucao.md` dele se houver, a especificação da 0.2 e
   `docs/planos/tarefas_0.2.md`. Sem caminho informado, pergunte qual plano usar.
2. Pare e avise o usuário se o plano não estiver aprovado ou se o checklist de testes deixar algum
   critério de aceite sem teste.
3. Quebre cada fase em tarefas pequenas, na ordem de execução. Cada tarefa entrega um
   comportamento e cabe em um commit.
4. Acrescente as tarefas em `docs/planos/tarefas_0.2.md`, continuando a numeração e o formato já
   usados no arquivo; cada tarefa traz:
   - requisito atendido (`RF-<ÁREA>-NN` ou `RNF-NN`) e fase do plano;
   - Vermelho: `<arquivo de teste>::<nome do teste>` e ver falhar;
   - Verde: mudança mínima no arquivo de código;
   - Limpeza: refatoração, ou "nenhuma";
   - Pronto quando: suíte do pacote verde no contêiner depois do rebuild, `ruff` e `mypy` limpos.
5. Migration vem em tarefa própria, antes da primeira que depende dela. Tarefa de exceção ao TDD
   (componente só de apresentação, `llm`, `carga`, E2E) diz "revisão manual" no lugar de Vermelho
   e Verde.
6. Confira que todo critério de aceite do plano aparece em pelo menos uma tarefa.
7. Responda com a lista de tarefas e a tabela `Requisito | Tarefa`. Não comece a implementação.
