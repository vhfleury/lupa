# Plano da versão 0.2 — execução

Complementa o [plano da 0.2](plano_0.2.md): passo a passo dos algoritmos e checklist de testes.
A lista de arquivos está na seção "O que muda" do plano. Cada passo informa entrada, ação e
saída.

## Passo a passo do algoritmo

### A1. Chave por hash (`dominio/chaves.py`)

1. Entrada: partes da chave de negócio, na ordem do hub. Ação: converter cada parte em texto,
   aparar espaços e normalizar em NFC; número CNJ só com dígitos; hashes em minúsculas. Saída:
   lista de textos.
2. Entrada: lista de textos. Ação: recusar parte vazia ou que contenha `|`, salvo `sujeito`, que
   pode ser vazio. Saída: lista válida ou `ChaveInvalidaError`.
3. Entrada: lista válida. Ação: unir por `|` e calcular SHA-256. Saída: 32 bytes (`hk`).
4. Entrada: `hk` de cada hub de um link, na ordem das colunas. Ação: unir os hex por `|` e
   calcular SHA-256. Saída: `hk` do link.
5. Entrada: atributos de um satélite. Ação: serializar em JSON canônico (chaves ordenadas, sem
   espaços) e calcular SHA-256; se o satélite tem coluna cifrada, HMAC-SHA-256 com a DEK do
   processo. Saída: `hash_diff`.

### A2. Gravação (`dominio/gravacao.py`)

1. Entrada: hub, chave de negócio, `record_source`. Ação: calcular `hk` (A1) e inserir com `ON
   CONFLICT (hk) DO NOTHING`. Saída: `hk`.
2. Entrada: link, `hk` dos hubs. Ação: calcular `hk` do link e inserir com `ON CONFLICT DO
   NOTHING`. Saída: `hk` do link.
3. Entrada: satélite, `hk` do pai, atributos. Ação: calcular `hash_diff` (A1) e ler o
   `hash_diff` da linha mais recente do pai. Saída: os dois valores.
4. Desvio: `hash_diff` igual ao corrente. Ação: não inserir. Saída: `False`.
5. Entrada: `hash_diff` diferente ou pai sem linha. Ação: inserir linha nova. Saída: `True`.
6. Satélite multiativo: os passos 3 a 5 comparam com a linha mais recente da mesma subchave
   (`numero` ou `sequencia`); anotação e falha de login sempre inserem.
7. Erro: violação de FK ou de `CHECK`. Ação: propagar; a transação do chamador desfaz. Saída:
   exceção.

### A3. Recepção de arquivo (`ingestao/recepcao.py`, rota `POST /processos/{id}/arquivos`)

1. Entrada: `id` do processo e corpo. Ação: ler `v_processo`. Saída: processo ou 404.
2. Desvio: processo `descartado`. Saída: 409.
3. Entrada: corpo. Ação: gravar em arquivo temporário calculando SHA-256 e tamanho; recusar acima
   do limite. Saída: `sha256`, `tamanho_bytes` ou 413.
4. Entrada: `numero_cnj`, `sha256`. Ação: procurar em `v_arquivo`. Saída: arquivo existente ou
   nada.
5. Desvio: arquivo existente. Saída: 200 com `duplicado: true`; fim.
6. Entrada: arquivo temporário e DEK do processo. Ação: cifrar e gravar o objeto em
   `processo/<hk>/<sha256>`. Saída: `chave_storage`.
7. Entrada: dados do arquivo. Ação: na mesma transação, gravar `hub_arquivo`,
   `link_processo_arquivo`, `sat_arquivo_dados` e `sat_arquivo_ingestao` com estado `recebido`
   (A2), e o evento `upload` (A15). Saída: 201 com o `id` do arquivo.
8. Erro: falha depois do passo 6. Ação: desfazer a transação; o objeto órfão é sobrescrito no
   próximo envio do mesmo arquivo. Saída: 500.

### A4. Laço do worker (`ingestao/worker.py`)

