# Plano — cadastro do processo pelo arquivo

15 de novembro de 2026 · Estado: **executado** · Atende a
[especificação da 0.2](../especificacao/0.2/especificacao.md): RF-PRO-01, RF-PRO-06, RF-ING-01,
RF-ING-02, RF-ING-04, RF-FAT-01, RF-FAT-04.

## O que muda

### Banco

| Objeto | Antes | Depois |
| --- | --- | --- |
| `hub_fato`, CHECK `tipo_valido` (constraint) | 15 valores de `TipoFato` | os 15 mais `relator`, `orgao_julgador`, `assunto`, `valor_causa`, `juizo_origem`, `data_distribuicao` |
| `sat_processo_dados.hk_usuario` (`BYTEA`) | quem criou o processo; uma linha por processo | autor da linha: quem criou na primeira, quem corrigiu a classe nas seguintes |
| `v_processo.classe` (`TEXT`) | da linha mais recente de `sat_processo_dados` | igual |
| `v_processo.hk_criador` (`BYTEA`), `v_processo.criador_id` (`TEXT`) | da linha mais recente de `sat_processo_dados` | da linha mais antiga |
| `v_processo.classe_anterior` (`TEXT`, nula) | não existe | `classe` da penúltima linha de `sat_processo_dados` |
| `v_processo.hk_classe_corrigida_por` (`BYTEA`, nula), `v_processo.classe_corrigida_por_id` (`TEXT`, nula) | não existem | `hk_usuario` da linha mais recente, quando há mais de uma |
| `v_processo.classe_corrigida_em` (`TIMESTAMPTZ`, nula) | não existe | `load_dts` da linha mais recente, quando há mais de uma |

As colunas novas de `v_processo` entram no fim, por `CREATE OR REPLACE VIEW`.

### Arquivos

