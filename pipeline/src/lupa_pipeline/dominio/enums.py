"""Enumerações do domínio jurídico do Lupa."""

from enum import StrEnum


class StatusProcesso(StrEnum):
    """Situação do processo dentro do Lupa.

    Attributes:
        CRIADO: Cadastrado, sem arquivos processados.
        EM_INGESTAO: Arquivos sendo processados.
        PRONTO: Fatos extraídos e validações disponíveis.
        ARQUIVADO: Fora de uso; mantido para auditoria.
        EM_REVISAO: Incidente de injeção no agente; o chat fica bloqueado até o desembargador
            liberar (RF-CHA-08).
        DESCARTADO: Exclusão criptográfica (Etapa 7.7): DEK apagada, só resta o registro.
    """

    CRIADO = "criado"
    EM_INGESTAO = "em_ingestao"
    PRONTO = "pronto"
    ARQUIVADO = "arquivado"
    EM_REVISAO = "em_revisao"
    DESCARTADO = "descartado"


class TipoPeca(StrEnum):
    """Peças processuais cíveis conforme a seção 3.2 da especificação."""

    PETICAO_INICIAL = "peticao_inicial"
    CONTESTACAO = "contestacao"
    REPLICA = "replica"
    DECISAO_INTERLOCUTORIA = "decisao_interlocutoria"
    SENTENCA = "sentenca"
    EMBARGOS_DECLARACAO = "embargos_declaracao"
    APELACAO = "apelacao"
    AGRAVO_INSTRUMENTO = "agravo_instrumento"
    AGRAVO_INTERNO = "agravo_interno"
    CONTRARRAZOES = "contrarrazoes"
    ACORDAO = "acordao"
    CERTIDAO = "certidao"
    PROCURACAO = "procuracao"
    COMPROVANTE_PREPARO = "comprovante_preparo"
    LAUDO_PERICIAL = "laudo_pericial"
    PARECER_MP = "parecer_mp"
    OUTROS = "outros"


class MetodoClassificacao(StrEnum):
    """Método utilizado na classificação vigente da peça."""

    REGRA = "regra"
    MANUAL = "manual"


class OrigemPeca(StrEnum):
    """Origem identificada da peça processual."""

    JUIZO = "juizo"
    MP = "mp"
    PARTE = "parte"
    TERCEIRO = "terceiro"
    DESCONHECIDA = "desconhecida"


class TipoPagina(StrEnum):
    """Origem do texto da página.

    Attributes:
        NATIVA: Texto extraído da camada de texto do PDF.
        OCR: Texto obtido por reconhecimento óptico.
        VAZIA: Página sem texto.
    """

    NATIVA = "nativa"
    OCR = "ocr"
    VAZIA = "vazia"


class FlagPagina(StrEnum):
    """Marcadores de ingestão definidos em `docs/especificacao/prompt-injection.md`.

    Attributes:
        TEXTO_OCULTO: Texto invisível (cor, tamanho ou posição).
        BLOCO_CODIFICADO: Bloco em base64 ou codificação semelhante.
        PADRAO_INSTRUCAO: Texto com forma de instrução a um modelo.
        IDIOMA_INESPERADO: Trecho em idioma diferente do esperado.
        TEXTO_DIVERGENTE: Camada de texto diverge do que o OCR lê na imagem da página.
        METADADO_SUSPEITO: Metadado, anotação ou campo do PDF com padrão de instrução.
        HOMOGLIFOS: Texto com caracteres de outros alfabetos trocados pelo latino.
        DENSIDADE_ANOMALA: Volume de texto muito acima do padrão do tipo de página.
    """

    TEXTO_OCULTO = "texto_oculto"
    BLOCO_CODIFICADO = "bloco_codificado"
    PADRAO_INSTRUCAO = "padrao_instrucao"
    IDIOMA_INESPERADO = "idioma_inesperado"
    TEXTO_DIVERGENTE = "texto_divergente"
    METADADO_SUSPEITO = "metadado_suspeito"
    HOMOGLIFOS = "homoglifos"
    DENSIDADE_ANOMALA = "densidade_anomala"


class TipoFato(StrEnum):
    """Fatos jurídicos cíveis extraídos com evidência de página."""

    DATA_DECISAO_RECORRIDA = "data_decisao_recorrida"
    DATA_INTIMACAO = "data_intimacao"
    TIPO_RECURSO = "tipo_recurso"
    DATA_INTERPOSICAO = "data_interposicao"
    QUALIDADE_RECORRENTE = "qualidade_recorrente"
    COMPROVANTE_PREPARO = "comprovante_preparo"
    GRATUIDADE_PEDIDO = "gratuidade_pedido"
    GRATUIDADE_DECISAO = "gratuidade_decisao"
    ADVOGADO_SUBSCRITOR = "advogado_subscritor"
    PROCURACAO = "procuracao"
    HIPOTESE_DECISAO_AGRAVADA = "hipotese_decisao_agravada"
    DATA_AJUIZAMENTO = "data_ajuizamento"
    DATA_CITACAO = "data_citacao"
    DATA_CONTESTACAO = "data_contestacao"
    DATA_ACORDAO = "data_acordao"