1. Entrada: conexão. Ação: `pg_try_advisory_lock(<constante>)`. Saída: obtido ou não.
2. Parada: lock não obtido. Ação: registrar `worker_duplicado` e encerrar com código 1.
3. Entrada: `v_fila_ingestao`. Ação: ler o primeiro arquivo. Saída: arquivo ou nada.
4. Desvio: fila vazia. Ação: esperar `LUPA_FILA_INTERVALO_S` e voltar ao passo 3.
5. Entrada: arquivo. Ação: ler `tentativas` do estado corrente. Saída: número.
6. Desvio: `tentativas >= LUPA_MAX_TENTATIVAS`. Ação: gravar estado `falho` com `erro_interno`;
   voltar ao passo 3.
7. Entrada: arquivo. Ação: gravar o estado corrente com `tentativas + 1` e executar A5. Saída:
   estado final do arquivo.
8. Erro: exceção não tratada em A5. Ação: registrar em log sem conteúdo e voltar ao passo 3; o
   arquivo continua na fila com a tentativa já contada.
9. Parada: sinal `SIGTERM`. Ação: terminar o lote em curso, liberar o lock e encerrar com 0.

### A5. Ingestão de um arquivo

1. Entrada: arquivo em `recebido`. Ação: validar tipo, assinatura, senha, truncamento e ZIP no
   sandbox. Saída: `validado` com manifesto, ou `quarentena` com motivo (fim).
2. Entrada: arquivo `validado`. Ação: diagnosticar no sandbox e gravar `sat_arquivo_diagnostico`.
   Saída: cenário e total de páginas.
3. Entrada: total de páginas. Ação: gravar estado `em_extracao`; listar as páginas sem linha em
   `sat_pagina_extracao` na versão corrente do extrator. Saída: páginas pendentes.
4. Entrada: páginas pendentes, em lotes de 8. Ação: extrair no sandbox; por página, gravar
   `hub_pagina`, `link_arquivo_pagina`, `sat_pagina_extracao` e `sat_pagina_saneamento`; por
   lote, `sat_arquivo_lote`. Saída: lotes `concluido` ou `falho`.
5. Erro: `tempo_esgotado` ou `erro_parser` num lote. Ação: repetir o lote até
   `LUPA_MAX_RETENTATIVAS`; depois, marcar o lote `falho` e seguir.
6. Erro: `limite_memoria` ou `limite_cpu`. Ação: gravar estado `falho` com o motivo. Saída: fim.
7. Entrada: páginas gravadas. Ação: calcular sinais de fronteira (`sat_pagina_fronteira`), separar
   e classificar peças, gravar `hub_peca`, `link_arquivo_peca` e `sat_peca_classificacao`. Peça
   com linha `metodo = manual` não recebe linha nova. Saída: peças vigentes.
8. Entrada: páginas e peças vigentes. Ação: extrair partes e fatos (A6). Saída: fatos gravados.
9. Entrada: fatos vigentes e classe do processo. Ação: rodar o catálogo (A7 a A10); para cada
   resultado, gravar `hub_achado`, `link_processo_achado`, `link_achado_fato` e
   `sat_achado_resultado` (A2 só insere se o resultado mudou). Saída: achados.
10. Entrada: lotes. Ação: gravar o estado final: `concluido` se todos os lotes concluíram,
    `parcial` com a lista de páginas faltantes no relatório caso contrário. Saída: estado final.
11. Entrada: estados dos arquivos do processo. Ação: gravar `sat_processo_estado`
    (`em_ingestao` ou `pronto`). Saída: status do processo.
12. Retomada: A5 chamado para arquivo em `validado` ou `em_extracao` recomeça do passo 2 ou 3; os
    passos 3 e 4 pulam o que já está gravado.

### A6. Extração de partes e fatos (`ingestao/eventos/`)

1. Entrada: peças vigentes do tipo petição inicial, sentença, acórdão e recursos. Ação: aplicar
   os padrões de qualificação de parte. Saída: candidatos (nome, polo, trecho, página).
2. Entrada: candidatos. Ação: normalizar o nome, calcular `chave_nome` (A1, HMAC), classificar a
   qualidade pela lista de `preparo.yaml` (Fazenda, Ministério Público, Defensoria; senão
   particular); gravar evidência, `hub_parte`, `link_processo_parte` e `sat_parte_identidade`.
   Saída: partes.
