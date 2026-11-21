# Plano — limpeza da pipeline

20 de novembro de 2026, reescrito em 21/11/2026 no formato de um PR por plano · Estado:
**aprovado** · Branch e PR únicos: `refactor/limpeza-pipeline` · Atende a
[especificação da 0.2](../especificacao/0.2/especificacao.md): RNF-08, RF-ING-03, RF-ING-04,
RF-ING-07, RF-ING-08, RF-FAT-01, RF-FAT-02, RF-VAL-01 a RF-VAL-05. Nenhum requisito muda; o
resultado de ingestão, fatos e achados é o mesmo, fixado pelos testes existentes e pelos novos
testes de igualdade.

## O que muda

### Banco

Nenhuma tabela, coluna, índice, função ou view muda. Sem migration.

### Código

| Objeto | Antes | Depois |
| --- | --- | --- |
| `ingestao/texto.py` (módulo) | não existe | `dobrar`, `levenshtein`, `colapsar_espacos`, `maiusculas_sem_acento` (D1, D2) |
| `datas.dobrar`, `deteccao.dobrar` (funções) | duas regras | saem; quem usa importa `texto.dobrar`, com a regra de `datas.py` (D1) |
| `hibridas.levenshtein`, `medicao.levenshtein` | duas cópias | `texto.levenshtein`, a versão com corte de prefixo e sufixo (D2) |
| `sinais_fronteira.normalizar`, `medicao.normalizar`, `hibridas._normalizar` | três nomes iguais, regras diferentes | `texto.maiusculas_sem_acento` e `texto.colapsar_espacos` (D2) |
| `eventos.modelo.PaginaTexto` (dataclass) | só o texto normalizado | ganha `dobrado` e `datas`, calculados uma vez (D3) |
| `datas.TextoAnalise`, `datas.encontrar_datas` | sem uso em produção | removidos com o teste (D9) |
| `datas.UNIDADES` | lista própria | montada das tuplas de escrita por extenso |
| `data_peca.MESES`, `ANO_MINIMO`, `ANO_MAXIMO` e a checagem de faixa | cópia | `datas.MESES`, `datas.construir_data` |
| `data_peca.REGRAS` | `(tipo, padrão)` e `if tipo == "juntada"` | `(tipo, padrão, direção)` |
| `calibracao.sha256_arquivo` | laço próprio, `TAMANHO_BLOCO` próprio | em `dominio/esquemas.py`, ao lado de `calcular_hash` |
| `eventos/fatos.py`, `eventos/modelo.py` (ids de fato e evidência) | `chave_hash(...).hex()` à mão | `chave_do_hub(hub_fato, ...)`, `chave_do_hub(hub_evidencia, ...)` (D10) |
| `eventos/fatos.candidatos_da_peca` | conjuntos, ifs e dicionário misturados | um registro `EXTRATORES: TipoPeca → extratores`; a capa é um extrator com filtro de página (D11) |
| `eventos/capa._valor` | ifs por `TipoFato` | `CONVERSORES_CAPA: TipoFato → conversor` |
| `eventos/etapa.processar_eventos` | lê processo e fatos duas vezes | passa o processo lido adiante |
| `dominio/esquemas.Fato.valor` (`Any`) | escalar ou `{"valor": ...}` | sempre o escalar; `de_registro` converte o formato antigo ao ler (D12) |
| `validacoes/modelo.valor_de` | desembrulha em cada consumidor | removida; consumidores leem `fato.valor` |
| `eventos/saida.py`, `sinteticos/gerador.py` (caso `PROCURACAO`) | cada um troca o outorgante pelo nome | `partes.nome_do_outorgante`, usado pelos dois; o fato de procuração não muda (D13) |
| `dominio/esquemas.Anotacao`, `Usuario`, `JobIngestao`, `LoteIngestao`, `Peca` | sem consumidor | removidos com os testes (D9) |
| `dominio/tabelas.HUBS`, `LINKS`, `SATELITES` | constantes só do teste | calculadas no teste de migração |
| `ingestao/processamento._processar` | `if/elif` por nome de etapa | `ETAPAS: tuple[Etapa, ...]` executada a partir de `primeira_etapa` (D11) |
| `ingestao/processamento._preparar`, `_entradas` | ifs por mime em três momentos e remapeamento de `entrada-1.pdf` | `FORMATOS: mime → Formato(inventariar, diagnosticar, persistir)`; os nomes vão para `diagnosticar_*` (D11) |
| `ingestao/processamento._processar_lotes` | lotes em série, dois caminhos de gravação, `copiar_do_cache` por lote | extração paralela (D4), um caminho de gravação, um `copiar_do_cache` antes do laço |
| `ingestao/processamento._extrair_lote` | retentativa com saída inalcançável | laço de `retentativas` mais uma chamada final |
| `ingestao/extracao.executar_em_paralelo`, `LimitadorGabinete`, `Paralelismo.lotes_por_gabinete` | sem chamador; semáforo por gabinete | chamado pelo worker; sai o gabinete (D4) |
| `config.extracao_lotes_por_gabinete` (`LUPA_EXTRACAO_LOTES_POR_GABINETE`) | `4` | removida (D4) |
| `config.extracao_lotes_por_job` (`LUPA_EXTRACAO_LOTES_POR_JOB`) | `4`, sem efeito | `2`; `1` volta à execução em série (D5) |
| `ingestao/paginas.py`, `dominio/gravacao.py` | 6 comandos por página | hubs e links por lote com `executemany`; um `SELECT DISTINCT ON` dos `hash_diff` correntes antes do laço (D6) |
| `ingestao/storage.ler` | `BytesIO` e cópia | `baixar_para(chave, caminho)` com `download_fileobj` |
| `ingestao/extrator_paginas.py`, `renderizacao.py` | `read_bytes()` e `fitz.open(stream)` | `fitz.open(caminho)` |
| `ingestao/repositorio.mudar_estado` | relê o arquivo depois de gravar | devolve o lido com os atributos novos |
| `ingestao/repositorio_pecas._serializar` | `session.get(VisaoEvidencia)` por peça | um `select ... where hk in (...)` em `indice_processo` |
| `ingestao/repositorio._atributos_correntes`, `repositorio_pecas._atributos` | dois helpers | `atributos(visao, satelite)` ao lado de `atributos_do_satelite` |
| fila: travar processo e checar `DESCARTADO` (`processamento.py`, `worker.py`, `reprocessamento.py`) | três cópias | `processo_ativo(session, hk) -> VisaoProcesso \| None` em `repositorio.py` |
| `validacoes/calendario.Calendario` | `feriados: Mapping[date, str]` e `fontes` paralelos | `feriados: Mapping[date, FeriadoCalendario]` com descrição e fonte (D7) |
| `validacoes/calendario.contar_prazo_corrido` | só usada em teste | removida com o teste (D7) |
| `validacoes/calendario.contar_prazo_util`, `fonte_em`, `_prorrogar` | laços copiados | gerador `_dias_seguintes`, usado por `contar_prazo_util` e por `dias_uteis_entre(inicio, fim)`; `_prorrogar` sai com `contar_prazo_corrido` (D7) |
| `validacoes/civel/tempestividade.py` | conta dias úteis e monta os descartados à mão | `calendario.dias_uteis_entre` |
| `validacoes/dados/dispensas.yaml` (arquivo) | `preparo.yaml` com `qualidade → rótulo` | renomeado; `qualidade → {rotulo, preparo, mandato}` com os mesmos valores, versão 0.3.0 (D8) |
| `validacoes/dados.TabelaPreparo`, `preparo_padrao()` | tabela do preparo, lida também por `eventos/partes.py` | `TabelaDispensas` e `dispensas_padrao()`; `partes.py` lê dela (D8) |
| `validacoes/apoio.Coleta.unico` | anota o conflito e cada regra checa `coleta.conflitos` | em fato opcional, levanta `FatoPendenteError`; o decorador `@regra` converte em `coleta.verificar()` (D8) |
| `validacoes/apoio.Coleta.pendente`, `Coleta.qualidade()` | `pendente` sem uso; qualidade lida em duas regras | sai `pendente`; entra `qualidade()` |
| `validacoes/apoio.PECAS` | dicionário central com `KeyError` para tipo novo | `PECA_PROCURADA` em cada módulo de `civel/`, consultada pela `Coleta` |
| `validacoes/modelo.ModeloProcesso.fato`, `recorrentes` | serializa a cada consulta e refaz o índice | resultado memorizado por instância |
| `validacoes/adaptador.para_modelo` | repassa para `ModeloProcesso` | removida; chamadores usam `ModeloProcesso` |
| `validacoes/versao.VERSAO_CATALOGO` | `0.2.0` | `0.3.0` (D8) |
| `sinteticos/gerador._ler_marcas` e as três montagens de `InjecaoGabarito` | aninhado, repetido | `_parte`, `_evento`, `_injecao` |
| `sinteticos/gabarito.ProcessoGabarito.diagnostico_esperado` | campo gravado e validado | `computed_field` derivado de `cenario` |
| `sinteticos/roteiro.py` (ifs por `ClasseProcessual`) | repete o catálogo | peças derivadas de `validacoes_de(classe)` e de `PECA_PROCURADA` |
| `sinteticos/identidades._MESES` | tabela própria | mantida (D2) |

