"""Mapeamento somente leitura das views `v_*` do Data Vault (D13).

A API e os repositórios leem por estas classes; gravar é só por `dominio.gravacao`. Os metadados
ficam separados de `dominio.tabelas.metadata`, para o autogenerate não tomar as views por
tabelas. Use `atual` ao reler uma view depois de gravar na mesma transação. Colunas de JSON
guardadas em `TEXT` usam `JsonTexto`, como no satélite de origem. `id` é o hex do
`hk` (D12). Qualquer tentativa de gravar uma view levanta `VisaoSomenteLeituraError`.
"""

from datetime import date, datetime
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import ARRAY, DateTime, MetaData, Select, Text, event
from sqlalchemy.dialects.postgresql import BYTEA, JSONB
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Mapped, Mapper, mapped_column

from lupa_pipeline.dominio.tipos import JsonTexto

Instante = DateTime(timezone=True)
T = TypeVar("T")


class VisaoSomenteLeituraError(RuntimeError):
    """Tentativa de inserir, alterar ou apagar por uma view."""


class BaseVisao(DeclarativeBase):
    """Base das views; metadados próprios, fora do Data Vault."""

    metadata = MetaData()
    type_annotation_map = {bytes: BYTEA, datetime: Instante, dict[str, Any]: JSONB}


@event.listens_for(BaseVisao, "before_insert", propagate=True)
@event.listens_for(BaseVisao, "before_update", propagate=True)
@event.listens_for(BaseVisao, "before_delete", propagate=True)
def _recusar_gravacao(_mapper: Mapper[Any], _conexao: Connection, alvo: Any) -> None:
    """Recusa gravar por uma view.

    Raises:
        VisaoSomenteLeituraError: Sempre.
    """
    raise VisaoSomenteLeituraError(type(alvo).__tablename__)


def atual(consulta: Select[tuple[T]]) -> Select[tuple[T]]:
    """Marca a consulta para reler do banco os objetos que a sessão já carregou.

    A view muda quando um satélite ganha linha nova na mesma transação; sem isto, o mapa de
    identidade da sessão devolveria a linha lida antes.

    Args:
        consulta: Consulta sobre uma view.

    Returns:
        A mesma consulta com `populate_existing`.
    """
    return consulta.execution_options(populate_existing=True)


def _hk() -> Mapped[bytes]:
    return mapped_column(BYTEA, primary_key=True)


class VisaoUsuario(BaseVisao):
    """`v_usuario`: cadastro e credencial correntes."""

    __tablename__ = "v_usuario"

    hk_usuario: Mapped[bytes] = _hk()
    id: Mapped[str]
    nome_usuario: Mapped[str]
    criado_em: Mapped[datetime]
    papel: Mapped[str | None]
    ativo: Mapped[bool | None]
    senha_hash: Mapped[str | None]
    troca_senha_obrigatoria: Mapped[bool | None]
    mfa_segredo: Mapped[str | None]
    mfa_confirmado: Mapped[bool | None]
    mfa_ultimo_passo: Mapped[int | None]


class VisaoProcesso(BaseVisao):
    """`v_processo`: dados, estado, chave e revisão correntes."""

    __tablename__ = "v_processo"

    hk_processo: Mapped[bytes] = _hk()
    id: Mapped[str]
    numero_cnj: Mapped[str]
    criado_em: Mapped[datetime]
    classe: Mapped[str | None]
    hk_criador: Mapped[bytes | None]
    criador_id: Mapped[str | None]
    classe_anterior: Mapped[str | None]
    hk_classe_corrigida_por: Mapped[bytes | None]
    classe_corrigida_por_id: Mapped[str | None]
    classe_corrigida_em: Mapped[datetime | None]
    status: Mapped[str | None]
    em_revisao: Mapped[bool]
    motivo_revisao: Mapped[str | None]
    status_anterior_revisao: Mapped[str | None]
    revisao_em: Mapped[datetime | None]