3. Entrada: cada peça vigente. Ação: escolher o extrator pelo tipo da peça (`certidao`,
   `recurso`, `sentenca`, `preparo`, `procuracao`, `decisao_agravada`, `marcos`). Saída:
   candidatos a fato com trecho e posição.
4. Entrada: candidato. Ação: conferir que o trecho está na posição informada do texto
   normalizado da página. Saída: candidato confirmado.
5. Desvio: trecho não confere. Ação: descartar e contar em `relatorio`. Saída: nenhum fato.
6. Entrada: candidato confirmado. Ação: gravar `hub_evidencia`, `link_pagina_evidencia`,
   `sat_evidencia_trecho`; calcular a chave do fato (`numero_cnj`, tipo, sujeito, evidência de
   origem); gravar `hub_fato`, `link_processo_fato`, `link_fato_evidencia`,
   `sat_fato_evidencia_vigencia` e `sat_fato_valor` com status `automatico`. Saída: fato.
7. Desvio: fato cujo satélite corrente tem status `confirmado` ou `corrigido`. Ação: não gravar
   linha nova. Saída: fato preservado.
8. Entrada: fatos do mesmo tipo e sujeito com valores diferentes. Ação: nenhuma na gravação; os
   dois ficam vigentes. Saída: conflito visível às validações.

### A7. Tempestividade (`validacoes/civel/tempestividade.py`)

1. Entrada: fatos vigentes do recorrente: `tipo_recurso`, `data_intimacao`,
   `data_interposicao`, `qualidade_recorrente`. Ação: verificar presença e unicidade. Saída:
   valores.
2. Desvio: fato ausente. Saída: `verificar` com o fato faltante e os tipos de peça procurados.
3. Desvio: dois valores diferentes para o mesmo fato. Saída: `verificar` citando os dois.
4. Entrada: tipo do recurso. Ação: ler o prazo em `prazos_recursos.yaml` (15 dias; embargos de
   declaração, 5). Saída: prazo.
5. Entrada: qualidade do recorrente. Ação: dobrar o prazo para Fazenda Pública, Ministério
   Público e Defensoria Pública. Saída: prazo aplicado.
6. Entrada: data da intimação, prazo aplicado, feriados e suspensões. Ação: contar dias úteis a
   partir do primeiro dia útil seguinte à intimação, pulando sábados, domingos, feriados e
   suspensões. Saída: data do vencimento e lista dos dias não contados.
7. Entrada: data da interposição e vencimento. Ação: comparar. Saída: `conforme` se a
   interposição é até o vencimento; `atenção` com os dias úteis de atraso caso contrário.
8. Saída comum: valores usados (datas, prazo, dobra, dias não contados com fonte), base legal e
   fatos.

### A8. Preparo (`validacoes/civel/preparo.py`)

1. Entrada: fatos vigentes do recorrente: `tipo_recurso`, `qualidade_recorrente`,
   `data_interposicao`, `comprovante_preparo`, `gratuidade_pedido`, `gratuidade_decisao`. Saída:
   valores.
2. Desvio: `tipo_recurso` ou `qualidade_recorrente` ausente. Saída: `verificar`.
3. Desvio: qualidade dispensada em `preparo.yaml`. Saída: `conforme` com a razão.
4. Desvio: `gratuidade_decisao` com valor `deferida`. Saída: `conforme` com a razão.
5. Desvio: `gratuidade_pedido` presente sem `gratuidade_decisao`. Saída: `verificar`.
6. Entrada: `comprovante_preparo`. Ação: comparar a data com a da interposição. Saída:
   `conforme` se presente e até a interposição; `atenção` se ausente ou posterior.

### A9. Representação (`validacoes/civel/representacao.py`)

1. Entrada: fatos vigentes do recorrente: `qualidade_recorrente`, `advogado_subscritor`,
   `procuracao` (zero ou mais). Saída: valores.
2. Desvio: qualidade dispensada. Saída: `conforme` com a razão.
3. Desvio: `advogado_subscritor` ausente. Saída: `verificar`.
4. Entrada: nome e inscrição do subscritor; procurações e substabelecimentos. Ação: procurar uma
   cujo outorgante é o recorrente e cujo advogado tem a mesma inscrição na OAB ou, sem inscrição,
   o mesmo nome normalizado; seguir substabelecimentos em cadeia. Saída: procuração ou nada.
