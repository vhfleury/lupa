# Lupa 0.2 — Especificação

13 de novembro de 2026 · Estado: **aprovada** (alterada e aprovada em 15 de novembro de 2026: decisões 40 a 45; em 19 de novembro de 2026: decisões 46 a 53; em 20 de novembro de 2026: decisões 54 a 58)

Fonte da verdade da versão 0.2. Diz o que o sistema faz e para quem, com requisitos e critérios
de aceite verificáveis. Não decide implementação: isso é do plano, que só começa depois desta
especificação aprovada. Substitui, para a 0.2, [requisitos-v1.md](../requisitos-v1.md) e
[catalogo-validacoes.md](../catalogo-validacoes.md). O [prompt-injection.md](../prompt-injection.md)
continua como referência dos controles de ingestão.

## 1. Objetivo

Ferramenta web privada que auxilia um desembargador da área cível e seus assessores a conferir
processos em 2º grau. O sistema recebe os autos, organiza as peças, monta a linha do tempo, roda
quatro validações objetivas e responde perguntas de localização sobre o processo. Toda informação
exibida aponta para a página de origem.

A ferramenta é de apoio. Não decide, não opina, não valora prova, não conclui sobre aplicação de
norma e não redige atos. A conclusão jurídica é do assessor ou do magistrado.

A 0.2 é uma simplificação da 0.1.0: mantém o que serve a este objetivo e remove o resto
(seção 8).

## 2. Usuários

| Papel | Vê | Faz |
| --- | --- | --- |
| Assessor | todos os processos | cria processo, envia autos, usa dossiê, validações e chat, anota, corrige fato, reclassifica peça |
| Desembargador | o mesmo do assessor, mais a auditoria | o mesmo do assessor; cria, desativa e reativa assessores; redefine senha e MFA deles; exporta o relatório de uso |

Não há outro papel. O primeiro desembargador é criado por procedimento do responsável técnico,
fora da interface.

## 3. Escopo jurídico

### 3.1 Classes processuais

| Classe | Validações aplicáveis (seção 4.6) |
| --- | --- |
| Apelação cível | tempestividade, preparo, representação |
| Agravo de instrumento | tempestividade, preparo, representação, cabimento |
| Embargos de declaração | tempestividade, representação |
| Agravo interno | tempestividade, preparo, representação |
| Ação originária (rescisória, mandado de segurança, reclamação, conflito de competência e demais) | nenhuma |

Toda classe tem ingestão, dossiê, visualizador e chat.

### 3.2 Tipos de peça

Petição inicial, contestação, réplica, decisão interlocutória, sentença, embargos de declaração,
apelação, agravo de instrumento, agravo interno, contrarrazões, acórdão, certidão, procuração,
comprovante de preparo, laudo pericial, parecer do Ministério Público, outros.

"Agravo interno" foi acrescentado à lista confirmada porque a classe está no escopo (3.1).

### 3.3 Origem dos autos

PDF ou ZIP exportado do Projudi/PJD do TJGO, enviado pela interface. Não há integração com o
Projudi nem com o DataJud.

## 4. Requisitos funcionais

Cada requisito tem identificador `RF-<ÁREA>-NN` e critérios de aceite no formato
Dado/Quando/Então. Os critérios usam autos sintéticos.

### 4.1 Acesso (ACE)

**RF-ACE-01 — Autenticação.** Todo acesso exige usuário, senha e código TOTP. Não há e-mail no
cadastro nem no login.

- Dado um usuário ativo com MFA confirmado, quando informa senha e código corretos, então recebe
  uma sessão.
- Dado um usuário com senha correta e código errado, quando tenta entrar, então é recusado e a
  falha fica na auditoria.
- Dada uma requisição sem sessão válida a qualquer rota que não seja login ou saúde, então a
  resposta é 401.

**RF-ACE-02 — Bloqueio por tentativas.** Falhas seguidas de login bloqueiam novas tentativas do
mesmo usuário por um período.

- Dado um usuário que atingiu o limite de falhas, quando informa credenciais corretas dentro do
  período, então é recusado.

**RF-ACE-03 — Papéis.** Existem dois papéis, com as permissões da seção 2, verificadas no
servidor em toda requisição.

- Dado um assessor, quando chama a auditoria ou a gestão de usuários, então recebe 403.
- Dado um desembargador, quando chama as mesmas rotas, então recebe o conteúdo.

**RF-ACE-04 — Gestão de assessores.** O desembargador cria, desativa e reativa assessores e
redefine senha e MFA deles. Credencial criada ou redefinida é temporária, com troca obrigatória
no primeiro acesso.

- Dado um assessor recém-criado, quando entra com a senha temporária, então só consegue trocar a
  senha e configurar o MFA antes de qualquer outra tela.
- Dado um assessor desativado, quando tenta entrar, então é recusado, e seus eventos de auditoria
  continuam consultáveis.

**RF-ACE-05 — Primeiro usuário.** O primeiro desembargador é criado por comando do responsável
técnico.

- Dado um banco sem usuários, quando o comando roda, então existe um desembargador com credencial
  temporária.
- Dado um banco que já tem desembargador, quando o comando roda sem pedido explícito de novo
  usuário, então nada é criado.

### 4.2 Processos (PRO)

**RF-PRO-01 — Cadastro pelo arquivo.** O usuário cria um processo enviando o PDF ou ZIP dos autos.
O sistema lê o número CNJ e a classe (3.1) nas primeiras páginas e cria o processo sem outro
passo. Não há cadastro sem arquivo.

- Dado um arquivo cuja capa traz um número CNJ com dígito verificador válido e uma classe da seção
  3.1, quando é enviado, então o processo é criado com esse número e essa classe, o arquivo fica
  recebido e quem enviou é o criador.
- Dado um arquivo sem número CNJ válido, com números válidos diferentes sem rótulo que indique o
  do processo, ou sem classe reconhecida, quando é enviado, então nada é gravado e a resposta traz
  o que foi lido e o que falta; quando o usuário reenvia o mesmo arquivo informando o que faltava,
  então o processo é criado.
- Dado um número informado pelo usuário com dígito verificador inválido, então é recusado com a
  razão.
- Dado um arquivo cujo número já está cadastrado, quando é enviado, então entra como arquivo do
  processo existente, a classe do processo não muda e a resposta aponta o processo.
- Dado um arquivo cujo número é de processo descartado, quando é enviado, então é recusado.
- Dado um arquivo que não abre (senha, corrompido, truncado, tipo não aceito ou ZIP malicioso),
  quando é enviado para criar processo, então é recusado com o motivo e nada é gravado.