class VisaoArquivo(BaseVisao):
    """`v_arquivo`: dados, estado da ingestão e diagnóstico correntes."""

    __tablename__ = "v_arquivo"

    hk_arquivo: Mapped[bytes] = _hk()
    id: Mapped[str]
    numero_cnj: Mapped[str]
    sha256: Mapped[str]
    criado_em: Mapped[datetime]
    hk_processo: Mapped[bytes]
    processo_id: Mapped[str]
    tamanho_bytes: Mapped[int | None]
    nome_original: Mapped[str | None] = mapped_column(Text)
    mime: Mapped[str | None]
    chave_storage: Mapped[str | None]
    hk_enviado_por: Mapped[bytes | None]
    estado: Mapped[str | None]
    motivo_quarentena: Mapped[str | None]
    motivo_falha: Mapped[str | None]
    tentativas: Mapped[int | None]
    total_paginas: Mapped[int | None]
    manifesto: Mapped[Any] = mapped_column(JSONB)
    relatorio: Mapped[Any] = mapped_column(JSONB)
    versao_extrator: Mapped[str | None]
    estado_em: Mapped[datetime | None]
    cenario: Mapped[str | None]
    total_paginas_diagnostico: Mapped[int | None]
    tem_indice: Mapped[bool | None]
    sinais: Mapped[Any] = mapped_column(JSONB)
    fronteiras_origem: Mapped[Any] = mapped_column(JSONB)
    metadados_descartados: Mapped[Any] = mapped_column(JSONB)


class VisaoPagina(BaseVisao):
    """`v_pagina`: extração, saneamento e sinais de fronteira correntes."""

    __tablename__ = "v_pagina"

    hk_pagina: Mapped[bytes] = _hk()
    id: Mapped[str]
    numero_cnj: Mapped[str]
    sha256: Mapped[str]
    numero: Mapped[int]
    hk_arquivo: Mapped[bytes]
    arquivo_id: Mapped[str]
    hk_processo: Mapped[bytes]
    processo_id: Mapped[str]
    tipo: Mapped[str | None]
    texto: Mapped[str | None] = mapped_column(Text)
    hash_texto: Mapped[str | None]
    texto_nativo: Mapped[str | None] = mapped_column(Text)
    texto_ocr: Mapped[str | None] = mapped_column(Text)
    coordenadas: Mapped[Any] = mapped_column(JSONB)
    sinais: Mapped[Any] = mapped_column(JSONB)
    extracao: Mapped[Any] = mapped_column(JSONB)
    versao_extrator: Mapped[str | None]
    origem_arquivo: Mapped[str | None]
    pagina_origem: Mapped[int | None]
    extraida_em: Mapped[datetime | None]
    texto_normalizado: Mapped[str | None] = mapped_column(Text)
    flags: Mapped[Any] = mapped_column(JSONB)
    trechos_ocultos: Mapped[Any] = mapped_column(JsonTexto)
    trechos_suspeitos: Mapped[Any] = mapped_column(JsonTexto)
    sinais_fronteira: Mapped[Any] = mapped_column(JSONB)


class VisaoPeca(BaseVisao):
    """`v_peca`: classificação corrente da peça."""

    __tablename__ = "v_peca"

    hk_peca: Mapped[bytes] = _hk()
    id: Mapped[str]
    numero_cnj: Mapped[str]
    sha256: Mapped[str]
    pagina_inicial: Mapped[int]
    hk_arquivo: Mapped[bytes]
    arquivo_id: Mapped[str]
    hk_processo: Mapped[bytes]
    processo_id: Mapped[str]
    tipo: Mapped[str | None]
    pagina_final: Mapped[int | None]
    confianca: Mapped[float | None]
    metodo: Mapped[str | None]
    origem: Mapped[str | None]
    data: Mapped[date | None]
    tipo_data: Mapped[str | None]
    hk_evidencia_data: Mapped[bytes | None]
    flags: Mapped[Any] = mapped_column(JSONB)
    classificacao: Mapped[Any] = mapped_column(JSONB)
    vigente: Mapped[bool | None]
    hk_usuario: Mapped[bytes | None]
    classificada_em: Mapped[datetime | None]