5. Saída: `conforme` com a página da procuração, ou `atenção`.

### A10. Cabimento do agravo (`validacoes/civel/cabimento.py`)

1. Entrada: fato `hipotese_decisao_agravada`. Saída: valor ou nada.
2. Desvio: fato ausente. Saída: `verificar`.
3. Entrada: valor. Ação: procurar o inciso em `cabimento_art1015.yaml`. Saída: `conforme` com o
   inciso e o trecho, ou `verificar` quando o valor é `nao_identificada`. Nunca `atenção`.

### A11. Correção de fato (rota `POST /processos/{processo_id}/fatos/{fato_id}/corrigir`)

1. Entrada: `id`, valor novo, página, início e fim do trecho. Ação: ler `v_fato`. Saída: fato ou
   404.
2. Entrada: página e posição. Ação: conferir o trecho contra o texto da página. Saída: trecho ou
   422.
3. Entrada: trecho. Ação: gravar evidência, `link_fato_evidencia` e
   `sat_fato_evidencia_vigencia` (`vigente = true` na nova, `false` nas anteriores). Saída:
   evidência.
4. Entrada: valor novo. Ação: gravar `sat_fato_valor` com status `corrigido` e o autor; evento
   `correcao_fato` (A15). Saída: fato corrigido.
5. Entrada: processo. Ação: rodar o catálogo (A5, passo 9). Saída: achados novos se o resultado
   mudou.
6. Confirmação sem mudança de valor: só o passo 4, com status `confirmado`.

### A12. Reclassificação de peça (rota `POST /processos/{processo_id}/pecas/{peca_id}/reclassificar`)

1. Entrada: `id`, tipo, página inicial e final. Ação: ler `v_peca`. Saída: peça ou 404.
2. Desvio: intervalo fora do arquivo ou `final < inicial`. Saída: 422.
3. Desvio: página inicial igual à atual. Ação: gravar `sat_peca_classificacao` com `metodo =
   manual` e o autor. Saída: mesma peça, linha nova.
4. Entrada: página inicial diferente. Ação: gravar linha `vigente = false` na peça atual; gravar
   `hub_peca` da nova chave, `link_arquivo_peca` e `sat_peca_classificacao` manual. Saída: peça
   nova.
5. Entrada: processo. Ação: evento `reclassificacao_peca`; refazer A6 e o passo 9 de A5 para o
   processo. Saída: fatos e achados atualizados.

### A13. Descarte (`lupa_descartar_processo`, `seguranca/descarte.py`)

1. Entrada: `id` do processo, usuário desembargador. Ação: ler `v_processo`. Saída: processo, 403
   ou 404.
2. Entrada: `hk_processo`. Ação, na função do banco: `set_config('lupa.descarte', 'on', true)`.
   Saída: transação autorizada a apagar.
3. Entrada: `hk_processo`. Ação: reunir pelos links os `hk` de arquivos, páginas, peças,
   evidências, fatos, achados, partes e conversas do processo. Saída: conjuntos de `hk`.
4. Entrada: conjuntos. Ação: apagar as linhas de todos os satélites desses hubs e de
   `sat_fato_evidencia_vigencia`; apagar `sat_processo_revisao`. Saída: contagens.
5. Entrada: `sat_processo_chave`. Ação: calcular o SHA-256 da DEK cifrada e apagar a linha.
   Saída: hash.
6. Mantidos: hubs, links, `sat_processo_dados`, `sat_processo_estado`, `link_chamada_modelo`,
   `link_evento_auditoria`.
7. Entrada: hash. Ação, no Python e na mesma transação: gravar `sat_processo_estado` com
   `descartado` e o evento `processo_descartado` com o hash. Saída: commit.
8. Entrada: prefixo `processo/<hk>/` e cache de renderização. Ação: apagar os objetos e tirar a
   DEK do contexto. Saída: número de objetos apagados.
9. Erro no passo 8: registrar `descarte_objetos_pendente` na auditoria; repetir o descarte apaga
   o que restou.