| Arquivo | Ação |
| --- | --- |
| `pipeline/src/lupa_pipeline/migrations/versions/v0002_cadastro_pelo_arquivo.py` | criar: `upgrade` e `downgrade` do CHECK de `hub_fato.tipo` e de `v_processo` |
| `pipeline/tests/dominio/test_migracao_0002.py` | criar: sobe e desce com `migrar` |
| `pipeline/src/lupa_pipeline/dominio/enums.py` | acrescentar os seis valores a `TipoFato` |
| `pipeline/src/lupa_pipeline/dominio/visoes.py` | acrescentar a `VisaoProcesso` as quatro colunas novas |
| `pipeline/src/lupa_pipeline/config.py` | acrescentar `identificacao_paginas` (3) e `identificacao_tempo_segundos` (30) |
| `.env.example` | acrescentar `LUPA_IDENTIFICACAO_PAGINAS` e `LUPA_IDENTIFICACAO_TEMPO_SEGUNDOS` |
| `pipeline/src/lupa_pipeline/ingestao/dados/eventos.yaml` | acrescentar a seção `capa` (rótulos de número, classe e dos seis dados) e subir `versao` para `civel-0.3.0` |
| `pipeline/src/lupa_pipeline/ingestao/identificacao.py` | criar: A1 (leitura no sandbox) e A2 (número e classe a partir do texto) |
| `pipeline/src/lupa_pipeline/ingestao/eventos/capa.py` | criar: A4 |
| `pipeline/src/lupa_pipeline/ingestao/eventos/fatos.py` | chamar `capa.extrair` nas páginas de número até `identificacao_paginas` |
| `pipeline/src/lupa_pipeline/sinteticos/roteiro.py`, `gabarito.py`, `gerador.py` | capa sintética e gabarito com relator, órgão julgador, assunto, valor da causa, juízo de origem e distribuição |
| `intranet/api/src/lupa_intranet/api/rotas/ingestao.py` | criar a rota `POST /processos/arquivos` (A3) |
| `intranet/api/src/lupa_intranet/api/rotas/processos.py` | remover a rota `POST /processos` e `CorpoProcesso`; `gravar_processo` passa a receber número e classe; criar `POST /processos/{processo_id}/classe` (A5); `_serializar` devolve as colunas novas |
| `intranet/api/src/lupa_intranet/auditoria/eventos.py` | acrescentar `CLASSE_CORRIGIDA` a `AcaoAuditoria` |
| `intranet/api/src/lupa_intranet/agente/dossie.py` | ficha com os seis dados da capa |
| `intranet/api/scripts/e2e_processos.py` | criar os processos pelo envio do arquivo |
| `intranet/web/src/lib/processos/envio.ts`, `tipos.ts`, `rotulos.ts` | `enviarProcesso`, tipos da resposta e do complemento, rótulos dos seis fatos |
| `intranet/web/src/lib/processos/NovoProcesso.svelte` | criar: envio, progresso, pedido do que faltou (A6) |
| `intranet/web/src/lib/processos/CabecalhoProcesso.svelte` | criar: partes, dados da capa e correção da classe |
| `intranet/web/src/routes/processos/+page.svelte` | trocar o formulário de número e classe por `NovoProcesso` |
| `intranet/web/src/routes/processos/[id]/+page.svelte` | usar `CabecalhoProcesso` |
| `intranet/web/src/lib/processos/cadastro.test.ts` | reescrever para o envio; sai o caso do formulário (D8) |
| `intranet/api/tests/api/test_processos.py`, `test_processos_lista.py`, `test_responsaveis.py`, `intranet/api/tests/auditoria/test_eventos_reais.py` | casos do `POST /processos` saem (D8); a preparação passa a usar `criar_processo_teste` |
| `intranet/web/e2e/testes/processos.spec.ts`, `acessibilidade.spec.ts`, `seguranca.spec.ts`, `intranet/web/e2e/capturas.spec.ts` | cadastro pelo envio |
| `docs/guias/guia-assessor.md`, `docs/imagens/processos.png`, `docs/imagens/processo.png` | passo 2 e capturas |
| `docs/sistema/ingestao.md`, `docs/sistema/modelo-de-dados.md`, `docs/sistema/front.md`, `docs/sistema/sinteticos.md`, `docs/arquitetura.md` | comportamento novo |
| `docs/decisoes/registro.md` | D1 a D14 |
| `docs/adr/0017-cadastro-pelo-arquivo.md`, `docs/adr/README.md` | ADR novo, ligado ao 0003 |
| `docs/planos/plano_0.2_execucao.md` | A3 passa a remeter a este plano para o envio que cria processo |
| `docs/planos/tarefas_0.2.md` | fase 8 com as tarefas deste plano |
| `CHANGELOG.md` | seção `Não publicado` |
| `docs/README.md` | link deste plano |

### O que não muda

- `POST /processos/{id}/arquivos`: envio a processo existente, quarentena e duplicidade.
- Chaves de negócio dos hubs, `chave_objeto`, DEK por processo e `lacrar`.
- Fila `v_fila_ingestao`, worker, lotes, OCR, saneamento e índice de peças.
- Extração de partes (`eventos/partes.py`) e `v_parte`.
- `GET /processos`: mesmos campos; não lê partes nem fatos.
- `POST /processos/{id}/fatos/{fato_id}/corrigir`: serve aos seis fatos novos sem alteração.
- `listar_achados`: já filtra pelas regras e recorrentes da classe corrente.
- Papéis e permissões; `link_evento_auditoria` (a coluna `acao` não tem CHECK).
- `pyproject.toml`, `docker-compose*.yml`, `Dockerfile`, `Caddyfile` e `requirements*.txt`.

## Problemas

- **P1.** `numero_cnj` está na chave de `hub_arquivo`, `hub_pagina`, `hub_peca`, `hub_evidencia`,
  `hub_fato`, `hub_achado` e `hub_parte`, e o objeto é cifrado com a DEK do processo: o arquivo
  não pode ser lacrado antes de o número ser conhecido.
- **P2.** Nenhum código lê número CNJ ou classe do texto.
- **P3.** A API não abre PDF; a leitura hoje só acontece no worker.
- **P4.** `v_processo` lê criador e classe da mesma linha de `sat_processo_dados`; uma linha de
  correção de classe trocaria o criador.