### Arquivos

| Arquivo | Ação |
| --- | --- |
| `pipeline/src/lupa_pipeline/ingestao/texto.py` | criar |
| `pipeline/src/lupa_pipeline/ingestao/{datas,deteccao,hibridas,sinais_fronteira,data_peca,calibracao,processamento,extracao,paginas,storage,extrator_paginas,renderizacao,repositorio,repositorio_pecas,reprocessamento,worker,cache}.py` | alterar |
| `pipeline/src/lupa_pipeline/ingestao/eventos/{modelo,fatos,capa,base,recurso,preparo,decisao_agravada,partes,saida,etapa}.py` | alterar |
| `pipeline/src/lupa_pipeline/dominio/{esquemas,tabelas,gravacao}.py` | alterar |
| `pipeline/src/lupa_pipeline/validacoes/{calendario,dados,apoio,modelo,motor,adaptador,versao}.py`, `civel/*.py` | alterar |
| `pipeline/src/lupa_pipeline/validacoes/dados/preparo.yaml` | renomear para `dispensas.yaml` (D8) |
| `pipeline/src/lupa_pipeline/ingestao/reprocessamento.py` | chave `dispensas=` nas versões de fatos e catálogo (D8) |
| `pipeline/src/lupa_pipeline/sinteticos/{medicao,gerador,gabarito,roteiro,empacotamento}.py` | alterar |
| `pipeline/src/lupa_pipeline/config.py`, `.env.example` | `extracao_lotes_por_job=2`; sai `extracao_lotes_por_gabinete` |
| `intranet/api/src/lupa_api/agente/ferramentas/leitura.py`, `recusa.py`, `agente/dossie.py` | importam `texto.dobrar`; `dossie.py` lê `fato.valor` |
| `pipeline/tests/ingestao/test_texto.py` | criar |
| `pipeline/tests/**` correspondentes | ajustar imports; remover os testes do código removido (D9) |
| `docs/sistema/ingestao.md`, `docs/sistema/validacoes.md`, `docs/sistema/modelo-de-dados.md` | atualizar |
| `docs/arquitetura.md` | extração paralela no worker |
| `CHANGELOG.md` | `Não publicado`: paralelismo da extração e variável removida |
| `docs/decisoes/registro.md` | D4, D7, D8, D12, D13 |
| `docs/dividas/todo.md` | dívida do outorgante como sujeito da procuração (D13) |