### A14. Login e sessão (`acesso/`)

1. Entrada: nome e senha. Ação: calcular `chave` (SHA-256 do nome) e ler `v_bloqueio_login`.
   Saída: bloqueado ou não.
2. Desvio: bloqueado. Saída: 429.
3. Entrada: nome. Ação: ler `v_usuario` e verificar a senha com Argon2. Saída: usuário ou falha.
4. Desvio: falha ou usuário inativo. Ação: gravar `hub_chave_login` e `sat_chave_login_falha`;
   se as falhas na janela atingem o limite, gravar `sat_chave_login_bloqueio`; evento
   `login_falha`. Saída: 401.
5. Entrada: usuário com senha certa. Ação: se há falhas do nome desde o último zeramento,
   gravar `sat_chave_login_bloqueio` com `bloqueado_ate` nulo (zera a contagem sem `DELETE`);
   gravar `hub_desafio_mfa`, `link_desafio_mfa_usuario` e `sat_desafio_mfa_estado` com validade
   de 5 min. Saída: token do desafio.
6. Entrada: token e código TOTP. Ação: ler `v_desafio_mfa`; recusar expirado ou consumido;
   verificar o código e que o passo é maior que `mfa_ultimo_passo`. Saída: válido ou 401.
7. Entrada: código válido. Ação: gravar `sat_desafio_mfa_estado` com `consumido = true`,
   `sat_usuario_credencial` com o passo novo, `hub_sessao`, `link_sessao_usuario` e
   `sat_sessao_estado`; zerar as falhas como no passo 5; evento `login`. Saída: cookie de
   sessão.
8. Requisição autenticada. Entrada: cookie. Ação: ler `v_sessao`; recusar revogada, expirada ou
   inativa há 30 min. Saída: usuário e papel, ou 401.
9. Entrada: sessão válida. Ação: se `ultimo_acesso_em` tem 60 s ou mais, gravar
   `sat_sessao_estado` com o instante atual. Saída: sessão.
10. Saída do sistema e desativação de usuário: gravar `sat_sessao_estado` com `revogada = true`
    para cada sessão.
11. Primeiro usuário (`criar_desembargador.py`). Entrada: variáveis de ambiente. Ação: se
    `v_usuario` não tem desembargador, gravar `hub_usuario`, `sat_usuario_cadastro` e
    `sat_usuario_credencial` com troca obrigatória; se tem, sair sem gravar. Saída: contagem.

### A15. Evento de auditoria (`auditoria/registrador.py`)

1. Entrada: ação, usuário, processo, objeto, resultado, IP. Ação: derivar a localização do IP
   pela base GeoIP local. Saída: localização ou nulo.
2. Entrada: transação. Ação: `pg_advisory_xact_lock(<constante da cadeia>)`. Saída: escrita
   serializada.
3. Entrada: cadeia. Ação: ler `sequencia` e `hash_evento` do último evento. Saída: antecessor ou
   nada.
4. Entrada: campos do evento e `hash_anterior`. Ação: calcular `hash_evento` (SHA-256 do JSON
   canônico) e `hk_evento` (A1 sobre `sequencia`). Saída: hashes.
5. Entrada: evento. Ação: inserir em `link_evento_auditoria` na transação da ação auditada.
   Saída: evento gravado antes da resposta.
6. Verificação. Entrada: todos os eventos em ordem de `sequencia`. Ação: recalcular cada hash e
   conferir o encadeamento e a ausência de saltos. Saída: íntegra, ou a primeira `sequencia`
   inconsistente.

### A16. Pergunta ao chat (`agente/servico.py`)

1. Entrada: `id` do processo, conversa, pergunta. Ação: ler `v_processo`. Saída: processo ou 404.
2. Desvio: `em_revisao`. Saída: aviso de revisão; nenhuma chamada.
3. Desvio: conversa encerrada ou tetos atingidos em `v_conversa`. Saída: aviso de teto; nenhuma
   chamada.
4. Entrada: pergunta. Ação: aplicar a política de recusa. Saída: segue, ou mensagem de recusa
   gravada (fim).
