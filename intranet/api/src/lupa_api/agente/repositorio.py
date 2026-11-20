"""Histórico de conversas do usuário e metadados das chamadas ao modelo no Data Vault."""

import re
from dataclasses import asdict, dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.chaves import chave_hash
from lupa_pipeline.dominio.enums import PapelMensagem, StatusMensagem
from lupa_pipeline.dominio.gravacao import gravar_hub, gravar_link, gravar_satelite
from lupa_pipeline.dominio.tabelas import (
    hub_conversa,
    link_chamada_modelo,
    link_processo_conversa,
    sat_conversa_estado,
    sat_conversa_mensagem,
)
from lupa_pipeline.dominio.visoes import (
    VisaoAchado,
    VisaoArquivo,
    VisaoAuditoria,
    VisaoConversa,
    VisaoEvidencia,
    VisaoFato,
    VisaoMensagem,
    VisaoPagina,
    VisaoParte,
    VisaoPeca,
)

ORIGEM = "api.agente"


@dataclass
class EstadoConversa:
    """Contadores correntes que serão gravados em uma nova versão do satélite."""

    encerrada: bool = False
    motivo_encerramento: str | None = None
    tokens_entrada: int = 0
    tokens_saida: int = 0
    paginas_originais: int = 0
    citacoes_descartadas: int = 0


@dataclass
class Conversa:
    """Conversa do processo e do usuário autenticado, sob a trava do processo."""

    hk: bytes
    estado: EstadoConversa


def conversa_do_usuario(session: Session, hk_processo: bytes, hk_usuario: bytes) -> Conversa:
    """Abre a conversa mais recente, inclusive quando já atingiu o teto, ou cria a primeira."""
    consulta = (
        select(VisaoConversa)
        .where(
            VisaoConversa.hk_processo == hk_processo,
            VisaoConversa.hk_usuario == hk_usuario,
        )
        .order_by(VisaoConversa.criada_em.desc(), VisaoConversa.id)
        .limit(1)
    )
    linha = session.scalar(consulta)
    if linha is not None:
        return Conversa(
            linha.hk_conversa,
            EstadoConversa(
                bool(linha.encerrada),
                linha.motivo_encerramento,
                linha.tokens_entrada or 0,
                linha.tokens_saida or 0,
                linha.paginas_originais or 0,
                linha.citacoes_descartadas or 0,
            ),
        )
    hk = gravar_hub(session, hub_conversa, {"conversa_id": uuid4()}, ORIGEM)
    gravar_link(
        session,
        link_processo_conversa,
        {
            "hk_processo": hk_processo,
            "hk_conversa": hk,
            "hk_usuario": hk_usuario,
        },
        ORIGEM,
    )
    conversa = Conversa(hk, EstadoConversa())
    gravar_estado(session, conversa)
    return conversa


def gravar_estado(session: Session, conversa: Conversa) -> None:
    """Insere o estado da conversa quando algum contador ou indicador mudou."""
    gravar_satelite(session, sat_conversa_estado, conversa.hk, asdict(conversa.estado), ORIGEM)


def tokens_do_processo(session: Session, hk_processo: bytes) -> int:
    """Soma tokens de todas as chamadas auditadas do processo, inclusive dos resumos."""
    consulta = select(func.sum(VisaoAuditoria.tokens_entrada + VisaoAuditoria.tokens_saida)).where(
        VisaoAuditoria.hk_processo == hk_processo, VisaoAuditoria.acao == "chamada_modelo"
    )
    return int(session.scalar(consulta) or 0)


def id_mensagem(mensagem: VisaoMensagem) -> str:
    """Identificador público derivado da chave do satélite multiativo, para auditoria e API."""
    return chave_hash([mensagem.hk_conversa, mensagem.sequencia]).hex()


def gravar_mensagem(
    session: Session,
    conversa: Conversa,
    papel: PapelMensagem,
    status: StatusMensagem,
    texto: str,
    citacoes: list[dict[str, Any]] | None = None,
    avisos: list[str] | None = None,
) -> VisaoMensagem:
    """Acrescenta mensagem com sequência crescente."""
    ultima = session.scalar(
        select(func.max(VisaoMensagem.sequencia)).where(VisaoMensagem.hk_conversa == conversa.hk)
    )
    sequencia = (ultima or 0) + 1
    dados = {
        "sequencia": sequencia,
        "papel": papel.value,
        "status": status.value,
        "texto": texto,
        "citacoes": citacoes or [],
        "avisos": avisos or [],
    }
    gravar_satelite(session, sat_conversa_mensagem, conversa.hk, dados, ORIGEM)
    return session.scalars(
        select(VisaoMensagem).where(
            VisaoMensagem.hk_conversa == conversa.hk,
            VisaoMensagem.sequencia == sequencia,
        )
    ).one()