**RF-PRO-02 — Lista.** O usuário vê todos os processos, com número, classe, estado da ingestão e
responsáveis.

- Dado dois usuários, quando cada um lista os processos, então veem a mesma lista.

**RF-PRO-03 — Responsáveis.** Um processo pode ter um ou mais usuários responsáveis, usados para
filtrar a lista. Responsável não restringe acesso.

- Dado um processo sem o usuário como responsável, quando ele o abre, então o conteúdo é exibido.

**RF-PRO-04 — Qualquer processo é aceito.** O sistema não distingue processo público de processo
em segredo de justiça.

- Dado um arquivo de processo com marca de sigilo, quando é enviado, então é recebido e processado
  como qualquer outro.

**RF-PRO-05 — Descarte.** O desembargador pode descartar um processo. O descarte torna
irrecuperável o conteúdo dos autos desse processo e preserva a auditoria.

- Dado um processo descartado, quando qualquer usuário pede página, peça, fato, achado ou
  conversa dele, então recebe erro de conteúdo indisponível.
- Dado um processo descartado, quando o desembargador consulta a auditoria, então os eventos
  dele continuam lá.

**RF-PRO-06 — Correção da classe.** O usuário pode corrigir a classe de um processo. A classe
anterior fica guardada, com quem mudou e quando, e as validações são refeitas para a nova classe.

- Dado um processo cuja classe foi corrigida, quando o processo é aberto, então mostra a nova
  classe e permite ver a anterior, quem corrigiu e quando.
- Dado um processo cuja classe foi corrigida, quando os achados são consultados, então são os das
  validações da nova classe (3.1).
- Dado um processo descartado, quando a classe é corrigida, então é recusado.

### 4.3 Ingestão (ING)

**RF-ING-01 — Recepção e lacre.** O usuário envia PDF ou ZIP para criar um processo (RF-PRO-01)
ou a um processo existente. Cada arquivo recebe SHA-256 no recebimento; o original nunca é
alterado.

- Dado um arquivo enviado, quando o original é lido de volta, então seu SHA-256 é o registrado.
- Dado o mesmo arquivo enviado de novo ao mesmo processo, então a resposta informa duplicidade e
  nada novo é gravado.

**RF-ING-02 — Arquivo inválido.** Arquivo corrompido, truncado, com senha, de tipo não aceito ou
ZIP malicioso enviado a um processo existente vai para quarentena com o motivo. No envio que cria
o processo, o arquivo é recusado (RF-PRO-01).

- Dado um PDF com senha, quando é enviado, então o estado final é quarentena com motivo `senha` e
  nenhuma página é gravada.

**RF-ING-03 — Páginas.** Cada página tem texto, coordenadas e tipo (nativa, OCR ou vazia). OCR só
nas páginas sem texto nativo utilizável.

- Dado um PDF com páginas nativas e digitalizadas, quando a ingestão termina, então há uma página
  gravada por página do PDF, cada uma com o tipo correto.

**RF-ING-04 — Parsing isolado.** A abertura de PDF e o OCR rodam isolados, sem rede e sem acesso
ao banco, com limite de memória, CPU e tempo. A leitura das primeiras páginas no envio que cria o
processo (RF-PRO-01) roda no serviço da API, em subprocesso sem credenciais, com a rede bloqueada
no próprio subprocesso e com os mesmos limites (risco 4 da seção 10).

- Dado o subprocesso de leitura do envio, quando tenta abrir uma conexão de rede ou ler uma
  variável de ambiente com credencial, então falha.

- Dado um PDF que estoura o limite de memória, quando é processado, então o estado final é falho
  com o motivo e o serviço continua atendendo outros arquivos.

**RF-ING-05 — Saneamento contra injeção.** Texto oculto, bloco codificado, padrão de instrução,
idioma inesperado, divergência entre texto nativo e OCR, metadado suspeito, homóglifos e
densidade anômala são detectados por página; as marcas acompanham a página até a tela e até o
contexto do agente.

- Dado o corpus de injeção por vetor, quando é ingerido, então cada vetor produz a marca
  correspondente na página.
- Dado o mesmo corpus, quando as validações rodam, então nenhum achado é criado nem suprimido em
  relação ao mesmo processo sem a injeção.

**RF-ING-06 — Estado visível.** O usuário acompanha o estado de cada arquivo: recebido, em
processamento, concluído, parcial (com as páginas que faltam), falho ou quarentena (com o
motivo).

- Dado um arquivo com extração incompleta, quando o usuário abre o processo, então vê o estado
  parcial e a lista das páginas que faltam.

**RF-ING-07 — Retomada.** Interrupção no meio do processamento não perde nem duplica resultado.

- Dado um processamento interrompido depois de parte das páginas gravadas, quando o serviço
  volta, então o arquivo chega ao estado final sem intervenção e sem página duplicada.

**RF-ING-08 — Reprocessamento.** Mudar a versão do extrator refaz as páginas; mudar só as regras
de peças, eventos ou validações refaz só o que depende delas. Correções e anotações feitas por
pessoa são preservadas.

- Dado um fato corrigido por um assessor, quando o processo é reprocessado, então a correção
  continua vigente.

### 4.4 Peças (PEC)

**RF-PEC-01 — Separação e classificação.** As páginas são agrupadas em peças, cada uma com tipo
(3.2), intervalo de páginas, origem (juízo, Ministério Público, parte, terceiro ou desconhecida),
confiança e data quando houver. Classificação por regras, sem modelo de linguagem.

- Dado o processo sintético de referência de cada classe, quando a ingestão termina, então o
  índice de peças coincide com o gabarito dentro da meta do RNF-02.
- Dada uma peça que nenhuma regra reconhece, então o tipo é `outros`.

**RF-PEC-02 — Reclassificação.** O usuário pode mudar o tipo ou o intervalo de uma peça. A
versão anterior fica guardada, com quem mudou e quando.

- Dada uma peça reclassificada, quando o índice é consultado, então mostra a nova e permite ver a
  anterior.

### 4.5 Fatos e partes (FAT)

**RF-FAT-01 — Fatos com evidência.** O sistema extrai dos autos os fatos da tabela abaixo. Cada
fato tem ao menos uma evidência: página, trecho literal, posição e hash do trecho. Fato sem
evidência não é gravado.