5. Entrada: pergunta. Ação: gravar a mensagem do usuário em `sat_conversa_mensagem`; montar o
   contexto só com dados do `hk_processo` da conversa, delimitados e rotulados pela origem da
   peça. Saída: contexto.
6. Entrada: contexto. Ação: chamar o modelo com as ferramentas de leitura e de cálculo. Saída:
   resposta com citações.
7. Entrada: resposta. Ação: gravar `link_chamada_modelo` e o evento `chamada_modelo`. Saída:
   chamada registrada.
8. Entrada: resposta. Ação: procurar instrução dos autos refletida e identificador de outro
   processo. Saída: liberada ou bloqueada.
9. Desvio: bloqueada. Ação: gravar `sat_processo_revisao` (`aberta`, motivo, status anterior),
   `sat_processo_estado` (`em_revisao`), mensagem `descartada` e evento. Saída: aviso de revisão.
10. Entrada: citações. Ação: conferir cada uma contra o texto da página; descartar as que não
    conferem e registrar. Saída: citações válidas.
11. Desvio: nenhuma citação válida. Ação: gravar mensagem `sem_evidencia`. Saída: "sem
    evidência".
12. Entrada: resposta e citações válidas. Ação: gravar a mensagem `respondida` e
    `sat_conversa_estado` com os contadores. Saída: resposta rotulada como gerada por IA.
13. Liberação da revisão. Entrada: desembargador. Ação: gravar `sat_processo_revisao`
    (`liberada`), `sat_processo_estado` com o status anterior e o evento. Saída: chat disponível.

## Checklist de testes

Marcar na fase de tarefas. `U` é unitário; `I`, integração (marcador `integracao`).

### Fase 1

- [x] U: nenhum módulo de `lupa_pipeline` importa `lupa_intranet` (D2).
- [ ] Suíte completa da 0.1 verde nos dois pacotes, com 90% de cobertura em cada.
- [x] `docker build --target verificacao intranet/web` verde.

### Fase 2

- [x] U: `config` ignora as chaves removidas de Redis, métricas e backup (T2.1, T3.8).
- [x] I: `GET /metricas/servico` responde 404 (`test_rotas_de_metricas_nao_existem`, T2.1).
- [x] `docker compose --profile e2e config --services` lista os nove serviços de D22 (T3.8).

### Fase 3

- [x] U: `chave_hash` é estável, sensível à ordem e recusa parte vazia (A1). T3.1.
- [x] U: `hash_diff` com DEK difere do sem DEK para o mesmo conteúdo (D5). T3.1.
- [x] I: `test_migracao_0001` sobe e desce. T3.2.
- [x] I: `UPDATE` e `DELETE` em hub, link e satélite são recusados sob `lupa_app` (D6). T3.3.
- [x] I: `gravar_satelite` não insere com `hash_diff` igual e insere com diferente (A2). T3.3.
- [x] I: fato sem evidência é recusado no commit (RF-FAT-01). T3.2.
- [x] I: login, falha, bloqueio, desafio e sessão (A14; RF-ACE-01, 02). T3.4.
- [ ] I: assessor recebe 403 em auditoria e usuários; desembargador não (RF-ACE-03).
  - Usuários feito em T3.4 (`test_usuarios.py`); auditoria fica com T3.11, que monta a rota.
- [x] I: criação, desativação, reativação e redefinição de assessor (RF-ACE-04). T3.4.
- [x] I: `criar_desembargador.py` cria um e não repete (RF-ACE-05). T3.4.
- [x] I: cadastro recusa CNJ inválido e duplicado; lista igual para dois usuários (RF-PRO-01, 02). T3.6.
- [x] I: responsável não restringe acesso (RF-PRO-03). T3.6.
- [x] I: arquivo com marca de sigilo é aceito (RF-PRO-04, T3.7).
- [x] I: upload lacra, detecta duplicado e deixa `recebido` (A3; RF-ING-01, T3.7).
- [ ] I: PDF com senha vai a quarentena (RF-ING-02).
- [x] I: worker processa a fila sem Redis; segundo worker encerra (A4; RES-07, T3.8).
- [ ] I: interrupção depois de parte dos lotes retoma sem duplicar página (RF-ING-07).
- [ ] I: estado parcial lista as páginas faltantes (RF-ING-06).
- [x] I: cadeia de auditoria única; alteração direta no banco é apontada (A15; RF-AUD-03). T3.4 (`test_registrador.py`; o registrador foi reescrito em T3.4 porque o login grava eventos).
- [ ] I: cada ação da lista gera evento, com localização (RF-AUD-01).
- [ ] I: varredura de eventos e logs não acha texto sintético (RF-AUD-02).
- [ ] I: relatório de uso com contagens e custo (RF-AUD-05).
- [ ] I: descarte apaga satélites e chave, mantém hubs, links e auditoria; conteúdo responde
  indisponível (A13; RF-PRO-05).