### O que não muda

- Esquema do banco, views `v_*`, privilégios do `lupa_app` e a fila `v_fila_ingestao`.
- Advisory lock e processamento na mesma conexão física: as threads de extração só rodam os
  filhos sandbox; toda gravação fica na thread do worker.
- Isolamento do parsing (RF-ING-04): um processo filho por lote, sem rede.
- Texto dos achados, resultado de cada validação, base legal e templates de frase.
- Rotas da API, `lupa_web` e o contrato HTTP.
- `sinteticos/identidades._MESES` e os gabaritos sintéticos gravados.
- Sujeito e id dos fatos de procuração, e as correções e notas que apontam para eles (D13).

## Problemas

- **P1.** Duas regras de `dobrar`; a busca da API e a detecção podem discordar em caracteres raros.
- **P2.** `dobrar` roda de 2 a 4 vezes por página e normaliza caractere a caractere; `Fonte.datas`
  refaz a busca de datas a cada chamada.
- **P3.** `levenshtein` e três `normalizar` duplicados ou homônimos.
- **P4.** Lotes de extração em série com `executar_em_paralelo` pronto e sem chamador; semáforo por
  gabinete, conceito fora da 0.2.
- **P5.** Gravação de páginas com cerca de 6 comandos por página; consulta extra por peça no
  índice; PDF duas vezes na memória; PDF relido em cada filho.
- **P6.** Calendário com laços copiados, dicionários paralelos e contagem de dias úteis fora dele
  (tempestividade).
- **P7.** Dispensa de mandato lida da tabela de preparo; bloco de qualidade repetido; cada regra
  lembra de checar conflitos; `PECAS` central.
- **P8.** `Fato.valor` ambíguo e caso especial de procuração em dois lugares.
- **P9.** Despachos por `if` (espécie de peça, mime, nome de etapa) e remapeamento tardio de nomes.
- **P10.** Ids de fato e evidência montados à mão, em paralelo à definição do hub.
- **P11.** Código sem uso em produção e duplicações menores (`data_peca`, `sha256_arquivo`,
  `processo_ativo`, helpers de atributos, gerador sintético, `diagnostico_esperado`).

## Decisões

- **D1.** Fica a regra de `datas.py` (preserva o comprimento); `deteccao.py` e a API importam de
  `texto.py`.
- **D2.** Novo `ingestao/texto.py` com as funções de texto; a ingestão não importa de
  `sinteticos`. A tabela de meses do sintético fica separada, para o gabarito não depender do
  leitor.
- **D3.** `PaginaTexto` guarda `dobrado` e `datas` como `cached_property`.
- **D4.** Extração paralela com `ThreadPoolExecutor`, limite global; o semáforo por gabinete e
  `LUPA_EXTRACAO_LOTES_POR_GABINETE` saem.
- **D5.** O limite é a variável que já existe, `LUPA_EXTRACAO_LOTES_POR_JOB`, com padrão `2`; `1`
  volta à execução em série. O worker processa um job por vez, então o teto por job é o teto
  global. Substitui o nome `LUPA_EXTRACAO_PARALELA` levantado na pergunta, para não criar uma
  segunda variável com o mesmo papel.
- **D6.** Gravação em lote só dentro da transação que já existe; o `hash_diff` continua por linha.
- **D7.** `contar_prazo_corrido` sai com o teste; `feriados` e `fontes` viram um só
  `Mapping[date, FeriadoCalendario]`; o especialista-validacoes revisa.
- **D8.** `preparo.yaml` vira `dispensas.yaml`, tabela própria com os mesmos valores, lida pelas regras e por `eventos/partes.py`; as versões de fatos e catálogo do reprocessamento passam a citar `dispensas=`, e fatos e achados são regravados uma vez (decisão do usuário na T12.6); `Coleta.unico` interrompe a
  regra em conflito de fato opcional (decisão do usuário na T12.8; o obrigatório já cai em conferência coletando os demais); o especialista-validacoes revisa. A troca de arquivo de dados muda
  `versoes_dados` do achado, então `VERSAO_CATALOGO` sobe e o reprocessamento (RF-ING-08)
  regrava os achados com o mesmo resultado e texto.
