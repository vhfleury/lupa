# TODO

## infra

- [ ] **CI obrigatório no merge** `melhoria` — a proteção de `main` e `develop` só exige PR, sem
  CI; quando houver CI, criar o workflow que dispara em PR para `develop` e `main` e ligar os
  checks obrigatórios na proteção das branches (especialista-infra).
  Local: `docs/decisoes/registro.md::Regras de Git — 20/11/2026`

## pipeline

- [ ] **Outorgante como sujeito do fato de procuração** `divida` — o fato de procuração guarda
  o outorgante no valor, não no sujeito; gravá-lo como sujeito muda o id do fato
  (`chave_hash([processo, tipo, sujeito, evidência])`), e correções e notas do gabinete apontam
  para esse id. Exige plano próprio que migre ou religue correções e notas (especialista-banco,
  especialista-validacoes).
  Local: `docs/planos/plano_limpeza_pipeline.md::D13`
- [ ] **Fatos antigos com valor `{"valor": x}`** `divida` — a F10 desembrulha esse formato ao
  ler para as validações, e a API devolve o gravado (D16). Se houver linhas assim no banco, o
  recálculo grava `x` nos `valores` do achado (mesmo resultado) e a ferramenta de leitura do
  agente (`agente/ferramentas/leitura.py`) ainda mostra o valor cru. Contar as linhas com o
  especialista-banco e, se houver, alinhar a leitura do agente.
  Local: `docs/planos/plano_limpeza_pipeline.md::D16`
- [ ] **Ids de fato e evidência diferentes das chaves dos hubs** `divida` — a pipeline calcula o
  id da evidência por `chave_hash([hk_pagina, inicio, fim])` e o do fato por
  `chave_hash([hk_processo, tipo, sujeito, evidência])`, mas `hub_evidencia` e `hub_fato` usam
  `numero_cnj`, `sha256` e `numero` do arquivo. Unificar exige levar esses campos a
  `PaginaTexto`, mudar as chaves e regravar os ids, com correções e notas religadas
  (especialista-banco, especialista-ingestao).
  Local: `docs/planos/plano_limpeza_pipeline.md::F12`
