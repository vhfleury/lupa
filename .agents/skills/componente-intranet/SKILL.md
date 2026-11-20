---
name: componente-intranet
description: 'Cria ou altera um componente do catálogo do padrão visual da intranet Django (intranet/web/src/lupa_web/templates/componentes) de ponta a ponta: template com parâmetros do include documentados, CSS só com tokens, exemplo na /padrao, teste de tela, seção em docs/sistema/padrao-visual.md e revisão do guardiao-padrao-visual. Use sempre que precisar de um componente novo, variante nova ou mudança de componente.'
---

# Componente da intranet

## Passo a passo

1. Confirme que nenhum componente existente resolve com outro parâmetro (`templates/componentes/` e `docs/sistema/padrao-visual.md`). Componente novo fora do catálogo de RF-VIS-04 é mudança de especificação: pare e pergunte.
2. Vermelho (agente `escritor-testes` ou `tdd`): em `intranet/web/tests/telas/test_padrao.py`, teste que a `/padrao` mostra o componente ou a variante; rode e veja falhar.
3. Template em `templates/componentes/<nome>.html`, chamado por `{% include "componentes/<nome>.html" with ... %}`. Parâmetros com nome em português, valores padrão por `|default`, sem lógica de negócio, sem `style=` nem script.
4. CSS em `static/css/componentes.css`, só com `var(--…)`. Token novo vai em `tokens.css` e no par de contraste de `tests/unit/test_tokens.py`.
5. Exemplo em `templates/padrao.html`, em cada variante, com dado sintético de `telas/padrao.py`.
6. Verde: rebuild do `front` e suíte de `lupa_web` (agente `rodador-verificacao`).
7. Documente em `docs/sistema/padrao-visual.md`: para que serve, quando não usar, parâmetros e o `include` de exemplo.
8. Revisão: `guardiao-padrao-visual` e `especialista-acessibilidade`; capturas pela skill `capturas-visuais`.
9. Commit citando a tarefa.