- **D9.** Código sem uso sai junto com os testes dele, no mesmo commit, citando a tarefa.
- **D10.** A troca por `chave_do_hub` só entra com teste de igualdade dos ids atuais; se o teste
  mostrar id diferente, a fase sai do plano e vira dívida em `docs/dividas/todo.md`, sem parar
  (decisão do usuário, 21/11/2026).
- **D11.** Despachos viram registros declarativos: extratores por espécie, formatos por mime,
  etapas em lista ordenada.
- **D12.** `Fato.valor` passa a ser sempre o escalar. Sem migration: `Fato.de_registro` converte
  `{"valor": x}` em `x` ao ler da view; fatos novos já saem normalizados.
- **D13.** O fato de procuração não muda: o id do fato é `chave_hash([processo, tipo, sujeito,
  evidência])`, e gravar o outorgante como sujeito mudaria o id a que correções e notas do
  gabinete apontam. F11 só tira o caso especial repetido: `partes.nome_do_outorgante` traduz o
  outorgante para o nome e é usado por `eventos/saida.py` e `sinteticos/gerador.py`; um teste
  fixa que o id das procurações não muda. O outorgante como sujeito do fato vira dívida em
  `docs/dividas/todo.md` (decisão do usuário, 21/11/2026).
- **D14.** Um PR para o plano inteiro, da branch `refactor/limpeza-pipeline`, com um commit por
  fase. F1 a F7 já entraram na `develop` pelos PRs #20 a #26 e #27, antes desta regra; a branch
  parte da `develop` com F8.
- **D15.** Fases sem arquivo em comum e sem dependência rodam em paralelo, cada agente na própria
  worktree; o agente principal junta os commits na branch do plano e roda
  `bash scripts/verificar.sh` na stack inteira ao fim de cada grupo (decisão do usuário,
  21/11/2026).

## Fases

Campos de cada fase: requisito e P/D; revisores; arquivos (código em `pipeline/src/lupa_pipeline/`
e testes em `pipeline/tests/`, salvo indicação); depende de; paralela com; Vermelho; Verde;
Entregue. Implementa o `executor`, que chama o `tdd`; revisa sempre também o `revisor-codigo`.
Pronto quando, salvo indicação: rebuild, suítes da pipeline (`worker`) e da intranet (`api`)
verdes com 90% de cobertura, `ruff` e `mypy` limpos e, em fase que toca ingestão ou validação,
`bash scripts/verificar.sh` na stack inteira com saída 0. A evidência de F1 a F8 está em
`tarefas_0.2.md` (T12.1 a T12.8).

### F1 — `dobrar` único em `ingestao/texto.py`

- Requisito: RNF-08, RF-ING-03 · P1 · D1, D2.
- Entregue: PR #20.

### F2 — `levenshtein` e normalizações em `texto.py`

- Requisito: RNF-08 · P3 · D2.
- Entregue: PR #21.

### F3 — Texto da página guardado

- Requisito: RF-FAT-01 · P2 · D3.
- Entregue: PR #22.

### F4 — Contagem única do calendário

- Requisito: RF-VAL-02 · P6 · D7.
- Entregue: PR #23.

### F5 — Feriado com fonte e tempestividade pelo calendário

- Requisito: RF-VAL-02 · P6 · D7.
- Entregue: PR #24.

### F6 — Tabela de dispensas

- Requisito: RF-VAL-03, RF-VAL-04 · P7 · D8.
- Entregue: PR #25.

### F7 — Reprocessamento pela versão do catálogo

- Requisito: RF-ING-08 · D8.
- Entregue: PR #26.

### F8 — Conflito em fato opcional interrompe a regra

- Requisito: RF-FAT-02, RF-VAL-01 · P7 · D8.
- Revisores: especialista-validacoes (aprovado).
- Entregue: primeiro commit da branch do plano; `verificar.sh` com saída 0 (pipeline 713 passed,
  95,35%).

### F9 — Peça procurada por regra, modelo memorizado, fim de `para_modelo`

- Requisito: RF-VAL-01, RF-VAL-05 · P7.
- Revisores: especialista-validacoes.
- Arquivos: `validacoes/apoio.py`, `validacoes/civel/*.py`, `validacoes/modelo.py`,
  `validacoes/adaptador.py`, `validacoes/__main__.py`, `pipeline/scripts/medir_extracao.py`,
  `tests/validacoes/`.
- Depende de: F8. Paralela com: F14, F15.
- Vermelho: `tests/validacoes/test_motor_e_regras.py::test_tipo_de_fato_novo_usa_a_peca_procurada_da_regra`.
- Verde: `PECA_PROCURADA` em cada módulo de `civel/`, lida pela `Coleta`; sai `PECAS`;
  `ModeloProcesso.fato` e `recorrentes` memorizados; chamadores de `para_modelo` usam
  `ModeloProcesso`.
- Entregue:

### F10 — `Fato.valor` escalar com leitura do formato antigo