| Fato | Usado por |
| --- | --- |
| Data da sentença ou da decisão recorrida | linha do tempo, tempestividade |
| Data da intimação da decisão recorrida, por recorrente | tempestividade |
| Tipo do recurso e recorrente | todas as validações |
| Data da interposição do recurso | tempestividade, preparo |
| Qualidade do recorrente: Fazenda Pública, Ministério Público, Defensoria Pública ou particular | tempestividade, preparo, representação |
| Comprovante de preparo: presença e data | preparo |
| Gratuidade da justiça: pedido e decisão | preparo |
| Advogado que assina o recurso | representação |
| Procuração ou substabelecimento: outorgante e advogado | representação |
| Hipótese da decisão agravada | cabimento |
| Datas de ajuizamento, citação, contestação e acórdão | linha do tempo |
| Relator e órgão julgador | cabeçalho do processo, dossiê |
| Assunto e valor da causa | cabeçalho do processo, dossiê |
| Juízo de origem e data de distribuição | cabeçalho do processo, dossiê |

- Dado o processo sintético de referência, quando a ingestão termina, então relator, órgão
  julgador, assunto, valor da causa, juízo de origem e data de distribuição coincidem com o
  gabarito, cada um com a página de origem.
- Dado qualquer fato gravado, quando sua evidência é conferida contra o texto da página, então o
  trecho está na posição registrada e o hash confere.
- Dado um trecho candidato a fato cuja evidência não confere, então o fato não é gravado.

**RF-FAT-02 — Conflito.** Duas fontes com valores diferentes para o mesmo fato são mantidas e
sinalizadas; o sistema não escolhe.

- Dadas duas certidões com datas de intimação diferentes para o mesmo recorrente, quando a
  tempestividade roda, então o resultado é `verificar` e cita as duas.

**RF-FAT-03 — Correção.** O usuário pode confirmar ou corrigir um fato. A correção exige
evidência, gera registro novo ligado ao anterior e não o apaga.

- Dado um fato corrigido, quando as validações rodam de novo, então usam o valor corrigido e o
  achado indica que o fato foi corrigido por pessoa.

**RF-FAT-04 — Partes.** O sistema registra as partes do processo com nome e polo, como aparecem
nos autos, sem pseudonimização.

- Dado o processo sintético de referência, quando a ingestão termina, então a ficha lista as
  partes do gabarito com o polo correto e a página de origem.
- Dado um processo com partes extraídas, quando o usuário o abre, então o cabeçalho mostra as
  partes com o polo; a lista de processos não mostra partes.

### 4.6 Validações (VAL)

**RF-VAL-01 — Regras comuns.** Toda validação é determinística. O resultado é um achado
`conforme`, `atenção` ou `verificar`, com todos os valores usados, a base legal e, para cada
valor, o fato e a página de origem. O texto vem de modelo de frase fixo, não de modelo de
linguagem. Prazos, feriados e suspensões ficam em dados versionados, cada um com versão e fonte.

- Dado um fato necessário ausente, então o resultado é `verificar`, dizendo qual fato falta e
  onde o sistema procurou.
- Dada uma classe à qual a validação não se aplica (3.1), então nenhum achado é gerado.
- Dado um achado gravado, então ele não é alterado; nova execução com resultado diferente gera
  achado novo.

**RF-VAL-02 — Tempestividade.** Confere se o recurso foi interposto no prazo.

Regra: prazo de 15 dias para apelação, agravo de instrumento e agravo interno (art. 1.003, § 5º,
CPC) e de 5 dias para embargos de declaração (art. 1.023 CPC); contagem em dias úteis (art. 219),
excluído o dia do começo e incluído o do vencimento (art. 224); prazo em dobro para Ministério
Público, Fazenda Pública e Defensoria Pública (arts. 180, 183 e 186); feriados e suspensões,
inclusive o recesso de 20/12 a 20/01 (art. 220), não contam.

- Dada intimação numa segunda-feira útil e apelação de particular interposta no 15º dia útil
  seguinte, então `conforme`.
- Dada a mesma intimação e interposição no 16º dia útil, então `atenção`, com o número de dias
  úteis de atraso e a lista dos dias não contados.
- Dado recorrente Fazenda Pública e interposição no 30º dia útil, então `conforme`, e o achado
  cita o prazo em dobro.
- Dado um feriado local dentro do prazo, então o achado lista o feriado e sua fonte.

**RF-VAL-03 — Preparo.** Confere se o recurso veio acompanhado do comprovante de preparo
(art. 1.007 CPC).

- Dado comprovante de preparo com data até a da interposição, então `conforme`.
- Dado recorrente Ministério Público, Fazenda Pública ou Defensoria Pública, ou decisão que
  deferiu a gratuidade, então `conforme`, com a razão da dispensa.
- Dado pedido de gratuidade sem decisão localizada, então `verificar`.
- Dado recurso de particular sem comprovante e sem gratuidade, então `atenção`.
- O sistema não confere valor recolhido.

**RF-VAL-04 — Representação.** Confere se há nos autos procuração ou substabelecimento em nome do
advogado que assina o recurso, outorgado pelo recorrente (art. 104 CPC).

- Dada procuração do recorrente ao advogado que assina, então `conforme`, com a página da
  procuração.
- Dado recorrente Ministério Público, Fazenda Pública ou Defensoria Pública, então `conforme`,
  com a razão da dispensa.
- Dado recurso assinado por advogado sem procuração nem substabelecimento localizado, então
  `atenção`.
- Dada assinatura não identificada, então `verificar`.

**RF-VAL-05 — Cabimento do agravo de instrumento.** Confere se a decisão agravada corresponde a
uma hipótese do art. 1.015 do CPC.

- Dada decisão agravada que o sistema associa a um inciso do art. 1.015, então `conforme`, com o
  inciso e o trecho.
- Dada decisão que o sistema não associa a nenhum inciso, então `verificar`, nunca `atenção`: a
  admissão fora do rol (taxatividade mitigada) depende de juízo do magistrado.

**RF-VAL-06 — Execução pela linha de comando.** As validações rodam sobre um arquivo de fatos,
fora da interface, para conferência.

- Dado o arquivo de fatos de exemplo, quando o comando roda, então a saída é a lista de achados
  igual à do gabarito.

### 4.7 Dossiê e visualizador (DOS)

**RF-DOS-01 — Ficha.** Número, classe, partes e polos, responsáveis e estado da ingestão.

**RF-DOS-02 — Índice de peças.** Tipo, intervalo de páginas, origem, data e confiança de cada
peça vigente.

**RF-DOS-03 — Linha do tempo.** Fatos datados em ordem, cada um ligado à página de origem.

**RF-DOS-04 — Achados.** Lista dos achados vigentes, com resultado, explicação, valores e ligação
para cada fato e página.

- Para RF-DOS-01 a 04: dado o processo sintético de referência, quando o dossiê é aberto, então
  cada item exibido coincide com o gabarito e tem ligação para a página.