class VisaoEvidencia(BaseVisao):
    """`v_evidencia`: trecho corrente da evidência."""

    __tablename__ = "v_evidencia"

    hk_evidencia: Mapped[bytes] = _hk()
    id: Mapped[str]
    numero_cnj: Mapped[str]
    sha256: Mapped[str]
    numero: Mapped[int]
    inicio: Mapped[int]
    fim: Mapped[int]
    hk_pagina: Mapped[bytes]
    pagina_id: Mapped[str]
    hk_processo: Mapped[bytes]
    processo_id: Mapped[str]
    trecho: Mapped[str | None] = mapped_column(Text)
    hash_trecho: Mapped[str | None]
    bbox: Mapped[Any] = mapped_column(JSONB)


class VisaoFato(BaseVisao):
    """`v_fato`: valor corrente do fato e se tem evidência vigente."""

    __tablename__ = "v_fato"

    hk_fato: Mapped[bytes] = _hk()
    id: Mapped[str]
    numero_cnj: Mapped[str]
    tipo: Mapped[str]
    sujeito: Mapped[str]
    hk_evidencia_origem: Mapped[bytes]
    evidencias_vigentes: Mapped[list[bytes]] = mapped_column(ARRAY(BYTEA))
    hk_processo: Mapped[bytes]
    processo_id: Mapped[str]
    valor: Mapped[Any] = mapped_column(JsonTexto)
    extraido_por: Mapped[str | None]
    versao_extrator: Mapped[str | None]
    confianca: Mapped[float | None]
    status: Mapped[str | None]
    hk_usuario: Mapped[bytes | None]
    atualizado_em: Mapped[datetime | None]
    vigente: Mapped[bool]


class VisaoAchado(BaseVisao):
    """`v_achado`: resultado corrente do achado."""

    __tablename__ = "v_achado"

    hk_achado: Mapped[bytes] = _hk()
    id: Mapped[str]
    numero_cnj: Mapped[str]
    validacao: Mapped[str]
    sujeito: Mapped[str]
    hk_processo: Mapped[bytes]
    processo_id: Mapped[str]
    versao_catalogo: Mapped[str | None]
    resultado: Mapped[str | None]
    fatos_usados: Mapped[list[bytes] | None] = mapped_column(ARRAY(BYTEA))
    valores: Mapped[Any] = mapped_column(JsonTexto)
    explicacao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime | None]


class VisaoParte(BaseVisao):
    """`v_parte`: identidade corrente da parte."""

    __tablename__ = "v_parte"

    hk_parte: Mapped[bytes] = _hk()
    id: Mapped[str]
    numero_cnj: Mapped[str]
    chave_nome: Mapped[bytes]
    hk_processo: Mapped[bytes]
    processo_id: Mapped[str]
    nome: Mapped[str | None] = mapped_column(Text)
    polo: Mapped[str | None]
    qualidade: Mapped[str | None]
    hk_evidencia: Mapped[bytes | None]
    evidencia_id: Mapped[str | None]


class VisaoConversa(BaseVisao):
    """`v_conversa`: estado corrente da conversa."""

    __tablename__ = "v_conversa"

    hk_conversa: Mapped[bytes] = _hk()
    id: Mapped[str]
    conversa_id: Mapped[UUID]
    criada_em: Mapped[datetime]
    hk_processo: Mapped[bytes]
    processo_id: Mapped[str]
    hk_usuario: Mapped[bytes]
    usuario_id: Mapped[str]
    encerrada: Mapped[bool | None]
    motivo_encerramento: Mapped[str | None]
    tokens_entrada: Mapped[int | None]
    tokens_saida: Mapped[int | None]
    paginas_originais: Mapped[int | None]
    citacoes_descartadas: Mapped[int | None]