- Requisito: RF-FAT-01 · P8 · D12.
- Revisores: especialista-validacoes, especialista-intranet (`agente/dossie.py`).
- Arquivos: `dominio/esquemas.py`, `validacoes/modelo.py`, `validacoes/apoio.py`,
  `validacoes/civel/*.py`, `ingestao/calibracao.py`, `ingestao/eventos/saida.py`,
  `ingestao/eventos/fatos.py`, `intranet/api/src/lupa_api/agente/dossie.py`,
  `tests/dominio/test_esquemas.py`.
- Depende de: F9. Paralela com: F14, F15.
- Vermelho: `tests/dominio/test_esquemas.py::test_fato_le_valor_no_formato_antigo`.
- Verde: `Fato.de_registro` converte `{"valor": x}`; extratores gravam o escalar; sai `valor_de`.
- Entregue:

### F11 — Nome do outorgante num lugar só

- Requisito: RF-VAL-04 · P8 · D13.
- Revisores: especialista-validacoes, especialista-ingestao.
- Arquivos: `ingestao/eventos/partes.py`, `ingestao/eventos/saida.py`, `sinteticos/gerador.py`,
  `tests/ingestao/test_eventos.py`, `docs/dividas/todo.md`.
- Depende de: F10. Paralela com: F16.
- Vermelho: `tests/ingestao/test_eventos.py::test_nome_do_outorgante_resolve_o_codigo_da_parte`.
- Verde: `partes.nome_do_outorgante(valor, partes)`; `saida.py` e `gerador.py` passam a usá-la
  e saem os casos `PROCURACAO` deles. Guarda:
  `tests/ingestao/test_eventos.py::test_id_da_procuracao_nao_muda`, que fixa o id atual. Dívida
  do outorgante como sujeito registrada em `docs/dividas/todo.md`.
- Entregue:

### F12 — Ids de fato e evidência pelo hub

- Requisito: RF-FAT-01 · P10 · D10.
- Revisores: especialista-banco, especialista-ingestao.
- Arquivos: `ingestao/eventos/fatos.py`, `ingestao/eventos/modelo.py`,
  `tests/ingestao/test_eventos.py`.
- Depende de: F11. Paralela com: F16, F17.
- Vermelho: `tests/ingestao/test_eventos.py::test_ids_de_fato_e_evidencia_iguais_aos_atuais`.
- Verde: `chave_do_hub(hub_fato, ...)` e `chave_do_hub(hub_evidencia, ...)`. Se o teste falhar: a
  fase é revertida e vira dívida (D10).
- Entregue:

### F13 — Registro de extratores por espécie

- Requisito: RF-FAT-01 · P9 · D11.
- Revisores: especialista-ingestao.
- Arquivos: `ingestao/eventos/fatos.py`, `tests/ingestao/test_eventos.py`.
- Depende de: F12. Paralela com: F17, F18.
- Vermelho: `tests/ingestao/test_eventos.py::test_toda_especie_com_extrator_esta_no_registro`.
- Verde: `EXTRATORES: TipoPeca → extratores`, capa como extrator com filtro de página;
  `candidatos_da_peca` vira um laço.
- Entregue:

### F14 — Etapas em lista ordenada no worker

- Requisito: RF-ING-08 · P9 · D11.
- Revisores: especialista-ingestao.
- Arquivos: `ingestao/processamento.py`, `tests/ingestao/test_processamento.py`.
- Depende de: F8. Paralela com: F9, F10.
- Vermelho: `tests/ingestao/test_processamento.py::test_etapas_executam_a_partir_da_primeira_agendada`.
- Verde: `ETAPAS` executada a partir de `reprocessamento.primeira_etapa`; sai a cadeia `if/elif`.
- Entregue:

### F15 — Formatos por mime e nomes internos no diagnóstico

- Requisito: RF-ING-07 · P9 · D11.
- Revisores: especialista-ingestao.
- Arquivos: `ingestao/processamento.py`, `ingestao/diagnostico.py`,
  `tests/ingestao/test_processamento.py`, `tests/ingestao/test_diagnostico.py`.
- Depende de: F14. Paralela com: F9, F10.
- Vermelho: `tests/ingestao/test_processamento.py::test_diagnostico_de_zip_ja_sai_com_os_nomes_internos`.
- Verde: `FORMATOS: mime → Formato(inventariar, diagnosticar, persistir)`; `diagnosticar_*`
  recebe o mapa de nomes; `_preparar` dividida em `_fontes_do_manifesto` e `_fontes_do_original`.
- Entregue:

### F16 — Extração paralela sem gabinete

- Requisito: RF-ING-04, RF-ING-07 · P4 · D4, D5.
- Revisores: especialista-ingestao, especialista-infra (`.env.example`).
- Arquivos: `ingestao/processamento.py`, `ingestao/extracao.py`, `config.py`, `.env.example`,
  `tests/ingestao/test_processamento.py`, `tests/ingestao/test_extracao.py`.
- Depende de: F15. Paralela com: F11, F12.
- Vermelho: `tests/ingestao/test_processamento.py::test_lotes_em_paralelo_gravam_na_conexao_do_lock`
  e `::test_falha_de_gravacao_cancela_lotes_e_retoma_so_os_faltantes` (integração).