**RF-DOS-05 — Visualizador.** Abre o original na página pedida e destaca o trecho da evidência.
Marcas de saneamento da página aparecem na tela.

- Dada uma evidência, quando o usuário segue a ligação, então o visualizador abre na página da
  evidência com o trecho destacado.
- Dada uma página com marca de texto oculto, quando é aberta, então o aviso aparece.

**RF-DOS-06 — Anotações.** O usuário anota um achado ou um fato. Anotação não altera o alvo.

- Dada uma anotação gravada, quando outro usuário abre o mesmo achado, então vê o texto, o autor
  e a data.

### 4.8 Chat (CHA)

**RF-CHA-01 — Escopo permitido.** O chat localiza, extrai, resume e relaciona informações dos
autos de um único processo por conversa, sempre com citação de página. Só tem ferramentas de
leitura e de cálculo de prazo.

- Dada uma pergunta de localização sobre o processo sintético, então a resposta traz ao menos uma
  citação que confere.
- Dada uma conversa do processo A, quando a pergunta pede conteúdo do processo B, então nenhum
  dado de B entra na resposta.

**RF-CHA-02 — Escopo vedado.** O chat recusa valorar prova, concluir sobre aplicação de norma ou
precedente, opinar sobre o resultado e redigir ato, e explica o limite.

- Dada cada pergunta da suíte de recusa, então a resposta é recusa.

**RF-CHA-03 — Citação conferida.** Toda citação é conferida por código contra o texto da página
antes de aparecer. Citação que não confere é descartada e registrada.

- Dada resposta do modelo com citação inexistente na página, então a citação não é exibida e o
  descarte fica na auditoria.
- Dada resposta em que nenhuma citação confere, então o usuário vê "sem evidência", não o texto.

**RF-CHA-04 — Rótulo.** Toda resposta aparece em bloco rotulado como gerado por IA.

**RF-CHA-05 — Autos como dado.** O texto dos autos entra no contexto delimitado e rotulado por
origem da peça, nunca como instrução.

- Dado o corpus de injeção, quando o chat responde sobre esses processos, então nenhuma instrução
  contida nos autos é seguida.

**RF-CHA-06 — Limites e registro.** Cada conversa tem teto de uso. Modelo, versão do modelo e
versão do prompt ficam registrados por chamada.

- Dada uma conversa que atinge o teto, quando o usuário pergunta de novo, então recebe aviso de
  teto e nenhuma chamada ao modelo é feita.

**RF-CHA-07 — Histórico.** O usuário reabre as conversas de um processo.

**RF-CHA-08 — Processo em revisão.** Resposta do modelo bloqueada pela conferência (instrução
dos autos refletida ou identificador de outro processo) põe o processo em revisão. Em revisão, o
chat do processo fica indisponível até o desembargador liberar.

- Dada uma resposta bloqueada, quando o usuário pergunta de novo no mesmo processo, então recebe
  aviso de revisão e nenhuma chamada ao modelo é feita.
- Dado um processo em revisão, quando o desembargador libera, então o processo volta ao estado
  anterior e a liberação fica na auditoria.

### 4.9 Auditoria (AUD)

**RF-AUD-01 — Eventos.** Ficam registrados: login e falha de login, redefinição de senha ou MFA,
criação, desativação e reativação de usuário, criação de processo, upload, abertura de processo,
página visualizada, busca, pergunta ao chat, chamada ao modelo, citação descartada, anotação,
correção de fato, reclassificação de peça, execução de validação, descarte de processo,
exportação de relatório, abertura e liberação de revisão. Cada evento tem quem, quando, IP,
localização aproximada derivada do IP, processo, ação, objeto e resultado.

- Dada cada ação da lista, quando é executada, então existe um evento correspondente.

**RF-AUD-02 — Sem conteúdo.** Evento de auditoria e log não contêm conteúdo de autos, texto de
pergunta ou resposta, senha nem token; contêm identificadores e hashes.

- Dada a execução da suíte completa, quando os eventos e os logs são varridos pelos textos
  sintéticos conhecidos, então nenhum aparece.

**RF-AUD-03 — Imutável e verificável.** A trilha só recebe inclusões e é encadeada por hash;
existe verificação da cadeia.

- Dado um evento alterado ou removido diretamente no banco, quando a verificação roda, então
  aponta o primeiro evento inconsistente.

**RF-AUD-04 — Consulta.** O desembargador consulta a auditoria por período, usuário, processo e
ação.

**RF-AUD-05 — Relatório de uso.** O desembargador exporta em CSV o uso por processo e por
usuário, para cumprir o dever de informar ao tribunal (art. 19, § 7º, Res. CNJ 615/2025).

- Dado um período com chamadas ao modelo, quando o relatório é exportado, então cada processo e
  usuário do período aparece com suas contagens e com o custo estimado das chamadas, calculado
  de uma tabela de preços versionada.

### 4.10 Proteção dos dados (SEG)

**RF-SEG-01 — Armazenamento sem cofre.** Original, texto extraído, trechos de evidência, nomes de
partes e mensagens do chat são gravados sem cifra da aplicação no banco e no armazenamento de
objetos. O sistema não depende de cofre de chaves para gravar, ler ou descartar um processo
(decisão 40).

- Dado um processo enviado com o sistema recém-iniciado, sem nenhum passo de destravamento, então
  o processo é criado e lido sem erro.
- Dado um processo enviado, quando o banco e o armazenamento de objetos são lidos diretamente,
  então o texto extraído e o original aparecem como foram gravados, sem envelope de cifra.
- Dado o descarte de um processo, então os satélites de conteúdo e os objetos do processo são
  apagados e o evento de auditoria tem como objeto o id do processo.

**RF-SEG-02 — Removido.** Sem cofre, não há chave indisponível; a rota de saúde verifica só a
API, o banco e o armazenamento de objetos (decisão 41).

**RF-SEG-03 — Tráfego.** Todo tráfego entre navegador e servidor usa HTTPS com cabeçalhos de
segurança.

- Dada a página inicial, quando os cabeçalhos são conferidos, então a política de conteúdo, o
  HSTS e os demais cabeçalhos exigidos estão presentes.

**RF-SEG-04 — Saída de rede.** Só o componente que chama o modelo de linguagem tem saída para a
internet. A pipeline não tem.

- Dado o serviço da pipeline, quando tenta abrir conexão externa, então falha.

**RF-SEG-05 — Sem treinamento.** Nenhum dado de autos é usado para treinar ou ajustar modelo.

### 4.11 Documentação (DOC)

