---
name: atualizar-padrao-docs
description: 'Atualiza a documentação do Lupa depois de uma mudança de comportamento, componente, chave ou falha, seguindo a seção Estrutura da documentação do CLAUDE.md: docs/sistema/, docs/arquitetura.md, CHANGELOG.md (Não publicado), docs/decisoes/registro.md, ADR e docs/README.md, com conferência de links. Use no fim de cada fase e antes do PR.'
---

# Atualizar a documentação

## Passo a passo

1. Liste o que mudou: `git diff --stat <base>...HEAD` e a tarefa ou plano.
2. Decida o que cada mudança obriga:
   - comportamento já descrito → o documento de `docs/sistema/` correspondente;
   - componente, chave ou comportamento em falha → `docs/arquitetura.md`;
   - percebido pelo usuário ou operador → `CHANGELOG.md`, seção `Não publicado`;
   - decisão nova → `docs/decisoes/registro.md`; se define arquitetura, ADR novo no modelo de `docs/adr/README.md`;
   - documento novo → `docs/README.md`.
3. Delegue a escrita ao agente `documentador`, passando a lista do passo 2.
4. Rode o agente `conferente-links` sobre os `.md` alterados e corrija o que ele apontar.
5. Não altere a especificação aprovada nem `docs/etapas/ETAPAS.md`.
6. Commit de documentação citando a tarefa.