- Verde: `_processar_lotes` com `executar_em_paralelo` e `extracao_lotes_por_job` (padrão 2); um
  `copiar_do_cache` antes do laço; um caminho de gravação; retentativa simplificada; saem
  `LimitadorGabinete`, `lotes_por_gabinete` e `extracao_lotes_por_gabinete`.
- Entregue:

### F17 — Gravação de páginas em lote

- Requisito: RF-ING-03 · P5 · D6.
- Revisores: especialista-banco, especialista-ingestao.
- Arquivos: `ingestao/paginas.py`, `dominio/gravacao.py`, `ingestao/cache.py`,
  `tests/ingestao/test_paginas.py`, `tests/dominio/test_gravacao.py`.
- Depende de: F16. Paralela com: F12, F13.
- Vermelho: `tests/ingestao/test_paginas.py::test_gravacao_em_lote_igual_a_gravacao_por_pagina`
  (integração).
- Verde: hubs e links com `executemany`; `hash_diff` correntes lidos uma vez por lote.
- Entregue:

### F18 — MinIO para arquivo e PDF aberto pelo caminho

- Requisito: RF-ING-04 · P5.
- Revisores: especialista-ingestao.
- Arquivos: `ingestao/storage.py`, `ingestao/processamento.py`, `ingestao/extrator_paginas.py`,
  `ingestao/renderizacao.py`, `tests/ingestao/test_storage.py`.
- Depende de: F16. Paralela com: F13.
- Vermelho: `tests/ingestao/test_storage.py::test_baixar_para_grava_o_objeto_no_caminho`
  (integração).
- Verde: `storage.baixar_para` com `download_fileobj`; `fitz.open(caminho)`.
- Entregue:

### F19 — Leituras repetidas na fila e nos repositórios

- Requisito: RF-ING-07 · P5, P11.
- Revisores: especialista-ingestao, especialista-banco.
- Arquivos: `ingestao/repositorio.py`, `ingestao/repositorio_pecas.py`,
  `ingestao/processamento.py`, `ingestao/worker.py`, `ingestao/reprocessamento.py`,
  `ingestao/eventos/etapa.py`, `tests/ingestao/test_repositorio.py`.
- Depende de: F13, F18. Paralela com: nenhuma.
- Vermelho: `tests/ingestao/test_repositorio.py::test_processo_ativo_devolve_none_para_descartado`
  e `::test_indice_do_processo_le_evidencias_numa_consulta` (integração).
- Verde: `processo_ativo` nos três pontos da fila; `mudar_estado` sem releitura; uma consulta de
  evidências no índice; `atributos(visao, satelite)`; `processar_eventos` repassa o processo.
- Entregue:

### F20 — Remoção do código sem uso

- Requisito: RNF-08 · P11 · D9.
- Revisores: arquiteto.
- Arquivos: `ingestao/datas.py`, `dominio/esquemas.py`, `dominio/tabelas.py`,
  `tests/ingestao/test_datas.py`, `tests/dominio/test_esquemas.py`,
  `tests/ingestao/test_estados.py`, `tests/dominio/test_migracao_0001.py`.
- Depende de: F10. Paralela com: F14 a F18.
- Revisão manual: saem `TextoAnalise`, `encontrar_datas`, os esquemas `Anotacao`, `Usuario`,
  `JobIngestao`, `LoteIngestao` e `Peca`, e `HUBS`, `LINKS`, `SATELITES` (calculadas no teste),
  com os testes deles no mesmo commit; grep em `pipeline/` e `intranet/` sem referência.
- Entregue:

### F21 — Duplicações menores da ingestão

- Requisito: RNF-08, RF-ING-03 · P11.
- Revisores: especialista-ingestao.
- Arquivos: `ingestao/data_peca.py`, `ingestao/datas.py`, `dominio/esquemas.py`,
  `ingestao/calibracao.py`, `tests/ingestao/test_data_peca.py`, `tests/dominio/test_esquemas.py`.
- Depende de: F20. Paralela com: F14 a F18.
- Vermelho: `tests/ingestao/test_data_peca.py::test_regra_declara_a_direcao_da_busca` e
  `tests/dominio/test_esquemas.py::test_sha256_arquivo_igual_ao_da_recepcao`.
- Verde: `data_peca` com `datas.MESES`, `construir_data` e direção em `REGRAS`; `sha256_arquivo`
  em `dominio/esquemas.py`; `datas.UNIDADES` das tuplas de escrita.
- Entregue:

### F22 — Sintéticos sem repetição

- Requisito: RNF-04 · P11.
- Revisores: especialista-validacoes (roteiro e catálogo).
- Arquivos: `sinteticos/gabarito.py`, `sinteticos/gerador.py`, `sinteticos/roteiro.py`,
  `sinteticos/empacotamento.py`, `tests/sinteticos/test_gabarito.py`,
  `tests/sinteticos/test_roteiro.py`.
- Depende de: F9, F11. Paralela com: F14 a F19.
- Vermelho: `tests/sinteticos/test_gabarito.py::test_diagnostico_esperado_deriva_do_cenario` e
  `tests/sinteticos/test_roteiro.py::test_pecas_do_roteiro_seguem_o_catalogo_da_classe`.
- Verde: `diagnostico_esperado` como `computed_field`; `_ler_marcas` com `_parte`, `_evento` e
  `_injecao`; peças do roteiro derivadas de `validacoes_de(classe)` e `PECA_PROCURADA`.