**RF-DOC-01 — Guias.** Guia do assessor e guia do desembargador atualizados para a 0.2: o que a
ferramenta faz e não faz, como ler um achado e refazer a conta, como conferir uma citação,
limites do chat, o que a auditoria registra.

**RF-DOC-02 — Conformidade.** As minutas de `docs/conformidade/CONFORMIDADE.md` são revistas para
o que a 0.2 muda: fim da pseudonimização, aceitação de processo sigiloso, gabinete único e fim do
backup.

**RF-DOC-03 — Documentos de sistema.** `docs/arquitetura.md` e `docs/sistema/` descrevem a 0.2
como construída.

**RF-DOC-04 — Estrutura da documentação.** A raiz de `docs/` contém só `README.md`,
`arquitetura.md` e oito pastas: `especificacao/` (apenas `0.2/`), `sistema/`, `decisoes/` (ADRs em
`decisoes/adr/`), `operacao/` (runbooks em `operacao/runbooks/`), `planos/`, `relatorios/`,
`guias/` (capturas de tela, quando geradas, em `guias/imagens/`) e `conformidade/`. Análise,
dívida técnica, incidente e pesquisa de contexto ficam em `relatorios/`, sem subpasta, com o nome
`AAAA-MM-DD-<tipo>-<tema>` e tipo `analise`, `divida`, `incidente` ou `contexto`. Documentos da
0.1 não ficam no repositório.

- Dada a raiz de `docs/`, quando se listam suas entradas, então são exatamente os dois arquivos e
  as oito pastas acima.
- Dado um arquivo em `docs/relatorios/`, quando se lê o nome, então ele segue
  `AAAA-MM-DD-<tipo>-<tema>` com um dos quatro tipos.
- Dado um link relativo em qualquer arquivo `.md` versionado, quando o caminho é resolvido, então
  o arquivo existe.
- Dado qualquer arquivo versionado, quando se procuram os caminhos `docs/adr/`, `docs/runbooks/`,
  `docs/etapas/`, `docs/contexto/`, `docs/imagens/`, `docs/dividas/`, `docs/analises/` e
  `docs/incidentes/`, então nenhum é citado.

### 4.12 Interface (INT)

Aprovada em 19/11/2026 (decisões 46 a 53): o front SvelteKit de `intranet/web/` é substituído por um front Django
com templates renderizados no servidor, que consome a API FastAPI de `intranet/api/` sem
alterá-la. Altera RES-06, RES-12, RNF-08, RNF-09 e a decisão 17.

**RF-INT-01 — Front renderizado no servidor.** Toda tela da intranet é uma página
HTML gerada pelo Django, que obtém os dados chamando a API existente; o navegador não chama
`/api` diretamente.

- Dado um usuário com sessão válida, quando abre a lista de processos, então recebe a página já
  com os processos sintéticos, e a API registra a chamada feita pelo front.
- Dado o tráfego do navegador nessa tela, quando se listam as requisições, então nenhuma vai para
  `/api`.

**RF-INT-02 — Paridade de telas.** O front Django oferece as mesmas telas e ações da
0.2: login com TOTP, troca de senha, lista e cadastro de processo, processo, dossiê, validações,
visualizador, chat, auditoria e gestão de assessores.

- Dada cada tela listada, quando o usuário do papel permitido a abre, então vê o mesmo conteúdo
  que a API devolve para ele.
- Dado um assessor, quando abre auditoria ou gestão de assessores, então recebe a página de
  acesso negado, refletindo o 403 da API.

**RF-INT-03 — Sessão e permissões só na API.** O Django não tem usuários, senhas nem
papéis próprios: repassa a sessão da API e mostra o que ela permite.

- Dada uma sessão expirada na API, quando o usuário navega, então é levado ao login.
- Dado um formulário enviado sem token CSRF válido, quando chega ao Django, então é recusado sem
  chamar a API.

**RF-INT-04 — Envio e progresso de ingestão.** O cadastro por PDF ou ZIP e o
acompanhamento do estado (RF-PRO-01, RF-ING-06) funcionam no front Django.

- Dado um PDF sintético sem classe legível, quando é enviado, então a página pede a classe e o
  reenvio reaproveita o mesmo arquivo.

**RF-INT-05 — Rótulos e citações.** O chat e o dossiê no front Django mantêm o
rótulo de IA (RF-CHA-04), "sem evidência" (RF-CHA-03) e o link da evidência para a página do
arquivo.

- Dada uma resposta com citação conferida, quando aparece, então está em bloco rotulado como
  gerado por IA e o link abre a página citada.

Alterações aprovadas em requisitos e restrições existentes (já aplicadas nas seções 5 e 6):

- RES-06 passa a ser: "A interface é um front Django com templates, em `intranet/web/`, que
  consome a API de `intranet/api/`."
- RES-12 passa a ser: "Três pacotes Python: `lupa_pipeline` em `pipeline/`; `lupa_api` em
  `intranet/api/`, que depende do primeiro (antes `lupa_intranet`); e `lupa_web` em
  `intranet/web/`, o front Django, que só fala com `lupa_api` por HTTP e não importa nenhum dos
  outros dois."
- RNF-08: o trecho do front passa a valer para o Python do front Django (ruff, mypy, cobertura
  de 90%) e para os templates.
- RNF-09: a suíte de navegador, em `pytest-playwright`, roda contra o front Django e gera as
  capturas dos guias.

Perguntas e respostas:

- Q1. Renderização do chat — respondida em 19/11/2026: HTMX troca só o bloco da resposta,
  devolvido pelo Django como fragmento de template.
- Q2. Interatividade das demais telas (progresso do envio, visualizador de página) — respondida
  em 19/11/2026: HTMX, como no chat.
- Q3. Onde fica a sessão — respondida em 19/11/2026: o Django repassa o cookie de sessão da API,
  que fica no navegador, em cada chamada e devolve ao navegador o que a API renovar ou apagar;
  o Django não guarda sessão própria.
- Q4. Pacote Python — respondida em 19/11/2026: novo pacote `lupa_web` em `intranet/web/`, e
  `lupa_intranet` passa a se chamar `lupa_api` (RES-12).
- Q5. Banco do Django — respondida em 19/11/2026: nenhum; `lupa_web` não tem models, migrations
  nem acesso ao PostgreSQL.
- Q6. Transição — respondida em 19/11/2026: troca de uma vez; o SvelteKit sai no mesmo plano.
- Q7. Testes de navegador — respondida em 19/11/2026: a suíte é mantida, reescrita em
  `pytest-playwright` dentro de `lupa_web`, e as capturas dos guias são refeitas a partir dela.
- Q8. Visual — respondida em 19/11/2026: o front Django reproduz o layout atual.

