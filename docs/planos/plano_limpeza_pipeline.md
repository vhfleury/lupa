# Plano — limpeza da pipeline

20 de novembro de 2026 · Estado: **aprovado** · Atende a
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
| `eventos/saida.py`, `sinteticos/gerador.py` (caso `PROCURACAO`) | troca o outorgante pelo nome em cada um | o fato de procuração traz o outorgante como sujeito, resolvido em `eventos/partes.py` (D12) |
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
| `validacoes/calendario.Calendario` | `feriados: Mapping[date, str]` e `fontes` paralelos | `feriados: Mapping[date, Feriado]` com descrição e fonte (D7) |
| `validacoes/calendario.contar_prazo_corrido` | só usada em teste | removida com o teste (D7) |
| `validacoes/calendario.contar_prazo_util`, `fonte_em`, `_prorrogar` | laços copiados | `_contar(base, dias, sem_contagem)` e `dias_uteis_entre(inicio, fim)` (D7) |
| `validacoes/civel/tempestividade.py` | conta dias úteis e monta os descartados à mão | `calendario.dias_uteis_entre` |
| `validacoes/dados/dispensas.yaml` (arquivo) | `preparo.yaml` com `qualidade → rótulo` | renomeado; `qualidade → {rotulo, preparo, mandato}` com os mesmos valores, versão 0.3.0 (D8) |
| `validacoes/dados.TabelaPreparo`, `preparo_padrao()` | tabela do preparo, lida também por `eventos/partes.py` | `TabelaDispensas` e `dispensas_padrao()`; `partes.py` lê dela (D8) |
| `validacoes/apoio.Coleta.unico` | anota o conflito e cada regra checa `coleta.conflitos` | em fato opcional, levanta `FatoPendenteError`; o decorador `@regra` converte em `coleta.verificar()` (D8) |
| `validacoes/apoio.Coleta.pendente`, `Coleta.qualidade()` | `pendente` sem uso; qualidade lida em duas regras | sai `pendente`; entra `qualidade()` |
| `validacoes/apoio.PECAS` | dicionário central com `KeyError` para tipo novo | `peca_procurada` em cada regra, consultada pela `Coleta` |
| `validacoes/modelo.ModeloProcesso.fato`, `recorrentes` | serializa a cada consulta e refaz o índice | resultado memorizado por instância |
| `validacoes/adaptador.para_modelo` | repassa para `ModeloProcesso` | removida; chamadores usam `ModeloProcesso` |
| `validacoes/versao.VERSAO_CATALOGO` | versão atual | sobe uma versão menor (D8) |
| `sinteticos/gerador._ler_marcas` e as três montagens de `InjecaoGabarito` | aninhado, repetido | `_parte`, `_evento`, `_injecao` |
| `sinteticos/gabarito.ProcessoGabarito.diagnostico_esperado` | campo gravado e validado | `computed_field` derivado de `cenario` |
| `sinteticos/roteiro.py` (ifs por `ClasseProcessual`) | repete o catálogo | peças derivadas de `validacoes_de(classe)` e de `peca_procurada` |
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
| `docs/decisoes/registro.md` | D4, D7, D8, D12 |

### O que não muda

- Esquema do banco, views `v_*`, privilégios do `lupa_app` e a fila `v_fila_ingestao`.
- Advisory lock e processamento na mesma conexão física: as threads de extração só rodam os
  filhos sandbox; toda gravação fica na thread do worker.
- Isolamento do parsing (RF-ING-04): um processo filho por lote, sem rede.
- Texto dos achados, resultado de cada validação, base legal e templates de frase.
- Rotas da API, `lupa_web` e o contrato HTTP.
- `sinteticos/identidades._MESES` e os gabaritos sintéticos gravados.

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
  `Mapping[date, Feriado]`; o especialista-validacoes revisa.
- **D8.** `preparo.yaml` vira `dispensas.yaml`, tabela própria com os mesmos valores, lida pelas regras e por `eventos/partes.py`; as versões de fatos e catálogo do reprocessamento passam a citar `dispensas=`, e fatos e achados são regravados uma vez (decisão do usuário na T12.6); `Coleta.unico` interrompe a
  regra em conflito de fato opcional (decisão do usuário na T12.8; o obrigatório já cai em conferência coletando os demais); o especialista-validacoes revisa. A troca de arquivo de dados muda
  `versoes_dados` do achado, então `VERSAO_CATALOGO` sobe e o reprocessamento (RF-ING-08)
  regrava os achados com o mesmo resultado e texto.
- **D9.** Código sem uso sai junto com os testes dele, no mesmo commit, citando a tarefa.
- **D10.** A troca por `chave_do_hub` só entra com teste de igualdade dos ids atuais; divergência
  para a fase e volta ao usuário.
- **D11.** Despachos viram registros declarativos: extratores por espécie, formatos por mime,
  etapas em lista ordenada.
- **D12.** `Fato.valor` passa a ser sempre o escalar. Sem migration: `Fato.de_registro` converte
  `{"valor": x}` em `x` ao ler da view; fatos novos já saem normalizados. O outorgante da
  procuração vira o sujeito do fato, resolvido em `eventos/partes.py` e usado por extração,
  saída e gerador.