- **P5.** `hub_fato.tipo` tem CHECK com os valores de `TipoFato`.
- **P6.** O gatilho de `data_ajuizamento` em `eventos.yaml` aceita "distribuição".
- **P7.** Os rótulos da capa real do Projudi/PJD não podem ser conferidos em teste (`dados/` não
  é lido).
- **P8.** Dois envios simultâneos do mesmo número novo disputam a criação de `hub_processo`.
- **P9.** Testes e scripts usam `POST /processos` como preparação.

## Decisões

- **D1.** A API lê o arquivo ainda no temporário, antes de qualquer gravação: inspeção e extração
  das páginas 1 a `identificacao_paginas` pelos módulos do sandbox já existentes
  (`parser_pdf`, `inventario`, `extrator_paginas`), com `LimitesSandbox` e
  `identificacao_tempo_segundos`. Resolve P1 e P3. Decisões 30 e 39 da especificação.
- **D2.** O número do processo é o primeiro número CNJ com dígito verificador válido que segue um
  rótulo de `capa.numero` na página 1; sem rótulo, o único número válido distinto nas páginas
  lidas; com mais de um e sem rótulo, não há número. Resolve P2.
- **D3.** A classe é o texto que segue um rótulo de `capa.classe`, comparado sem acento e sem
  caixa com a tabela de `capa.classes`; "apelação criminal" e texto fora da tabela não dão
  classe. Ações originárias reconhecidas: ação rescisória, mandado de segurança, reclamação e
  conflito de competência. A classe não é inferida das peças.
- **D4.** Número ou classe faltando, tempo esgotado ou falha de recurso na leitura: resposta 422
  `identificacao_incompleta` com o lido, o que falta e os números encontrados; nada é gravado. O
  navegador reenvia o mesmo `File` com `numero_cnj` e `classe` na query; não há estado no
  servidor entre os dois envios. Valor informado prevalece sobre o lido. Decisão 32.
- **D5.** Arquivo que a inspeção recusa (`MotivoQuarentena`) ou de tipo desconhecido: 422 com o
  motivo, sem gravação, inclusive quando número e classe vêm informados. Decisão 38.
- **D6.** Número já cadastrado: o arquivo é lacrado no processo existente; a classe lida é
  ignorada. Processo descartado: 409. Decisão 33.
- **D7.** A criação é serializada por `pg_advisory_xact_lock` sobre os 4 primeiros bytes do
  `hk_processo`, com chave de espaço própria, tomado antes de consultar `v_processo`. Resolve P8.
- **D8.** A rota `POST /processos`, `CorpoProcesso` e o formulário de número e classe são
  removidos; os testes do cadastro manual saem no mesmo commit, e os que usavam a rota só como
  preparação passam a `criar_processo_teste`, sem mudar asserção. Resolve P9. Decisão 34.
- **D9.** Os seis dados da capa são fatos com `sujeito` vazio, extraídos pelo worker das páginas
  de número até `identificacao_paginas` de cada arquivo, pelo fluxo `candidatos_da_peca` →
  `confirmar`. `valor_causa` é decimal em texto (`"1234.56"`); `data_distribuicao` é data ISO e
  entra na linha do tempo do dossiê pelo prefixo `data_`. Resolve P5. Decisão 35.
- **D10.** `capa.py` só roda nas páginas da capa e o gatilho de `data_ajuizamento` não muda; a
  capa não é peça de marco, então "Distribuição" da capa não gera `data_ajuizamento`. Resolve P6.
- **D11.** Correção de classe é linha nova em `sat_processo_dados` com o `hk_usuario` de quem
  corrigiu, sob `travar_processo`, seguida de `atualizar_achados` na mesma transação e do evento
  `classe_corrigida`. Exige a permissão `anotar`, que os dois papéis têm. `v_processo` passa a ler o criador da linha
  mais antiga. Resolve P4. Decisão 36.
