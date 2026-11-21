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