class VisaoSessao(BaseVisao):
    """`v_sessao`: estado corrente da sessão."""

    __tablename__ = "v_sessao"

    hk_sessao: Mapped[bytes] = _hk()
    id: Mapped[str]
    token_sha256: Mapped[str]
    criada_em: Mapped[datetime]
    hk_usuario: Mapped[bytes]
    usuario_id: Mapped[str]
    papel: Mapped[str | None]
    expira_em: Mapped[datetime | None]
    ultimo_acesso_em: Mapped[datetime | None]
    revogada: Mapped[bool | None]
    ip_criacao: Mapped[str | None]
    atualizada_em: Mapped[datetime | None]


class VisaoDesafioMfa(BaseVisao):
    """`v_desafio_mfa`: estado corrente do desafio do segundo passo do login."""

    __tablename__ = "v_desafio_mfa"

    hk_desafio_mfa: Mapped[bytes] = _hk()
    id: Mapped[str]
    token_sha256: Mapped[str]
    criado_em: Mapped[datetime]
    hk_usuario: Mapped[bytes]
    usuario_id: Mapped[str]
    papel: Mapped[str | None]
    expira_em: Mapped[datetime | None]
    consumido: Mapped[bool | None]


class VisaoBloqueioLogin(BaseVisao):
    """`v_bloqueio_login`: bloqueio corrente e falhas desde o último zeramento."""

    __tablename__ = "v_bloqueio_login"

    hk_chave_login: Mapped[bytes] = _hk()
    chave: Mapped[str]
    bloqueado_ate: Mapped[datetime | None]
    zerado_em: Mapped[datetime | None]
    falhas: Mapped[list[datetime]] = mapped_column(ARRAY(Instante))


class VisaoPecaHistorico(BaseVisao):
    """`v_peca_historico`: todas as classificações da peça, com autor e data."""

    __tablename__ = "v_peca_historico"

    hk_peca: Mapped[bytes] = _hk()
    load_dts: Mapped[datetime] = mapped_column(Instante, primary_key=True)
    peca_id: Mapped[str]
    pagina_inicial: Mapped[int]
    hk_usuario: Mapped[bytes | None]
    usuario_id: Mapped[str | None]
    tipo: Mapped[str]
    pagina_final: Mapped[int]
    confianca: Mapped[float]
    metodo: Mapped[str]
    origem: Mapped[str]
    data: Mapped[date | None]
    tipo_data: Mapped[str | None]
    hk_evidencia_data: Mapped[bytes | None]
    flags: Mapped[Any] = mapped_column(JSONB)
    classificacao: Mapped[Any] = mapped_column(JSONB)
    vigente: Mapped[bool]


class VisaoFatoHistorico(BaseVisao):
    """`v_fato_historico`: todos os valores do fato, com autor e data."""

    __tablename__ = "v_fato_historico"

    hk_fato: Mapped[bytes] = _hk()
    load_dts: Mapped[datetime] = mapped_column(Instante, primary_key=True)
    fato_id: Mapped[str]
    evidencias_vigentes: Mapped[list[bytes]] = mapped_column(ARRAY(BYTEA))
    hk_usuario: Mapped[bytes | None]
    usuario_id: Mapped[str | None]
    valor: Mapped[Any] = mapped_column(JsonTexto)
    extraido_por: Mapped[str]
    versao_extrator: Mapped[str]
    confianca: Mapped[float]
    status: Mapped[str]