### 4.13 Padrão visual (VIS)

Aprovada em 20/11/2026 (decisões 54 a 58). Define um padrão visual único para o front
Django (`lupa_web`), com paleta e tipografia novas, e leva todas as telas atuais a ele. Altera a
decisão 53 ("reproduz o layout atual"): a estrutura das telas e as ações de RF-INT-02 continuam;
cores, fontes e componentes passam a seguir este padrão.

**RF-VIS-01 — Tokens únicos.** Cores, tipografia, espaçamento e raio vêm de um único conjunto de
tokens com tema claro e escuro; nenhuma folha de estilo de tela declara cor ou fonte literal.

- Dada qualquer folha de estilo de `lupa_web` além da de tokens, quando é inspecionada, então não
  contém valor de cor nem nome de fonte literal, só referência a token.
- Dado o tema escuro escolhido, quando o usuário abre qualquer tela, então todas as cores vêm da
  versão escura dos mesmos tokens.

**RF-VIS-02 — Paleta e tipografia.** A cor primária é verde (`#00613b` no claro, `#4cc489` no
escuro) sobre fundo branco; títulos (h1 a h3) em Source Serif 4, texto em Source Sans 3 e
monoespaçada em Source Code Pro, servidas pelo próprio front; todo par de texto e fundo dos tokens atinge contraste WCAG AA.

- Dado o conjunto de tokens, quando o teste de contraste calcula cada par texto/fundo declarado,
  então todos atingem ao menos 4,5:1 (texto normal) nos dois temas, e borda de campo, foco e
  tarja atingem ao menos 3:1 sobre o fundo (WCAG 1.4.11).
- Dada qualquer tela, quando carregada, então as fontes vêm da própria origem, sem requisição a
  domínio externo, e a CSP continua `font-src 'self'`.

**RF-VIS-03 — Selo de resultado.** Resultados de validação e de conferência (sucesso, atenção,
falha) aparecem num selo com tarja lateral colorida sobre fundo claro do mesmo tom, formato que
nenhum botão, link ou título usa; o selo traz o texto do resultado, não só a cor.

- Dada uma validação sintética tempestiva, quando a tela de validações é aberta, então o resultado
  aparece no selo de sucesso, com a palavra do resultado visível.
- Dadas validações com resultado de atenção e de falha, quando exibidas, então cada uma usa o selo
  do seu tom, distinto do botão primário.

**RF-VIS-04 — Catálogo de componentes.** Botão, aviso, tabela rolável, formulário, ação em
`<details>`, paginação, estado vazio, badge de status, cartão, barra de progresso e o selo de
RF-VIS-03 são templates reutilizáveis; toda tela os usa em vez de marcação própria equivalente.

- Dada qualquer tela de RF-INT-02, quando renderizada, então cada botão, aviso, tabela e
  formulário vem do template do componente correspondente.
- Dado um processo em ingestão, quando listado, então o estado aparece no badge de status, pílula
  neutra distinta do selo de resultado; o badge serve só a estados de fluxo (ingestão, conversa,
  papel).
- Dada uma tabela larga a 375 px, quando a página é aberta, então só a tabela rola na horizontal.

**RF-VIS-05 — Página do padrão.** Existe uma página `/padrao` que mostra todos os componentes de
RF-VIS-04 com dados sintéticos, disponível só com `LUPA_AMBIENTE=desenvolvimento`.

- Dado `LUPA_AMBIENTE=desenvolvimento`, quando um usuário logado abre `/padrao`, então vê cada
  componente do catálogo.
- Dado `LUPA_AMBIENTE` diferente de desenvolvimento, quando qualquer pessoa abre `/padrao`, então
  recebe 404.

**RF-VIS-06 — Acessibilidade verificada.** A suíte de navegador roda o axe em toda tela e na
`/padrao`, nos temas claro e escuro, e falha em qualquer violação, inclusive as de boas práticas;
a `/padrao` também gera capturas em claro, escuro e 375 px, e as capturas dos guias em
`docs/imagens/` são regeradas com o visual novo.

- Dada uma tela com um campo sem rótulo, quando a suíte roda, então o teste dessa tela falha
  citando a regra do axe.
- Dada a suíte verde, quando termina, então existem as capturas da `/padrao` nos três formatos.

Alterações propostas em requisitos e decisões existentes:

- Decisão 53 passa a ser: "Mesma estrutura de telas e ações; visual conforme a seção 4.13."
- RNF-09: a suíte de navegador também roda o axe sem tolerância a violações (RF-VIS-06).

Documentação: `docs/sistema/padrao-visual.md` descreve os tokens e cada componente.

Perguntas e respostas:

- Q1. Fonte monoespaçada — respondida em 20/11/2026: servida pelo projeto (Source Code Pro).
- Q2. Serifa — respondida em 20/11/2026: só nos títulos (h1 a h3).
- Q3. Badge e selo — respondida em 20/11/2026: badge só para estados de fluxo, em pílula neutra.
- Q4. Capturas dos guias — respondida em 20/11/2026: regeradas no mesmo plano.
- Q5. Contraste não textual — respondida em 20/11/2026: o teste de tokens exige 3:1.

## 5. Requisitos não funcionais

| Id | Requisito | Critério |
| --- | --- | --- |
| RNF-01 | Evidência | zero fato sem evidência no banco, medido na suíte de regressão |
| RNF-02 | Precisão | datas extraídas com precisão de 99% ou mais nos sintéticos com gabarito; índice de peças dentro da meta que o plano fixar a partir da medição da 0.1 |
| RNF-03 | Injeção | zero achado criado ou suprimido e zero instrução seguida pelo chat no corpus de injeção |
| RNF-04 | Regressão | suíte com sintéticos de cada classe (3.1), corpus de injeção e casos de recusa roda antes de toda entrega; troca de modelo ou de prompt exige rodá-la |
| RNF-05 | Dados de teste | todo teste usa dado sintético; nenhum teste lê `dados/` |
| RNF-06 | Execução | tudo roda em contêineres, num único host, sem dependência instalada na máquina do desenvolvedor |
| RNF-07 | Segredos | só em arquivo ignorado pelo git; nunca em código ou imagem |
| RNF-08 | Qualidade | lint, formatação, tipagem estrita e cobertura mínima de 90% no código Python, inclusive no front Django (`lupa_web`) |
| RNF-09 | Ponta a ponta | suíte de navegador em `pytest-playwright`, contra o front Django, cobre login, processos, dossiê, chat, auditoria e gestão de assessores sobre dados sintéticos; as capturas de tela dos guias saem dela |

## 6. Restrições

