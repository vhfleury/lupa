---
name: capturas-visuais
description: Gera as capturas de tela da intranet Django (tema claro e escuro a 1200 px, claro a 375 px), compara com as anteriores e devolve um resumo do que mudou por tela, para aprovação visual do usuário. Use depois de toda mudança visual e antes de pedir aprovação.
---

# Capturas visuais

## Passo a passo

1. Guarde as capturas atuais: copie `<scratchpad>/visual/` para `<scratchpad>/visual-anterior/`, se existir.
2. Rode `LUPA_CAPTURAS_VISUAL=<scratchpad>/visual bash intranet/web/scripts/capturas.sh` em background (agente `rodador-verificacao`). As capturas dos guias saem em `docs/imagens/`.
3. Confira que cada tela tem `<tela>-claro-1200.png`, `<tela>-escuro-1200.png` e `<tela>-claro-375.png` (e `padrao-*` quando existir).
4. Compare cada par anterior/atual: abra as duas imagens e anote diferenças visíveis (cor, fonte, espaçamento, quebra, rolagem horizontal a 375 px, contraste no escuro).
5. Devolva a tabela `Tela | Mudou | O que mudou | Suspeita de defeito` e a lista das imagens a enviar ao usuário (as que mudaram, até 8, priorizando claro 1200).
6. O agente principal envia as imagens com `SendUserFile` e pede a aprovação. Não marque aprovação sem a resposta do usuário.