class VisaoAchadoHistorico(BaseVisao):
    """Todas as versões do resultado de cada validação por recorrente."""

    __tablename__ = "v_achado_historico"

    hk_achado: Mapped[bytes] = _hk()
    criado_em: Mapped[datetime] = mapped_column(Instante, primary_key=True)
    id: Mapped[str]
    hk_processo: Mapped[bytes]
    processo_id: Mapped[str]
    validacao: Mapped[str]
    sujeito: Mapped[str]
    versao_catalogo: Mapped[str]
    resultado: Mapped[str]
    fatos_usados: Mapped[list[bytes]] = mapped_column(ARRAY(BYTEA))
    valores: Mapped[Any] = mapped_column(JsonTexto)
    explicacao: Mapped[str] = mapped_column(Text)


class VisaoMensagem(BaseVisao):
    """`v_mensagem`: versão corrente de cada mensagem da conversa, por `sequencia`."""

    __tablename__ = "v_mensagem"

    hk_conversa: Mapped[bytes] = _hk()
    sequencia: Mapped[int] = mapped_column(primary_key=True)
    conversa_id: Mapped[str]
    papel: Mapped[str]
    status: Mapped[str]
    texto: Mapped[str] = mapped_column(Text)
    citacoes: Mapped[Any] = mapped_column(JSONB)
    avisos: Mapped[Any] = mapped_column(JSONB)
    criada_em: Mapped[datetime]


class VisaoAnotacao(BaseVisao):
    """`v_anotacao`: anotações de fatos e achados, com autor e data."""

    __tablename__ = "v_anotacao"

    hk_alvo: Mapped[bytes] = _hk()
    criada_em: Mapped[datetime] = mapped_column(Instante, primary_key=True)
    alvo_tipo: Mapped[str] = mapped_column(Text)
    alvo_id: Mapped[str]
    hk_processo: Mapped[bytes]
    processo_id: Mapped[str]
    texto: Mapped[str] = mapped_column(Text)
    hk_usuario: Mapped[bytes]
    usuario_id: Mapped[str]
    nome_usuario: Mapped[str]


class VisaoResponsavel(BaseVisao):
    """`v_responsavel`: pares processo–usuário com a vigência corrente."""

    __tablename__ = "v_responsavel"

    hk_processo: Mapped[bytes] = _hk()
    hk_usuario: Mapped[bytes] = _hk()
    processo_id: Mapped[str]
    usuario_id: Mapped[str]
    nome_usuario: Mapped[str]
    vigente: Mapped[bool | None]
    atualizado_em: Mapped[datetime | None]


class VisaoFilaIngestao(BaseVisao):
    """`v_fila_ingestao`: arquivos a processar, do mais antigo para o mais novo."""

    __tablename__ = "v_fila_ingestao"

    hk_arquivo: Mapped[bytes] = _hk()
    id: Mapped[str]
    hk_processo: Mapped[bytes]
    processo_id: Mapped[str]
    estado: Mapped[str]
    tentativas: Mapped[int]
    criado_em: Mapped[datetime]


class VisaoAuditoria(BaseVisao):
    """`v_auditoria`: eventos com o nome do usuário e o número do processo."""

    __tablename__ = "v_auditoria"

    hk_evento: Mapped[bytes] = _hk()
    id: Mapped[str]
    sequencia: Mapped[int]
    ocorrido_em: Mapped[datetime]
    hk_usuario: Mapped[bytes | None]
    usuario_id: Mapped[str | None]
    nome_usuario: Mapped[str | None]
    hk_processo: Mapped[bytes | None]
    processo_id: Mapped[str | None]
    numero_cnj: Mapped[str | None]
    acao: Mapped[str]
    objeto_tipo: Mapped[str | None]
    objeto_id: Mapped[str | None]
    ip: Mapped[str | None]
    localizacao: Mapped[str | None]
    resultado: Mapped[str]
    versao_modelo: Mapped[str | None]
    versao_prompt: Mapped[str | None]
    hash_anterior: Mapped[str | None]
    modelo_chamada: Mapped[str | None]
    tokens_entrada: Mapped[int | None]
    tokens_saida: Mapped[int | None]
    hash_evento: Mapped[str]
    load_dts: Mapped[datetime]