Vêm do escopo definido pelo usuário; o detalhe é do plano.

| Id | Restrição |
| --- | --- |
| RES-01 | Um único gabinete. Não existe identificador de gabinete nem isolamento por gabinete. |
| RES-02 | Banco modelado em Data Vault 2.0 (hubs, links e satélites), para todas as tabelas, inclusive autenticação, estado da ingestão e auditoria. Chave por hash da chave de negócio; só raw vault; a API lê por views. Correção de fato e de peça é histórico de satélite. |
| RES-03 | Ponto de partida do modelo. Hubs: processo, arquivo, página, peça, evidência, fato, achado, parte, usuário, conversa. Links: processo–arquivo, arquivo–página, arquivo–peça, página–evidência, fato–evidência, processo–fato, processo–achado, achado–fato, processo–parte, processo–usuário responsável, processo–conversa. Satélites: um ou mais por hub, separando descrição de estado; anotação e mensagem como satélites. |
| RES-04 | Tudo do frontend e do back que o atende (API, acesso, auditoria, agente) fica em `intranet/`. "Intranet" é só o nome do diretório; o acesso continua por usuário, senha e TOTP. |
| RES-05 | Tudo da pipeline de dados (worker, ingestão, fatos, validações, modelo e migrations do Data Vault, sintéticos) fica em `pipeline/`. |
| RES-06 | A interface é um front Django com templates, em `intranet/web/`, que consome a API de `intranet/api/` (decisão 46). |
| RES-07 | Um único worker de ingestão, que lê a fila do próprio banco. Sem Redis. |
| RES-08 | Sem cofre de chaves e sem cifra na aplicação; a proteção em repouso é a do host (decisões 40 e 42). |
| RES-09 | O banco da 0.2 nasce vazio, com migration inicial nova. Os processos de `dados/` são enviados de novo, à mão, pela interface da 0.2; correções, anotações, conversas e auditoria da 0.1 não são migradas. |
| RES-11 | A 0.2 é instalada só na máquina de desenvolvimento. Não há servidor do piloto nem perfil de produção. |
| RES-12 | Três pacotes Python: `lupa_pipeline` em `pipeline/`; `lupa_api` em `intranet/api/`, que depende do primeiro (antes `lupa_intranet`); e `lupa_web` em `intranet/web/`, o front Django, que só fala com `lupa_api` por HTTP e não importa nenhum dos outros dois (decisão 49). |
| RES-13 | Tabelas com prefixo `hub_`, `link_` e `sat_`; colunas técnicas `hk_<entidade>`, `load_dts`, `record_source` e `hash_diff`; atributos de negócio em português; hash SHA-256. Toda mudança de estado é linha nova; `UPDATE` e `DELETE` são bloqueados no banco. Única exceção: o descarte apaga as linhas de satélite do processo e a chave, mantendo hubs e links. |
| RES-10 | A 0.2 vive neste repositório, na branch `feat/versao-0.2`, substituindo a estrutura atual. A 0.1 fica preservada na tag `v0.1.0`. |

## 7. Decisões de escopo

Respostas do usuário em 13/11/2026 às decisões levantadas antes desta especificação.

| Nº | Decisão | Resposta |
| --- | --- | --- |
| 1 | Classes processuais | todas: apelação, agravo de instrumento, embargos de declaração, agravo interno e ações originárias |
| 2 | Segredo de justiça | o bloqueio é removido; qualquer processo é aceito |
| 3 | Validações cíveis | tempestividade, preparo, representação e cabimento do agravo |
| 4 | Tipos de peça | lista da seção 3.2 |
| 5 | Pseudonimização | removida |
| 6 | `gabinete_id` e RLS | removidos; mantido o papel de banco só com DML |
| 7 | Papéis | desembargador e assessor; primeiro usuário por comando |
| 8 | Criptografia | cofre com chave única e chave por processo (substituída pelas decisões 40 a 45) |
| 9 | Alcance do Data Vault | todas as tabelas |
| 10 | Composição do Data Vault | RES-03 como ponto de partida |
| 11 | Convenções do Data Vault | RES-02 |
| 12 | Dados da 0.1 | banco vazio e reingestão dos 20 processos de `dados/` |
| 13 | Conteúdo de `pipeline/` | RES-05 |
| 14 | API, acesso, auditoria e agente | em `intranet/` |
| 15 | Fila | worker único lendo o banco, sem Redis |
| 16 | Monitoramento e backup | removidos: Prometheus, Grafana, métricas de serviço, backup, restauração e expurgo |
| 17 | Front | reaproveita o SvelteKit (substituída pelas decisões 46 a 53) |
| 18 | "Intranet" | só o nome do diretório |
| 19 a 21 | Specs | este arquivo; seção de restrições; specs da v1 mantidas e marcadas como substituídas |
| 22 | Repositório | o mesmo, em branch nova |
| 23 | Pacotes Python | RES-12 |
| 24 | Nomes e mutabilidade no Data Vault | RES-13 |
| 25 | Integração | commits diretos em `feat/versao-0.2`, um por tarefa; um PR para `develop` no fim |
| 26 | Ambiente | RES-11 |
| 27 | Reingestão | upload manual pela interface |
| 28 | Itens mantidos da 0.1 | localização por IP, custo estimado, processo em revisão, testes ponta a ponta e capturas |

Respostas do usuário em 15/11/2026 sobre o cadastro pelo arquivo (RF-PRO-01, RF-PRO-06).

| Nº | Decisão | Resposta |
| --- | --- | --- |
| 29 | Dados lidos do arquivo | número CNJ e classe no envio; partes, relator, órgão julgador, assunto, valor da causa, juízo de origem e data de distribuição na ingestão |
| 30 | Momento da identificação | no próprio envio, pela API |
| 31 | Conferência antes de criar | não há; o processo é criado direto |
| 32 | Número ou classe não lidos | o usuário completa o que faltou e o mesmo arquivo é aproveitado |
| 33 | Número já cadastrado | o arquivo é anexado ao processo existente |
| 34 | Cadastro manual sem arquivo | removido |
| 35 | Dados da capa | fatos, com evidência e correção |
| 36 | Classe errada | corrigível pela tela, com histórico |
| 37 | Partes | no cabeçalho do processo e no dossiê; fora da lista |
| 38 | Arquivo que não abre no envio que cria processo | recusado com o motivo |
| 39 | Isolamento da leitura no envio | aceito o subprocesso na API, sem o isolamento de rede do worker |

Respostas do usuário em 15/11/2026 sobre a remoção do Vault (RF-SEG-01, RF-SEG-02). Substituem a
decisão 8.

