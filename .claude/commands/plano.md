---
description: Gera o plano em docs/planos/ a partir de requisitos aprovados da especificação da 0.2
argument-hint: <tema e identificadores dos requisitos>
---

Pedido: $ARGUMENTS

Siga as seções "Versão 0.2" e "Conteúdo obrigatório de um plano" do `CLAUDE.md`.

1. Leia `CLAUDE.md`, `docs/especificacao/0.2/especificacao.md` e os planos existentes em
   `docs/planos/`. Sem requisitos informados, pergunte quais.
2. Pare e avise o usuário se algum requisito citado não estiver aprovado ou tiver pergunta em
   aberto.
3. Levante no código todas as decisões de implementação que a especificação não fixa e pergunte
   todas ao usuário antes de escrever. O plano não sai com decisão pendente. Decisão que muda um
   requisito volta para a especificação.
4. Crie `docs/planos/plano_<tema>.md` (sem branch nem commit). A primeira linha depois do título
   lista os requisitos que o plano cobre.
5. Abra com "O que muda": tabela `Objeto | Antes | Depois` (cada tabela, coluna, índice, função ou
   view, com o tipo), tabela `Arquivo | Ação` e lista "O que não muda".
6. Problemas e decisões numerados (P/D); fases de uma linha que citam P/D e requisitos; cada fato
   uma vez; sem motivação nem resultado previsto.
7. Seção "Passo a passo do algoritmo": passos numerados com entrada, ação e saída; desvios,
   paradas e erros como passos próprios; um bloco por algoritmo (ou em
   `docs/planos/plano_<tema>_execucao.md`, com lista de arquivos e checklist de testes).
8. Mudança de modelo entra como revisão `migrations/versions/vNNNN_<tema>.py` com `upgrade`,
   `downgrade` e teste com `migrar`.
9. Checklist de testes: cada critério de aceite vira pelo menos um teste, no formato
   `<requisito>: <arquivo de teste>::<nome do teste> — <o que verifica>`. Exceções do `CLAUDE.md`
   marcadas como revisão manual.
10. Execução em no máximo 3 etapas, na ordem de `docs/operacao/operacao.md`.
11. Inclua o plano em `docs/README.md`. Responda com o caminho e a tabela `Requisito | Teste`. Não
    escreva código.