- **D12.** Os rótulos de `capa` são os da capa sintética mais variantes usuais (`Processo nº`,
  `Autos nº`, `Número do processo`, `Classe`, `Classe processual`, `Classe judicial`, `Relator`,
  `Órgão julgador`, `Assunto`, `Valor da causa`, `Juízo de origem`, `Comarca`, `Distribuição`,
  `Data de distribuição`). Capa real fora desses rótulos cai em D4; acrescentar rótulo é edição
  de `eventos.yaml` com nova `versao`, que reprocessa os fatos (RF-ING-08). Resolve P7.
- **D13.** As partes e os dados da capa aparecem no cabeçalho do processo, lidos de
  `GET /processos/{id}/dossie`. Decisão 37.
- **D14.** Subir `versao` de `eventos.yaml` faz o worker refazer os fatos dos processos já
  ingeridos, que passam a ter os dados da capa sem novo envio.

## Fases

1. Migration `v0002`, `TipoFato` e `VisaoProcesso` (P4, P5, D9, D11). RF-PRO-06, RF-FAT-01.
2. Identificação: `identificacao.py`, rótulos em `eventos.yaml`, configuração (D1 a D3, D12).
   RF-PRO-01, RF-ING-04.
3. Rota `POST /processos/arquivos` e remoção do cadastro manual (D4 a D8). RF-PRO-01, RF-ING-01,
   RF-ING-02.
4. Dados da capa como fatos, capa sintética e gabarito (D9, D10, D14). RF-FAT-01.
5. Correção da classe (D11). RF-PRO-06.
6. Interface: `NovoProcesso`, `CabecalhoProcesso`, rótulos, E2E e capturas (D4, D13). RF-PRO-01,
   RF-PRO-06, RF-FAT-04.
7. Documentação, ADR 0017, registro de decisões, changelog e guia. RF-DOC-01, RF-DOC-03.

## Passo a passo do algoritmo

### A1. Leitura das primeiras páginas (`ingestao/identificacao.py`, na API)

1. Entrada: `ArquivoRecebido` no temporário, `Settings`. Ação: se o tipo é desconhecido, parar.
   Saída: `LeituraRecusada(tipo_invalido)`.
2. Entrada: arquivo ZIP. Ação: `inventariar_zip` em diretório temporário próprio; a fonte é a
   primeira entrada. Saída: caminho do primeiro PDF. Desvio: `ZipRecusadoError` vira
   `LeituraRecusada(motivo)`.
3. Entrada: caminho do PDF. Ação: `inspecionar_pdf`. Saída: quantidade de páginas. Desvio:
   `motivo_do_parser` com motivo vira `LeituraRecusada(motivo)`.
4. Entrada: PDF e páginas. Ação: `executar_tarefa` das páginas 1 a
   `min(identificacao_paginas, páginas)`, com `tempo_segundos = identificacao_tempo_segundos`.
   Saída: texto normalizado por página.
5. Erro: `FalhaSandboxError` ou `motivo_falha` nos passos 2 a 4. Ação: registrar em log o motivo
   e o `sha256`, sem texto. Saída: `Leitura` sem páginas (segue para D4).
6. Parada: o diretório temporário da leitura é apagado em qualquer saída.

### A2. Número e classe (`ingestao/identificacao.py`, função pura)

1. Entrada: textos das páginas. Ação: localizar números no formato CNJ (com máscara ou 20
   dígitos) e manter os que passam em `validar_numero_cnj`. Saída: números distintos, na ordem.
2. Entrada: página 1 e rótulos `capa.numero`. Ação: procurar número válido logo após um rótulo.
   Saída: `numero_cnj`. Desvio: sem rótulo e um único número distinto, é ele; caso contrário,
   `numero_cnj` vazio.
3. Entrada: páginas e rótulos `capa.classe`. Ação: tomar o texto até o fim da linha após o
   rótulo, dobrar e comparar com `capa.classes`. Saída: `ClasseProcessual` ou vazio.
4. Saída final: `Identificacao(numero_cnj, classe, numeros_encontrados)`.

### A3. Envio que cria o processo (`POST /processos/arquivos?nome=&numero_cnj=&classe=`)