- [x] I: varredura do banco e do storage não acha texto em claro; valor em claro é recusado
  (RF-SEG-01). T3.5 (`test_cifra_satelites.py`, no nível dos satélites e do
  storage; a varredura pela API, em `intranet/api/tests/seguranca/test_cifra_banco.py`, volta em
  T3.14).
- [ ] I: cofre selado dá 503 na saúde (RF-SEG-02).
  - Não feito em T3.5: a saúde não mudou e o teste da rota depende de `create_app` (T3.14).
- [ ] I: teto de conversa e processo em revisão bloqueiam a chamada; liberação restaura (A16;
  RF-CHA-06, 08).

### Fase 4

- [ ] U: classificação de cada tipo de peça da seção 3.2 e `outros` (RF-PEC-01).
- [ ] U: cada extrator de A6 com trecho que confere e que não confere (RF-FAT-01).
- [ ] U: tempestividade: 15º e 16º dia útil, prazo em dobro, feriado local, recesso, embargos em
  5 dias, fato ausente, conflito (A7; RF-VAL-02, RF-FAT-02).
- [ ] U: preparo: comprovante, dispensa, gratuidade deferida, pedido sem decisão, ausência (A8;
  RF-VAL-03).
- [ ] U: representação: procuração, substabelecimento em cadeia, dispensa, sem procuração,
  assinatura não identificada (A9; RF-VAL-04).
- [ ] U: cabimento: inciso identificado e não identificado; nunca `atenção` (A10; RF-VAL-05).
- [ ] U: catálogo aplica a tabela 3.1; ação originária não gera achado (RF-VAL-01).
- [ ] U: linha de comando sobre `fatos_exemplo.json` reproduz o gabarito (RF-VAL-06).
- [ ] U: gerador produz as cinco classes com gabarito (RNF-04).
- [ ] I: ponta a ponta de cada classe contra o gabarito: páginas, peças, partes, fatos e achados
  (RF-ING-03, RF-FAT-04, RNF-01, RNF-02).
- [ ] I: correção de fato preservada no reprocessamento e usada pela validação (A11; RF-FAT-03,
  RF-ING-08).
- [ ] I: reclassificação mantém histórico (A12; RF-PEC-02).
- [ ] I: estouro de memória no sandbox termina em `falho` (RF-ING-04).
- [ ] U: recusa do chat para cada pergunta da suíte (RF-CHA-02).
- [ ] I: citação inexistente descartada; nenhuma válida vira "sem evidência" (RF-CHA-03).
- [ ] I: conversa do processo A não lê o processo B (RF-CHA-01).

### Fase 5

- [ ] Unitários do front: permissões com dois papéis, rótulos cíveis, ids em texto, envio com
  classe.
- [ ] `svelte-check`, ESLint e Prettier sem aviso.

### Fase 6

- [ ] I (`injecao`): corpus de injeção gera as marcas e não cria nem suprime achado (RF-ING-05,
  RNF-03).
- [ ] I (`agente`): nenhuma instrução dos autos é seguida (RF-CHA-05).
- [ ] E2E: login, processos, dossiê, visualizador, chat, auditoria, gestão de assessores (RNF-09).
- [ ] Cabeçalhos de segurança do proxy (RF-SEG-03).
- [ ] I: worker não abre conexão externa (RF-SEG-04).

### Revisão manual

- Componentes Svelte só de apresentação.
- Chamada real ao modelo (marcador `llm`).
- Capturas de tela dos guias.
- Regras jurídicas da seção 11 da especificação, pelo gabinete.