def gravar_chamada(session: Session, **campos: Any) -> bytes:
    """Grava chamada não historizada, com identificador único até para tentativas idênticas."""
    hk = chave_hash([campos["hk_processo"], uuid4()])
    session.execute(
        link_chamada_modelo.insert().values(hk_chamada=hk, record_source=ORIGEM, **campos)
    )
    return hk


def ids_do_processo(session: Session, hk_processo: bytes) -> set[str]:
    """Identificadores do próprio processo que podem aparecer no texto da resposta."""
    ids = {hk_processo.hex()}
    for view in (
        VisaoArquivo,
        VisaoPagina,
        VisaoPeca,
        VisaoEvidencia,
        VisaoFato,
        VisaoAchado,
        VisaoParte,
    ):
        ids.update(session.scalars(select(view.id).where(view.hk_processo == hk_processo)))
    return ids


def paginas_citadas(
    session: Session, hk_processo: bytes, ids: list[str]
) -> dict[str, tuple[str, str | None]]:
    """Textos de conferência das páginas solicitadas e pertencentes ao processo."""
    if not ids:
        return {}
    consulta = select(VisaoPagina.id, VisaoPagina.texto, VisaoPagina.texto_normalizado).where(
        VisaoPagina.hk_processo == hk_processo,
        VisaoPagina.id.in_(ids),
    )
    return {
        i: (texto, saneado) for i, texto, saneado in session.execute(consulta) if texto is not None
    }


def historico(session: Session, hk_processo: bytes, hk_usuario: bytes) -> list[dict[str, Any]]:
    """Conversas do usuário no processo e mensagens ordenadas por sequência."""
    conversas = session.scalars(
        select(VisaoConversa)
        .where(VisaoConversa.hk_processo == hk_processo, VisaoConversa.hk_usuario == hk_usuario)
        .order_by(VisaoConversa.criada_em, VisaoConversa.id)
    )
    historico = []
    for conversa in conversas:
        mensagens = session.scalars(
            select(VisaoMensagem)
            .where(VisaoMensagem.hk_conversa == conversa.hk_conversa)
            .order_by(VisaoMensagem.sequencia)
        )
        historico.append(
            {
                "conversa_id": conversa.id,
                "criada_em": conversa.criada_em.isoformat(),
                "encerrada": conversa.encerrada,
                "motivo_encerramento": conversa.motivo_encerramento,
                "citacoes_descartadas": conversa.citacoes_descartadas,
                "mensagens": [serializar_mensagem(session, hk_processo, m) for m in mensagens],
            }
        )
    return historico


def serializar_mensagem(
    session: Session, hk_processo: bytes, mensagem: VisaoMensagem
) -> dict[str, Any]:
    """Localiza as citações e rotula a mensagem gerada pelo agente."""
    return {
        "mensagem_id": id_mensagem(mensagem),
        "papel": mensagem.papel,
        "status": mensagem.status,
        "texto": mensagem.texto,
        "citacoes": localizar_citacoes(session, hk_processo, mensagem.citacoes),
        "avisos": mensagem.avisos,
        "citacoes_descartadas": descartadas_dos_avisos(mensagem.avisos),
        "rotulo": "gerado por IA" if mensagem.papel == PapelMensagem.AGENTE.value else None,
        "criado_em": mensagem.criada_em.isoformat(),
    }


AVISO_DESCARTE = re.compile(r"^(\d+) citação\(ões\) não conferiram")


def descartadas_dos_avisos(avisos: list[str]) -> int:
    """Quantas citações a resposta perdeu na conferência (lido do aviso gravado).

    Args:
        avisos: Avisos da mensagem.

    Returns:
        Número de citações descartadas (0 se não houve).
    """
    for aviso in avisos:
        achado = AVISO_DESCARTE.match(aviso)
        if achado:
            return int(achado.group(1))
    return 0


def localizar_citacoes(
    session: Session, hk_processo: bytes, citacoes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Recupera o trecho e a posição de cada citação conferida no processo."""
    if not citacoes:
        return []
    ids = [c["pagina_id"] for c in citacoes]
    consulta = select(VisaoPagina.id, VisaoPagina.numero, VisaoPagina.arquivo_id).where(
        VisaoPagina.hk_processo == hk_processo, VisaoPagina.id.in_(ids)
    )
    locais = {i: (n, arquivo) for i, n, arquivo in session.execute(consulta)}
    return [
        c
        | {
            "pagina_numero": locais[c["pagina_id"]][0],
            "arquivo_id": locais[c["pagina_id"]][1],
        }
        for c in citacoes
        if c["pagina_id"] in locais
    ]