- Entregue:

### F23 — Documentação

- Requisito: RNF-08.
- Implementa: documentador. Revisores: conferente-links.
- Arquivos: `docs/sistema/ingestao.md`, `docs/sistema/validacoes.md`,
  `docs/sistema/modelo-de-dados.md`, `docs/arquitetura.md`, `CHANGELOG.md`,
  `docs/decisoes/registro.md`.
- Depende de: todas. Paralela com: nenhuma.
- Revisão manual: extração paralela e variável removida no `CHANGELOG.md`; D4, D7, D8, D12 e
  D13 no registro.
- Pronto quando: `bash scripts/verificar.sh` na stack inteira com saída 0 e links conferidos.
- Entregue:

## Distribuição

| Fase | Agente | Revisores | Depende de | Paralela com |
| --- | --- | --- | --- | --- |
| F9 | executor | especialista-validacoes | F8 | F14, F15 |
| F10 | executor | especialista-validacoes, especialista-intranet | F9 | F14, F15 |
| F11 | executor | especialista-validacoes, especialista-ingestao | F10 | F16 |
| F12 | executor | especialista-banco, especialista-ingestao | F11 | F16, F17 |
| F13 | executor | especialista-ingestao | F12 | F17, F18 |
| F14 | executor | especialista-ingestao | F8 | F9, F10 |
| F15 | executor | especialista-ingestao | F14 | F9, F10 |
| F16 | executor | especialista-ingestao, especialista-infra | F15 | F11, F12 |
| F17 | executor | especialista-banco, especialista-ingestao | F16 | F12, F13 |
| F18 | executor | especialista-ingestao | F16 | F13 |
| F19 | executor | especialista-ingestao, especialista-banco | F13, F18 | — |
| F20 | executor | arquiteto | F10 | F14 a F18 |
| F21 | executor | especialista-ingestao | F20 | F14 a F18 |
| F22 | executor | especialista-validacoes | F9, F11 | F14 a F19 |
| F23 | documentador | conferente-links | todas | — |

Grupos, cada um fechado por `verificar.sh` na stack inteira antes do seguinte:

1. F9 e F14 em paralelo; depois F10 e F15.
2. F11 e F16 em paralelo; depois F12 com F17, e F20.
3. F13 com F18 e F21; depois F19 com F22.
4. F23.

## Passo a passo do algoritmo

### Extração paralela dos lotes (F16)

1. Entrada: arquivo travado, conexão do lock, `prontas` (páginas já gravadas). Ação: calcular as páginas faltantes. Saída: `faltantes`.
2. Entrada: `faltantes`. Ação: uma chamada a `copiar_do_cache` numa transação. Saída: páginas copiadas e `restantes`.
3. Se `restantes` está vazio: gravar o estado dos lotes e ir ao passo 9.
4. Entrada: `restantes`, `extracao_paginas_por_lote`. Ação: `planejar`. Saída: tarefas.
5. Entrada: tarefas, `extracao_lotes_por_job`. Ação: `executar_em_paralelo` roda até N filhos sandbox em threads. Saída: resultados à medida que terminam.
6. Para cada resultado, na thread do worker e na conexão do lock: gravar páginas em lote (hubs e links com `executemany`, `hash_diff` correntes lidos uma vez por lote) e o satélite do lote. Saída: lote gravado.
7. Resultado com motivo retentável: até `max_retentativas` novas execuções do lote; depois, o lote fica falho com o motivo.
8. Erro de gravação: a transação do lote é desfeita, as threads pendentes são canceladas e o erro sobe; a retomada (RF-ING-07) refaz só os lotes sem satélite.
9. Saída: relatório da etapa `paginas`.

### Texto da página guardado (F3)

1. Entrada: `PaginaTexto.normalizado`. Ação: primeiro acesso a `dobrado` chama `texto.dobrar`. Saída: texto dobrado com o mesmo comprimento.
2. Entrada: `dobrado`. Ação: primeiro acesso a `datas` chama `datas_no_dobrado`. Saída: datas com offsets.
3. Extratores (`recurso`, `marcos`, `preparo`, `capa`, `decisao_agravada`, `Fonte.datas`) leem `pagina.dobrado` e `pagina.datas`; `capa._valor` recorta `dobrado[inicio:fim]`.
4. Saída: os mesmos candidatos de fato, conferidos pelo teste de igualdade sobre os sintéticos.

### Contagem de prazo (F4 e F5)

1. Entrada: data base, dias, calendário. Ação: `contar_prazo_util` percorre `_dias_seguintes`, um dia por vez, pulando os dias com `motivo_sem_expediente`. Saída: vencimento e dias pulados.
2. Prazo de zero dias: vencimento na própria data base, sem dias pulados. O vencimento sempre cai num dia útil, porque a contagem só termina num dia contado.
3. Entrada: início e fim. Ação: `dias_uteis_entre` percorre o mesmo gerador de `inicio + 1` até `fim`. Fim igual ou anterior ao início: `(0, ())`. Saída: contagem e dias pulados.
4. Tempestividade: atraso igual a `dias_uteis_entre(termo, protocolo)`; texto do achado igual ao atual.

### Regra com conflito (F8)