class StatusFato(StrEnum):
    """Estado de revisão humana de um fato.

    Attributes:
        AUTOMATICO: Extraído pelo sistema, sem revisão.
        CONFIRMADO: Conferido e mantido por pessoa.
        CORRIGIDO: Novo fato que substitui outro após correção humana.
    """

    AUTOMATICO = "automatico"
    CONFIRMADO = "confirmado"
    CORRIGIDO = "corrigido"


class ResultadoAchado(StrEnum):
    """Resultado de uma validação.

    Attributes:
        CONFORME: A regra foi atendida.
        ATENCAO: A regra indica problema (por exemplo, intempestivo ou prescrito).
        VERIFICAR: Faltam fatos ou há conflito; exige conferência humana.
    """

    CONFORME = "conforme"
    ATENCAO = "atencao"
    VERIFICAR = "verificar"


class PapelUsuario(StrEnum):
    """Papel de acesso (RF-ACE-03).

    Attributes:
        ASSESSOR: Vê todos os processos e trabalha neles.
        DESEMBARGADOR: Assessor mais auditoria, relatório de uso e gestão de assessores.
    """

    ASSESSOR = "assessor"
    DESEMBARGADOR = "desembargador"


class ClasseProcessual(StrEnum):
    """Classe processual do processo (seção 3.1 da especificação).

    Attributes:
        APELACAO_CIVEL: Apelação cível.
        AGRAVO_INSTRUMENTO: Agravo de instrumento.
        EMBARGOS_DECLARACAO: Embargos de declaração.
        AGRAVO_INTERNO: Agravo interno.
        ACAO_ORIGINARIA: Ação originária (rescisória, mandado de segurança e demais).
    """

    APELACAO_CIVEL = "apelacao_civel"
    AGRAVO_INSTRUMENTO = "agravo_instrumento"
    EMBARGOS_DECLARACAO = "embargos_declaracao"
    AGRAVO_INTERNO = "agravo_interno"
    ACAO_ORIGINARIA = "acao_originaria"


class Polo(StrEnum):
    """Polo da parte no processo (RF-FAT-04).

    Attributes:
        ATIVO: Autor, apelante, agravante, embargante.
        PASSIVO: Réu, apelado, agravado, embargado.
        TERCEIRO: Terceiro interessado.
    """

    ATIVO = "ativo"
    PASSIVO = "passivo"
    TERCEIRO = "terceiro"


class QualidadeParte(StrEnum):
    """Qualidade da parte que decide prazo em dobro e dispensas (RF-FAT-01).

    Attributes:
        FAZENDA_PUBLICA: Fazenda Pública.
        MINISTERIO_PUBLICO: Ministério Público.
        DEFENSORIA_PUBLICA: Defensoria Pública.
        PARTICULAR: Demais partes.
    """

    FAZENDA_PUBLICA = "fazenda_publica"
    MINISTERIO_PUBLICO = "ministerio_publico"
    DEFENSORIA_PUBLICA = "defensoria_publica"
    PARTICULAR = "particular"


class EstadoJob(StrEnum):
    """Estado de um job de ingestão; transições válidas em `lupa_pipeline.ingestao.estados`.

    Attributes:
        RECEBIDO: Arquivo lacrado e gravado no storage; aguardando validação.
        VALIDADO: Estrutura conferida (tipo, integridade, inventário); pronto para extração.
        EM_EXTRACAO: Páginas sendo extraídas.
        PARCIAL: Extração interrompida com parte das páginas gravadas.
        EM_REVISAO: Extração concluída com pendências para o assessor.
        CONCLUIDO: Ingestão terminada; estado final.
        FALHO: Erro de processamento (limite de recurso, erro interno); pode ser refeito.
        QUARENTENA: Arquivo recusado por motivo enumerado; estado final, nada avança.
    """

    RECEBIDO = "recebido"
    VALIDADO = "validado"
    EM_EXTRACAO = "em_extracao"
    PARCIAL = "parcial"
    EM_REVISAO = "em_revisao"
    CONCLUIDO = "concluido"
    FALHO = "falho"
    QUARENTENA = "quarentena"