## Fases

1. Texto: `ingestao/texto.py`, `dobrar` único, `levenshtein`, normalizações. P1, P3; D1, D2. RNF-08, RF-ING-03.
2. Texto da página guardado: `PaginaTexto.dobrado` e `datas`, extratores e `capa` sobre o recorte. P2; D3. RF-FAT-01.
3. Calendário e tempestividade. P6; D7. RF-VAL-01, RF-VAL-02.
4. Validações: dispensas, conflito por exceção, `qualidade()`, `peca_procurada`, memorização do modelo, `para_modelo`. P7; D8. RF-VAL-01, RF-VAL-03, RF-VAL-04, RF-VAL-05, RF-FAT-02.
5. Contrato do fato: `Fato.valor` escalar, leitura do formato antigo, outorgante como sujeito, fim de `valor_de`. P8; D12. RF-FAT-01, RF-VAL-04.
6. Ids pelo hub, com teste de igualdade. P10; D10. RF-FAT-01.
7. Despachos declarativos na extração e no worker. P9; D11. RF-FAT-01, RF-ING-07, RF-ING-08.
8. Desempenho do worker: extração paralela, gravação em lote, MinIO para arquivo, `fitz.open(caminho)`, `processo_ativo`, `mudar_estado`, índice de peças. P4, P5; D4, D5, D6. RF-ING-03, RF-ING-04, RF-ING-07.
9. Código sem uso e duplicações menores, inclusive sintéticos. P11; D9. RNF-08.
10. Documentação: `docs/sistema/`, `docs/arquitetura.md`, `CHANGELOG.md`, `docs/decisoes/registro.md`. RNF-08.

## Passo a passo do algoritmo

### Extração paralela dos lotes (fase 8)

1. Entrada: arquivo travado, conexão do lock, `prontas` (páginas já gravadas). Ação: calcular as páginas faltantes. Saída: `faltantes`.
2. Entrada: `faltantes`. Ação: uma chamada a `copiar_do_cache` numa transação. Saída: páginas copiadas e `restantes`.
3. Se `restantes` está vazio: gravar o estado dos lotes e ir ao passo 9.
4. Entrada: `restantes`, `extracao_paginas_por_lote`. Ação: `planejar`. Saída: tarefas.
5. Entrada: tarefas, `extracao_lotes_por_job`. Ação: `executar_em_paralelo` roda até N filhos sandbox em threads. Saída: resultados à medida que terminam.
6. Para cada resultado, na thread do worker e na conexão do lock: gravar páginas em lote (hubs e links com `executemany`, `hash_diff` correntes lidos uma vez por lote) e o satélite do lote. Saída: lote gravado.
7. Resultado com motivo retentável: até `max_retentativas` novas execuções do lote; depois, o lote fica falho com o motivo.
8. Erro de gravação: a transação do lote é desfeita, as threads pendentes são canceladas e o erro sobe; a retomada (RF-ING-07) refaz só os lotes sem satélite.
9. Saída: relatório da etapa `paginas`.

### Texto da página guardado (fase 2)

1. Entrada: `PaginaTexto.normalizado`. Ação: primeiro acesso a `dobrado` chama `texto.dobrar`. Saída: texto dobrado com o mesmo comprimento.
2. Entrada: `dobrado`. Ação: primeiro acesso a `datas` chama `datas_no_dobrado`. Saída: datas com offsets.
3. Extratores (`recurso`, `marcos`, `preparo`, `capa`, `decisao_agravada`, `Fonte.datas`) leem `pagina.dobrado` e `pagina.datas`; `capa._valor` recorta `dobrado[inicio:fim]`.
4. Saída: os mesmos candidatos de fato, conferidos pelo teste de igualdade sobre os sintéticos.

### Contagem de prazo (fase 3)

1. Entrada: data base, dias, calendário. Ação: `_contar` avança um dia por vez, pulando os dias com `motivo_sem_expediente`. Saída: termo final e dias descartados com descrição e fonte.
2. Termo final sem expediente: prorrogar ao próximo dia útil (`_prorrogar`) e registrar os dias pulados.
3. Entrada: início e fim. Ação: `dias_uteis_entre` usa o mesmo laço. Saída: contagem e descartados.
4. Tempestividade: atraso igual a `dias_uteis_entre(termo, protocolo)`; texto do achado igual ao atual.

### Regra com conflito (fase 4)

1. Entrada: `ModeloProcesso`, regra decorada com `@regra`. Ação: a regra chama `coleta.unico(tipo)`.
2. Fato obrigatório com dois valores: `unico` registra o conflito e devolve `None`; a regra segue coletando os demais e devolve `coleta.verificar()` com todas as faltas e divergências.
3. Fato opcional (`obrigatorio=False`) com dois valores: `unico` registra o conflito e levanta `FatoPendenteError(coleta)`.
4. `@regra` captura `FatoPendenteError` e devolve `coleta.verificar()`. Saída: achado "verificar" com os conflitos, igual ao atual.
5. Sem conflito: a regra segue e devolve o achado. Outras exceções sobem como hoje.