1. Entrada: corpo em streaming. Ação: `receber`. Saída: `ArquivoRecebido`. Erro: recusa por
   tamanho (413) ou vazio (422), com `upload` `negado` na auditoria.
2. Entrada: `numero_cnj` informado. Ação: `validar_numero_cnj`. Erro: 422 com a razão.
3. Entrada: arquivo. Ação: A1. Desvio: `LeituraRecusada` devolve 422 com `motivo`, registra
   `upload` `negado` e para.
4. Entrada: páginas lidas. Ação: A2; valor informado substitui o lido. Desvio: falta número ou
   classe: 422 `identificacao_incompleta` com `lido`, `faltando` e `numeros_encontrados`,
   registra `upload` `falha` sem processo e para.
5. Entrada: número. Ação: calcular `hk_processo` e tomar a trava de D7. Saída: transação
   serializada para esse número.
6. Entrada: `hk_processo`. Ação: ler `v_processo`. Desvio: descartado, 409 e para. Desvio:
   existe, segue ao passo 8 com `processo_criado = false`.
7. Entrada: número, classe e ator. Ação: `gravar_processo` e evento `processo_criado`. Saída:
   processo com DEK e, se o ator é assessor, responsável inicial.
8. Entrada: processo. Ação: `ativar_processo` e `lacrar`. Saída: `ResultadoLacre`.
9. Entrada: lacre não duplicado. Ação: evento `upload`.
10. Saída: 201 (200 se duplicado) com `processo_id`, `numero_cnj`, `classe`, `processo_criado`,
    `arquivo_id`, `estado`, `sha256`, `tamanho_bytes`, `mime`, `duplicado` e `origem` de número e
    classe (`lido`, `informado` ou `existente`).
11. Parada: o temporário do envio é apagado em qualquer saída. Erro em 7 a 9 desfaz a transação;
    o objeto órfão é sobrescrito no próximo envio (A3 do plano da 0.2, passo 8).

### A4. Dados da capa (`ingestao/eventos/capa.py`, no worker)

1. Entrada: `Fonte` de página com número até `identificacao_paginas`. Ação: para cada um dos
   seis tipos, procurar o rótulo de `capa` e tomar o valor até o fim da linha. Saída: candidato
   com o intervalo do valor e `sujeito` vazio.
2. Entrada: candidato `valor_causa`. Ação: converter `R$ 1.234,56` em `"1234.56"`. Desvio: valor
   que não converte não gera candidato.
3. Entrada: candidato `data_distribuicao`. Ação: converter pela rotina de datas existente.
   Desvio: data inválida não gera candidato.
4. Entrada: candidatos. Ação: `confirmar`. Saída: fato com evidência. Desvio: trecho que não
   confere não é gravado (RF-FAT-01).
5. Entrada: dois arquivos com valores diferentes. Saída: dois fatos vigentes (RF-FAT-02).

### A5. Correção da classe (`POST /processos/{processo_id}/classe`)

1. Entrada: `{classe}` e ator com `anotar`. Ação: `exige_processo`. Erro: 409 se descartado.
2. Entrada: processo. Ação: `travar_processo`. Desvio: classe igual à corrente, devolve o
   processo sem gravar e para.
3. Entrada: classe nova. Ação: `gravar_satelite` em `sat_processo_dados` com `hk_usuario` do
   ator.
4. Entrada: processo. Ação: `ativar_processo` e `atualizar_achados` com `ctx.agora.date()`.
   Saída: achados da nova classe.
5. Ação: eventos `classe_corrigida` e `validacao_executada`.
6. Saída: processo serializado com `classe`, `classe_anterior`, `classe_corrigida_por_id` e
   `classe_corrigida_em`.

### A6. Tela de novo processo (`NovoProcesso.svelte`, `envio.ts`)

1. Entrada: `File`. Ação: `problemaArquivo`. Erro: mensagem na tela e para.
2. Ação: `enviarProcesso(arquivo, complemento, aoProgredir)`. Saída: barra de progresso e, ao
   fim do envio, "Identificando o processo…".
