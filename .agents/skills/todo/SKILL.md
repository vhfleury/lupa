---
name: todo
description: Mantém a lista de pendências do Lupa no formato padrão (adicionar, editar, concluir, remover, listar ou reorganizar itens). Use sempre que for pedido registrar, listar ou atualizar um TODO.
---

# TODO

Pedido: $ARGUMENTS

## Formato

```markdown
# TODO

## <pacote>

- [ ] **<título curto>** `<tipo>` — <problema>; <ação esperada> (<revisor>).
  Local: `<caminho/relativo.py>::<símbolo>`
```

## Regras

1. Arquivo único. O `CLAUDE.md` não prevê `todo.md` na raiz: na primeira criação, confirme com o
   usuário se fica em `docs/dividas/todo.md` (com entrada em `docs/README.md`) ou na raiz.
2. Uma seção `##` por pacote (ex.: `pipeline/ingestao`, `intranet/api`, `intranet/web`), em ordem
   alfabética.
3. Um item por checkbox: título em negrito de 2 a 4 palavras, tipo, travessão, problema e ação.
4. Tipo: `bug`, `divida` ou `melhoria`, nessa ordem dentro da seção.
5. `Local:` com caminho e símbolo, sem número de linha.
6. Revisor pela tabela abaixo.
7. Item com plano ou análise em `docs/`: a ação vira link para o `.md`.
8. Sem prosa, datas ou histórico; sem conteúdo de autos.
9. Concluído: remover o item (o histórico fica no git).
10. Seção vazia: remover.
11. O `CLAUDE.md` proíbe comentário inline: não criar `# TODO` no código; o item vive só aqui.

## Revisor por pasta

| Pasta | Revisor |
|---|---|
| `pipeline/src/lupa_pipeline/ingestao/`, `sinteticos/` | especialista-ingestao |
| `pipeline/src/lupa_pipeline/validacoes/` | especialista-validacoes |
| `dominio/`, `migrations/` | especialista-banco |
| `intranet/` | especialista-intranet |
| compose, Dockerfiles, proxy, `scripts/` | especialista-infra |
| `pipeline/tests/`, `intranet/api/tests/` | tdd |
| demais | revisor-codigo |

## Passos

1. Ler o arquivo (criar com `# TODO` se não existir, após a confirmação da regra 1).
2. Adicionar: conferir que caminho e símbolo existem.
3. Editar: localizar pelo título, trocar só os campos pedidos, reconferir o `Local:`.
4. Concluir ou remover: apagar o item.
5. Listar: conferir cada `Local:` no código e apontar os que não existem mais; corrigir só o que o
   usuário confirmar.
6. Reescrever o arquivo inteiro no formato, preservando os demais itens.
