---
description: Propõe requisitos novos ou alterados na especificação da 0.2 e lista as perguntas em aberto
argument-hint: <descrição da funcionalidade ou da mudança>
---

Pedido do usuário: $ARGUMENTS

Siga as seções "Versão 0.2" e "Estrutura da documentação" do `CLAUDE.md`.

1. Leia `CLAUDE.md`, `docs/especificacao/0.2/especificacao.md` inteira e os documentos de
   `docs/sistema/` e `docs/decisoes/registro.md` que tratam do mesmo assunto.
2. Levante no código o que o pedido toca: módulos de `pipeline/` e `intranet/`, views `v_*` e
   rotas. Não altere nenhum deles.
3. Se o pedido for bug, ajuste visual ou documentação sem mudança de requisito, diga que ele
   dispensa especificação e pare.
4. Se o pedido reintroduz algo fora do escopo da 0.2 (`gabinete_id`, RLS, papel administrador,
   pseudonimização, Redis, monitoramento, backup), aponte e pergunte antes de seguir.
5. Escreva na especificação os requisitos novos ou alterados, com identificador no padrão
   existente (`RF-<ÁREA>-NN` ou `RNF-NN`, próximo número livre), um comportamento observável cada
   e critério de aceite em Dado/Quando/Então. Valores, nomes e datas dos critérios são fictícios.
6. Tudo que o pedido e o código não decidem vira pergunta (Q1, Q2…), cada uma com as opções que
   você enxerga. Não escolha por conta própria.
7. Marque os requisitos como propostos, sem mudar o estado de aprovação da especificação.
8. Responda com os identificadores criados ou alterados e a lista de perguntas. Não crie plano nem
   código.

Quando o usuário responder, leve cada resposta ao requisito ou critério correspondente. Só registre
a aprovação (com data e número da decisão em `docs/decisoes/registro.md`) quando o usuário aprovar
de forma explícita e não restar pergunta.