3. Desvio: 201 ou 200. Ação: ir a `/processos/{id}` com o aviso de criado, anexado ou duplicado.
4. Desvio: 422 `identificacao_incompleta`. Ação: mostrar o que foi lido, os números encontrados
   para escolha e só os campos que faltam; ao confirmar, voltar ao passo 2 com o complemento e o
   mesmo `File`.
5. Erro: outro 4xx ou falha de rede. Ação: mostrar a mensagem do servidor; o arquivo continua
   selecionado.

### Checklist de testes

Cada teste cita o requisito na docstring. U: unitário; I: integração.

- [x] I: `v0002` sobe e desce; `v_processo` devolve criador da primeira linha e os campos de
  correção (RF-PRO-06).
- [x] U: A2 com rótulo, com número único sem rótulo, com dois números sem rótulo, com dígito
  inválido e sem número (RF-PRO-01).
- [x] U: A2 reconhece as cinco classes, recusa "apelação criminal" e texto fora da tabela
  (RF-PRO-01).
- [x] U: A1 com executor injetado: PDF, ZIP, tipo desconhecido, motivo de quarentena e tempo
  esgotado (RF-PRO-01, RF-ING-02).
- [x] I: o subprocesso de A1 falha ao abrir conexão e não recebe variável com credencial
  (RF-ING-04).
- [x] I: envio de autos sintéticos de cada classe cria o processo com número, classe, criador,
  responsável e arquivo `recebido`, com `processo_criado` e `upload` na auditoria (RF-PRO-01,
  RF-ING-01).
- [x] I: capa sem classe devolve 422 com `faltando`; o reenvio com `classe` cria o processo;
  entre os dois nada foi gravado (RF-PRO-01).
- [x] I: número informado com dígito inválido é recusado (RF-PRO-01).
- [x] I: número já cadastrado anexa o arquivo, mantém a classe e devolve `processo_criado`
  falso; os mesmos bytes devolvem 200 com `duplicado` (RF-PRO-01, RF-ING-01).
- [x] I: número de processo descartado devolve 409 (RF-PRO-01).
- [x] I: PDF com senha devolve 422 `senha` e nenhuma linha nova em hub, link ou satélite
  (RF-PRO-01, RF-ING-02).
- [x] I: dois envios simultâneos do mesmo número novo resultam em um processo e dois arquivos
  (RF-PRO-01).
- [x] I: `POST /processos` devolve 405 (RF-PRO-01).
- [x] U: `capa.extrair` gera os seis candidatos com o intervalo do valor; valor e data
  inválidos não geram candidato (RF-FAT-01).
- [x] I: ingestão do sintético de referência grava os seis fatos do gabarito com evidência que
  confere, e `data_distribuicao` aparece na linha do tempo (RF-FAT-01).
- [x] I: fato da capa corrigido continua vigente depois do reprocessamento (RF-FAT-03,
  RF-ING-08).
- [x] I: correção de classe grava a linha, mantém o criador, refaz os achados para a nova classe
  e registra `classe_corrigida`; classe igual não grava; descartado devolve 409 (RF-PRO-06).
- [x] U (front): `NovoProcesso` envia, mostra o complemento só dos campos que faltam e reenvia
  o mesmo arquivo; `enviarProcesso` monta a query (RF-PRO-01).
- [x] U (front): `CabecalhoProcesso` mostra partes com polo, os seis dados e a classe anterior
  (RF-FAT-04, RF-PRO-06).
- [x] Medição dos sintéticos dentro da meta do RNF-02 com os seis tipos novos.

Revisão manual: fluxo E2E do Playwright (`processos.spec.ts`), capturas dos guias e conferência
da tela no navegador.

## Execução

1. Commits em `feat/versao-0.2`, um por tarefa.
2. `docker compose up -d --build --wait`.
3. `docker compose exec api alembic -c pipeline/src/lupa_pipeline/migrations/alembic.ini upgrade head`.

Os resultados dos testes e da medição dos autos sintéticos estão na [fase 8 do registro de tarefas](tarefas_0.2.md#fase-8--cadastro-pelo-arquivo).