### Leitura do fato (fase 5)

1. Entrada: linha de `v_fato`. Ação: `Fato.de_registro`. Saída: `Fato`.
2. Valor `dict` com só a chave `valor`: substituir pelo escalar.
3. Fato novo: o extrator grava o escalar; procuração grava o outorgante como sujeito.
4. Consumidores (validações, saída, gerador, `agente/dossie.py`) leem `fato.valor`.

## Checklist de testes

- RNF-08: `pipeline/tests/ingestao/test_texto.py::test_dobrar_preserva_o_comprimento_com_caractere_que_muda_de_tamanho` — regra única de D1.
- RNF-08: `pipeline/tests/ingestao/test_texto.py::test_levenshtein_com_prefixo_e_sufixo_comuns` — mesma distância da versão atual.
- RF-FAT-01: `pipeline/tests/ingestao/eventos/test_fatos.py::test_candidatos_iguais_com_texto_da_pagina_guardado` — candidatos idênticos aos atuais nos sintéticos.
- RF-VAL-02: `pipeline/tests/validacoes/test_calendario.py::test_dias_uteis_entre_registra_feriado_com_fonte` — contagem e descartados.
- RF-VAL-02: `pipeline/tests/validacoes/test_motor_e_regras.py::test_tempestividade_com_atraso_mantem_o_texto` — texto do achado igual.
- RF-VAL-03, RF-VAL-04: `pipeline/tests/validacoes/test_motor_e_regras.py::test_dispensa_por_qualidade_le_a_tabela_de_dispensas` — mesmo resultado.
- RF-FAT-02: `pipeline/tests/validacoes/test_motor_e_regras.py::test_conflito_interrompe_a_regra_e_vira_verificar` — achado com os conflitos.
- RF-FAT-01: `pipeline/tests/dominio/test_esquemas.py::test_fato_le_valor_no_formato_antigo` — `{"valor": x}` vira `x`.
- RF-VAL-04: `pipeline/tests/ingestao/eventos/test_partes.py::test_procuracao_traz_o_outorgante_como_sujeito`.
- RF-FAT-01: `pipeline/tests/ingestao/eventos/test_modelo.py::test_ids_de_fato_e_evidencia_iguais_aos_atuais` — D10.
- RF-ING-07: `pipeline/tests/ingestao/test_processamento.py::test_lotes_em_paralelo_gravam_na_conexao_do_lock` (integração).
- RF-ING-07: `pipeline/tests/ingestao/test_processamento.py::test_falha_de_gravacao_cancela_lotes_e_retoma_so_os_faltantes` (integração).
- RF-ING-03: `pipeline/tests/ingestao/test_paginas.py::test_gravacao_em_lote_igual_a_gravacao_por_pagina` (integração).
- RF-ING-08: `pipeline/tests/ingestao/test_reprocessamento.py::test_nova_versao_do_catalogo_regrava_achados_com_o_mesmo_texto` (integração).
- RNF-08: `pipeline/tests/ingestao/test_texto.py::test_colapsar_espacos_aplica_nfc` e `::test_maiusculas_sem_acento_remove_pontuacao`.
- RF-VAL-01, RF-VAL-05: `pipeline/tests/validacoes/test_motor_e_regras.py::test_tipo_de_fato_novo_usa_a_peca_procurada_da_regra`.
- RF-FAT-01: `pipeline/tests/ingestao/eventos/test_fatos.py::test_toda_especie_com_extrator_esta_no_registro`.
- RF-ING-08: `pipeline/tests/ingestao/test_processamento.py::test_etapas_executam_a_partir_da_primeira_agendada`.
- RF-ING-07: `pipeline/tests/ingestao/test_processamento.py::test_diagnostico_de_zip_ja_sai_com_os_nomes_internos`.
- RF-ING-04: `pipeline/tests/ingestao/test_storage.py::test_baixar_para_grava_o_objeto_no_caminho` (integração).
- RF-ING-07: `pipeline/tests/ingestao/test_repositorio.py::test_processo_ativo_devolve_none_para_descartado` e `test_repositorio_pecas.py::test_indice_do_processo_le_evidencias_numa_consulta` (integração).
- RF-ING-03: `pipeline/tests/ingestao/test_data_peca.py::test_regra_declara_a_direcao_da_busca` e `pipeline/tests/dominio/test_esquemas.py::test_sha256_arquivo_igual_ao_da_recepcao`.
- RNF-04: `pipeline/tests/sinteticos/test_gabarito.py::test_diagnostico_esperado_deriva_do_cenario` e `test_roteiro.py::test_pecas_do_roteiro_seguem_o_catalogo_da_classe`.
- RNF-04: suíte de regressão com os sintéticos de cada classe, corpus de injeção e `bash scripts/verificar.sh`.

## Execução

1. Commit e PR por fase, da branch `refactor/T12.<n>-<fase>` para a `develop`.
2. `docker compose up -d --build --wait`.
3. Sem migration; o reprocessamento dos achados pela versão nova do catálogo (D8) roda pelo worker, sem passo manual.