1. Entrada: `ModeloProcesso`, regra decorada com `@regra`. Ação: a regra chama `coleta.unico(tipo)`.
2. Fato obrigatório com dois valores: `unico` registra o conflito e devolve `None`; a regra segue coletando os demais e devolve `coleta.verificar()` com todas as faltas e divergências.
3. Fato opcional (`obrigatorio=False`) com dois valores: `unico` registra o conflito e levanta `FatoPendenteError(coleta)`.
4. `@regra` captura `FatoPendenteError` e devolve `coleta.verificar()`. Saída: achado "verificar" com os conflitos, igual ao atual.
5. Sem conflito: a regra segue e devolve o achado. Outras exceções sobem como hoje.

### Leitura do fato (F10)

1. Entrada: linha de `v_fato`. Ação: `Fato.de_registro`. Saída: `Fato`.
2. Valor `dict` com só a chave `valor`: substituir pelo escalar.
3. Fato novo: o extrator grava o escalar.
4. Consumidores (validações, saída, gerador, `agente/dossie.py`) leem `fato.valor`.

### Nome do outorgante (F11)

1. Entrada: valor do fato de procuração e o mapa `chave_nome → hk da parte`. Ação:
   `nome_do_outorgante`. Saída: o nome da parte.
2. Outorgante já é um nome (substabelecimento, com `nome` e `oab`): devolver o nome sem consulta.
3. Código sem parte correspondente no mapa: devolver o código, como hoje.
4. `saida.eventos_saida` e `gerador` chamam a função; o fato gravado, o sujeito e o id não mudam.

### Etapas em lista ordenada (F14)

1. Entrada: arquivo travado e `versoes_atuais()`. Ação: `primeira_etapa(arquivo, versoes)`.
   Saída: nome da primeira etapa a refazer, ou `None`.
2. `None` com arquivo novo: começar em `paginas`. `None` com arquivo já processado: encerrar sem
   refazer nada.
3. Entrada: nome da etapa. Ação: localizar sua posição em `ETAPAS` (`paginas`, `pecas`, `fatos`,
   `catalogo`). Saída: as etapas dali até o fim, na ordem.
4. Para cada etapa: executar a função dela na conexão do lock. Saída: a parte do relatório da
   etapa.
5. Etapa `catalogo`: juntar a parte dela ao relatório existente em vez de substituí-lo, como hoje.
6. Erro numa etapa: o erro sobe, as etapas seguintes não rodam e a retomada (RF-ING-07) recomeça
   pela primeira etapa sem versão gravada.
7. Saída: relatório com `versoes_processamento` iguais a `versoes_atuais()`.

### Formatos por tipo de arquivo (F15)

1. Entrada: arquivo lacrado (`mime`). Ação: `FORMATOS[mime]`. Saída: o `Formato` do arquivo.
2. Mime sem formato: recusar como hoje (RF-ING-02), sem tocar o storage.
3. Entrada: caminho baixado. Ação: `formato.inventariar`. Saída: entradas (um PDF é uma entrada).
4. Entrada: entradas e o mapa de nomes internos (`entrada-<n>.pdf`). Ação: `formato.diagnosticar`.
   Saída: diagnóstico com fronteiras de origem e metadados descartados já com os nomes internos.
5. Entrada: entradas. Ação: `formato.persistir` no storage, numa transação. Saída: fontes de
   páginas (`FontePaginas`).
6. Retomada com manifesto: `_fontes_do_manifesto` devolve as fontes e o diagnóstico gravados, sem
   os passos 3 a 5.
7. Nome interno sem entrada correspondente: erro de integridade, em vez do padrão `entrada-1.pdf`.

### Gravação de páginas em lote (F17)

1. Entrada: páginas extraídas de um lote. Ação: montar as chaves de hub e de link de cada uma.
   Saída: listas de hubs e links.
2. Ação: `INSERT ... ON CONFLICT DO NOTHING` dos hubs e dos links com `executemany`. Saída: hubs e
   links gravados.
3. Ação: um `SELECT DISTINCT ON (pai)` dos `hash_diff` correntes dos satélites das páginas do
   lote. Saída: mapa `pai → hash_diff`.
4. Para cada satélite de cada página: calcular o `hash_diff`; igual ao corrente, não gravar;
   diferente, incluir na lista de linhas novas.
5. Ação: inserir as linhas novas de satélite com `executemany`. Saída: lote gravado.
6. Erro: a transação do lote é desfeita inteira; nada do lote fica gravado e a retomada refaz o
   lote.

### Processo ativo na fila (F19)

1. Entrada: sessão e `hk_processo`. Ação: `SELECT ... FOR UPDATE` do processo em `v_processo`.
   Saída: `VisaoProcesso` travado.
2. Processo descartado: devolver `None`.
3. `Trabalho.transacao`: `None` levanta o erro de processo descartado, como hoje.
4. Worker: `None` marca o item da fila como encerrado, como hoje.
5. Reprocessamento: `None` pula o arquivo, como hoje.

## Execução

1. Merge do PR único da branch `refactor/limpeza-pipeline` na `develop`, com F23 concluída.
2. `docker compose up -d --build --wait`.
3. Sem migration; o reprocessamento dos achados pela versão nova do catálogo (D8) roda pelo worker, sem passo manual.