class MotivoQuarentena(StrEnum):
    """Motivo pelo qual um arquivo foi posto em quarentena.

    Attributes:
        CORROMPIDO: Estrutura ilegível (PDF que não abre, ZIP com CRC errado).
        SENHA: Arquivo ou entrada protegido por senha.
        TRUNCADO: PDF sem o marcador final `%%EOF`.
        ASSINATURA_INVALIDA: `/ByteRange` de assinatura que não cobre o arquivo inteiro.
        TIPO_INVALIDO: Conteúdo que não é PDF (ou entrada de ZIP que não é PDF).
        ZIP_MALICIOSO: Caminho perigoso, link simbólico ou limites de ZIP excedidos.
    """

    CORROMPIDO = "corrompido"
    SENHA = "senha"
    TRUNCADO = "truncado"
    ASSINATURA_INVALIDA = "assinatura_invalida"
    TIPO_INVALIDO = "tipo_invalido"
    ZIP_MALICIOSO = "zip_malicioso"


class MotivoFalha(StrEnum):
    """Motivo de um job `falho`.

    Attributes:
        LIMITE_MEMORIA: O parser excedeu o limite de memória do sandbox.
        LIMITE_CPU: O parser excedeu o limite de CPU do sandbox.
        TEMPO_ESGOTADO: O parser excedeu o tempo de parede do sandbox.
        ERRO_PARSER: O parser terminou com erro ou saída ilegível.
        ARQUIVO_AUSENTE: O objeto não está no storage.
        ERRO_INTERNO: Erro inesperado do worker.
    """

    LIMITE_MEMORIA = "limite_memoria"
    LIMITE_CPU = "limite_cpu"
    TEMPO_ESGOTADO = "tempo_esgotado"
    ERRO_PARSER = "erro_parser"
    ARQUIVO_AUSENTE = "arquivo_ausente"
    ERRO_INTERNO = "erro_interno"


class CenarioArquivo(StrEnum):
    """Cenário de empacotamento diagnosticado (preenchido pela Etapa 4C).

    Attributes:
        ZIP_POR_PECA: ZIP com um PDF por peça.
        PDF_COM_BOOKMARKS: PDF único com bookmarks.
        PDF_COM_INDICE: PDF único com índice de movimentações no texto.
        PDF_LISO: PDF único sem bookmarks nem índice.
        PDF_COM_BOOKMARKS_E_INDICE: PDF único com bookmarks e índice de movimentações.
    """

    ZIP_POR_PECA = "zip_por_peca"
    PDF_COM_BOOKMARKS = "pdf_com_bookmarks"
    PDF_COM_INDICE = "pdf_com_indice"
    PDF_LISO = "pdf_liso"
    PDF_COM_BOOKMARKS_E_INDICE = "pdf_com_bookmarks_e_indice"


class EstadoLote(StrEnum):
    """Estado de um lote de trabalho de um job.

    Attributes:
        CONCLUIDO: Resultado gravado.
        FALHO: O lote terminou com falha registrada.
    """

    CONCLUIDO = "concluido"
    FALHO = "falho"


class PapelMensagem(StrEnum):
    """Autor de uma mensagem do chat (Etapa 5).

    Attributes:
        USUARIO: Pergunta do assessor.
        AGENTE: Resposta do agente (ou recusa, ou aviso de teto).
    """

    USUARIO = "usuario"
    AGENTE = "agente"


class StatusMensagem(StrEnum):
    """Desfecho de uma mensagem do chat (Etapa 5).

    Attributes:
        PERGUNTA: Pergunta registrada.
        RESPONDIDA: Resposta com ao menos uma citação conferida.
        SEM_EVIDENCIA: Resposta sem nenhuma citação válida (exibida com aviso).
        RECUSA: Pergunta fora do escopo; o agente explica o limite.
        DESCARTADA: Saída do modelo descartada (esquema, instrução refletida, outro processo).
        TETO: Teto de tokens atingido; a conversa foi encerrada.
    """

    PERGUNTA = "pergunta"
    RESPONDIDA = "respondida"
    SEM_EVIDENCIA = "sem_evidencia"
    RECUSA = "recusa"
    DESCARTADA = "descartada"
    TETO = "teto"


class ResultadoChamada(StrEnum):
    """Desfecho de uma chamada ao modelo (Etapa 5).

    Attributes:
        OK: Saída válida.
        INVALIDA: Saída fora do esquema.
        BLOQUEADA: Saída descartada por instrução refletida ou dado de outro processo.
        TETO: Chamada acima do teto de tokens por chamada.
        ERRO: Falha do cliente ou da API.
    """

    OK = "ok"
    INVALIDA = "invalida"
    BLOQUEADA = "bloqueada"
    TETO = "teto"
    ERRO = "erro"