| Nº | Decisão | Resposta |
| --- | --- | --- |
| 40 | Cofre e cifra | Vault removido; toda a cifra da aplicação removida (banco e objetos) |
| 41 | Cofre indisponível (RF-SEG-02) | requisito removido |
| 42 | Dados gravados com cifra | não migrados; banco, objetos e volume do Vault recriados do zero |
| 43 | Rotação de chave | removida |
| 44 | Identificação interna do nome da parte | SHA-256 do nome normalizado, sem chave |
| 45 | Objeto do evento de descarte | id do processo |

Respostas do usuário em 19/11/2026 sobre o front em Django (seção 4.12). Substituem a decisão 17.

| Nº | Decisão | Resposta |
| --- | --- | --- |
| 46 | Front (RES-06, RF-INT-01 a RF-INT-05) | front Django com templates, em `intranet/web/`, consumindo a API FastAPI sem alterá-la |
| 47 | Interatividade (Q1, Q2) | HTMX no chat, no progresso do envio e no visualizador |
| 48 | Sessão (Q3) | o Django repassa o cookie de sessão da API; sem sessão própria |
| 49 | Pacotes (Q4, RES-12) | `lupa_web` novo em `intranet/web/`; `lupa_intranet` renomeado para `lupa_api` |
| 50 | Banco do Django (Q5) | nenhum: sem models, migrations nem acesso ao PostgreSQL |
| 51 | Transição (Q6) | troca de uma vez; o SvelteKit sai no mesmo plano |
| 52 | Testes de navegador (Q7, RNF-09) | `pytest-playwright` em `lupa_web`; capturas dos guias refeitas pela suíte |
| 53 | Visual (Q8) | reproduz o layout atual |

Respostas do usuário em 20/11/2026 sobre o padrão visual (seção 4.13). Alteram a decisão 53.

| Nº | Decisão | Resposta |
| --- | --- | --- |
| 54 | Padrão visual (RF-VIS-01 a RF-VIS-06) | tokens únicos; verde `#00613b`/`#4cc489` sobre branco; Source Serif 4 nos títulos e Source Sans 3 no texto; selo de resultado com tarja; catálogo de componentes adotado por todas as telas no mesmo plano; `/padrao` só no desenvolvimento; axe sem tolerância |
| 55 | Monoespaçada (Q1) | Source Code Pro servida pelo projeto |
| 56 | Serifa (Q2) | só nos títulos (h1 a h3) |
| 57 | Badge e selo (Q3, Q5) | badge só para estados de fluxo, em pílula neutra; contraste não textual de 3:1 no teste de tokens |
| 58 | Capturas (Q4) e decisão 53 | capturas dos guias regeradas no mesmo plano; a decisão 53 passa a "mesma estrutura de telas e ações; visual conforme a seção 4.13" |

## 8. Removido em relação à 0.1.0

- Vários gabinetes: tabela `gabinete`, `gabinete_id`, RLS por gabinete, tela de gabinetes, papel
  administrador e o destaque de acesso do administrador na auditoria.
- Área criminal: catálogo criminal, validações de tempestividade pelo CPP, prescrição e revisão da
  preventiva, extratores de denúncia, recebimento e prisão, tabelas de réu, tipos penais e
  situação prisional na ficha.
- Pseudonimização de partes e tabela de resolução de identidades.
- Bloqueio de processo sigiloso.
- Redis e fila RQ.
- Prometheus, Grafana e a rota de métricas de serviço.
- Backup cifrado, restauração, expurgo e agendamento.
- Perfil de produção: `docker-compose.prod.yml`, instalação e conferência do piloto, Vault de
  produção e modos de certificado do proxy além do interno.
- Migrations `v0001` a `v0012`.

## 9. Fora de escopo

- Validações semânticas e qualquer validação além das quatro da seção 4.6.
- Conferência do valor do preparo, complementação e recolhimento em dobro.
- Validações para ações originárias.
- Integração com Projudi ou DataJud; sugestão de jurisprudência; redação de atos.
- Migração dos dados da 0.1.
- Mais de um gabinete; outras áreas.

## 10. Riscos aceitos pelas decisões

Consequências das decisões 2, 5, 16 e 40 que o usuário deve ter à vista ao aprovar.

1. **Nomes reais e processos sigilosos vão ao fornecedor do modelo.** Sem pseudonimização e sem
   bloqueio de sigiloso, os trechos enviados ao modelo levam nomes de partes e podem ser de
   processo em segredo de justiça. O [requisitos-v1.md](../requisitos-v1.md) tratava a
   pseudonimização como a proteção desse envio e registrava a anonimização na origem como
   condição para sigilosos com modelo externo (art. 19, § 3º, IV, Res. CNJ 615/2025). A
   conformidade precisa ser revista (RF-DOC-02) antes de processo sigiloso real entrar.
2. **Sem backup, perda do host é perda dos dados.** Os originais continuam em `dados/`, fora do
   sistema; correções, anotações, conversas e auditoria não têm cópia.
3. **Sem monitoramento, falha é percebida pelo usuário.** Não há alerta de fila parada ou disco
   cheio.
4. **A leitura no envio tem isolamento menor que o do worker.** Para criar o processo a partir do
   arquivo (decisões 30 e 39), a API abre as primeiras páginas em subprocesso sem credenciais, com
   rede bloqueada no próprio subprocesso e limites de memória, CPU e tempo. O contêiner da API
   tem saída de rede; o do worker não. Um PDF que explore falha do parser nesse subprocesso não
   encontra a barreira de rede do contêiner.
5. **Autos em claro no host.** Sem cifra da aplicação (decisão 40), quem obtém o volume do
   PostgreSQL ou do MinIO, ou uma cópia deles, lê o texto dos autos, os nomes das partes e as
   conversas. A proteção em repouso passa a depender do disco do host e do controle de acesso a
   ele.

## 11. Regras jurídicas a confirmar pelo gabinete

Os dispositivos foram citados a partir do texto do CPC e precisam de conferência do gabinete
antes de o catálogo valer para processo real, como na 0.1.

1. Marco inicial do prazo em intimação eletrônica (publicação no diário ou ciência no portal) e
   qual deles o Projudi registra na certidão.
2. Calendário oficial de feriados e suspensões do TJGO.
3. Preparo no agravo interno e nos embargos de declaração conforme o regimento do TJGO; a tabela
   3.1 assume preparo no agravo interno e nenhum nos embargos.
4. Outras hipóteses de dispensa de procuração (advogado em causa própria, núcleo de prática
   jurídica, curador especial).
5. Correspondência entre padrões de decisão e incisos do art. 1.015 usada no RF-VAL-05.
