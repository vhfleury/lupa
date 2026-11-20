"""Consulta da cadeia única e relatório de uso a partir da view de auditoria."""

import base64
import csv
import io
import json
from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from itertools import groupby
from typing import Any

from sqlalchemy import Select, func, select, tuple_
from sqlalchemy.orm import Session

from lupa_api.agente.precos import TabelaPrecos, custo, tabela_padrao
from lupa_api.auditoria.eventos import AcaoAuditoria
from lupa_pipeline.dominio.esquemas import EventoAuditoria
from lupa_pipeline.dominio.visoes import VisaoAuditoria as Evento

LIMITE_PADRAO = 50
LIMITE_MAXIMO = 500
LIMITE_EXPORTACAO = 100_000


class CursorInvalidoError(ValueError):
    """O cursor recebido não identifica uma posição na cadeia."""


@dataclass(frozen=True)
class FiltroAuditoria:
    """Filtros por ids públicos e por intervalo semiaberto de ocorrência."""

    usuario_id: str | None = None
    processo_id: str | None = None
    acao: AcaoAuditoria | None = None
    inicio: datetime | None = None
    fim: datetime | None = None
    ip: str | None = None


@dataclass(frozen=True)
class PaginaEventos:
    """Eventos em ordem cronológica inversa e cursor para continuar a consulta."""

    eventos: list[EventoAuditoria]
    proximo_cursor: str | None


def codificar_cursor(evento: EventoAuditoria) -> str:
    """Codifica o instante e o id do último evento da página."""
    bruto = f"{evento.ocorrido_em.isoformat()}|{evento.id}"
    return base64.urlsafe_b64encode(bruto.encode()).decode()


def decodificar_cursor(cursor: str) -> tuple[datetime, bytes]:
    """Recupera o instante com fuso e o hash binário do evento."""
    try:
        bruto = base64.b64decode(cursor.encode(), altchars=b"-_", validate=True)
        instante, ident = bruto.decode().split("|")
        data = datetime.fromisoformat(instante)
        hk = bytes.fromhex(ident)
        if data.utcoffset() is None or len(hk) != 32 or len(ident) != 64:
            raise ValueError
    except ValueError as erro:
        raise CursorInvalidoError("cursor inválido") from erro
    return data, hk


def _aplicar_filtros(consulta: Select[Any], filtro: FiltroAuditoria) -> Select[Any]:
    if filtro.usuario_id is not None:
        consulta = consulta.where(Evento.hk_usuario == bytes.fromhex(filtro.usuario_id))
    if filtro.processo_id is not None:
        consulta = consulta.where(Evento.hk_processo == bytes.fromhex(filtro.processo_id))
    if filtro.acao is not None:
        consulta = consulta.where(Evento.acao == filtro.acao.value)
    if filtro.ip is not None:
        consulta = consulta.where(Evento.ip == filtro.ip)
    if filtro.inicio is not None:
        consulta = consulta.where(Evento.ocorrido_em >= filtro.inicio)
    if filtro.fim is not None:
        consulta = consulta.where(Evento.ocorrido_em < filtro.fim)
    return consulta


def _para_esquema(linha: Evento) -> EventoAuditoria:
    return EventoAuditoria.model_validate(linha, from_attributes=True)


def consultar(
    session: Session,
    filtro: FiltroAuditoria,
    cursor: str | None = None,
    limite: int = LIMITE_PADRAO,
) -> PaginaEventos:
    """Lê uma página de eventos filtrados, do mais recente ao mais antigo."""
    limite = max(1, min(limite, LIMITE_MAXIMO))
    consulta = _aplicar_filtros(select(Evento), filtro)
    if cursor is not None:
        consulta = consulta.where(
            tuple_(Evento.ocorrido_em, Evento.hk_evento) < decodificar_cursor(cursor)
        )
    consulta = consulta.order_by(Evento.ocorrido_em.desc(), Evento.hk_evento.desc()).limit(
        limite + 1
    )
    eventos = [_para_esquema(linha) for linha in session.scalars(consulta)]
    proximo = codificar_cursor(eventos[limite - 1]) if len(eventos) > limite else None
    return PaginaEventos(eventos[:limite], proximo)


def iterar_para_exportacao(session: Session, filtro: FiltroAuditoria) -> Iterator[EventoAuditoria]:
    """Percorre os eventos filtrados em ordem cronológica até o limite de exportação."""
    consulta = (
        _aplicar_filtros(select(Evento), filtro)
        .order_by(Evento.ocorrido_em, Evento.hk_evento)
        .limit(LIMITE_EXPORTACAO)
        .execution_options(yield_per=1000)
    )
    for linha in session.scalars(consulta):
        yield _para_esquema(linha)


def exportar_csv(eventos: Iterator[EventoAuditoria]) -> str:
    """Serializa eventos em CSV com cabeçalho."""
    saida = io.StringIO()
    escritor = csv.DictWriter(saida, fieldnames=list(EventoAuditoria.model_fields))
    escritor.writeheader()
    for evento in eventos:
        escritor.writerow(evento.model_dump(mode="json"))
    return saida.getvalue()


def exportar_json(eventos: Iterator[EventoAuditoria]) -> str:
    """Serializa os eventos como uma lista JSON."""
    return json.dumps([evento.model_dump(mode="json") for evento in eventos], ensure_ascii=False)


def relatorio_uso(session: Session, filtro: FiltroAuditoria) -> dict[str, Any]:
    """Resume contagens, acessos, versões e custos no escopo selecionado."""
    por_acao = session.execute(
        _aplicar_filtros(
            select(
                Evento.acao,
                func.count(),
                func.min(Evento.ocorrido_em),
                func.max(Evento.ocorrido_em),
            ),
            filtro,
        ).group_by(Evento.acao)
    ).all()
    versoes = session.execute(
        _aplicar_filtros(
            select(Evento.versao_modelo, Evento.versao_prompt, func.count()),
            replace(filtro, acao=AcaoAuditoria.CHAMADA_MODELO),
        )
        .group_by(Evento.versao_modelo, Evento.versao_prompt)
        .order_by(Evento.versao_modelo, Evento.versao_prompt)
    ).all()
    return {
        "contagem_por_acao": {acao: total for acao, total, _, _ in por_acao},
        "primeiro_acesso": min((linha[2] for linha in por_acao), default=None),
        "ultimo_acesso": max((linha[3] for linha in por_acao), default=None),
        "chamadas_modelo": [
            {"versao_modelo": modelo, "versao_prompt": prompt, "total": total}
            for modelo, prompt, total in versoes
        ],
        "custo_estimado": custo_estimado(session, filtro),
    }


def custo_estimado(
    session: Session, filtro: FiltroAuditoria, tabela: TabelaPrecos | None = None
) -> dict[str, Any]:
    """Custeia os tokens das chamadas de chat e de dossiê atribuídas a cada evento."""
    tabela = tabela or tabela_padrao()
    tokens = (
        _aplicar_filtros(
            select(
                Evento.modelo_chamada,
                func.sum(Evento.tokens_entrada),
                func.sum(Evento.tokens_saida),
            ),
            filtro,
        )
        .where(Evento.modelo_chamada.is_not(None))
        .group_by(Evento.modelo_chamada)
        .order_by(Evento.modelo_chamada)
    )
    por_modelo = []
    total = Decimal("0.0000")
    for modelo, entrada, saida in session.execute(tokens):
        preco = tabela.preco_de(modelo)
        valor = custo(preco, entrada, saida) if preco else None
        total += valor or 0
        por_modelo.append(
            {
                "modelo": modelo,
                "tokens_entrada": entrada,
                "tokens_saida": saida,
                "custo": str(valor) if valor is not None else None,
            }
        )
    return {
        "total": str(total),
        "moeda": tabela.moeda,
        "versao_tabela": tabela.versao,
        "fonte": tabela.fonte,
        "observacao": tabela.observacao,
        "por_modelo": por_modelo,
    }


def exportar_uso(session: Session, filtro: FiltroAuditoria) -> str:
    """Exporta contagens e custos por par processo/usuário no período (RF-AUD-05)."""
    tabela = tabela_padrao()
    grupos = [Evento.processo_id, Evento.usuario_id, Evento.acao, Evento.modelo_chamada]
    consulta = (
        _aplicar_filtros(
            select(
                *grupos,
                func.count(),
                func.sum(Evento.tokens_entrada),
                func.sum(Evento.tokens_saida),
            ),
            filtro,
        )
        .group_by(*grupos)
        .order_by(*grupos)
    )
    saida = io.StringIO()
    escritor = csv.writer(saida)
    escritor.writerow(
        (
            "processo_id",
            "usuario_id",
            "eventos",
            "contagem_por_acao",
            "chamadas_modelo",
            "chamadas_sem_preco",
            "custo_estimado",
            "moeda",
            "versao_tabela",
        )
    )
    for (processo, usuario), linhas in groupby(
        session.execute(consulta), key=lambda r: (r[0], r[1])
    ):
        por_acao: dict[str, int] = {}
        total = Decimal("0.0000")
        sem_preco = 0
        for _, _, acao, modelo, quantidade, tokens_entrada, tokens_saida in linhas:
            por_acao[acao] = por_acao.get(acao, 0) + quantidade
            if acao == AcaoAuditoria.CHAMADA_MODELO:
                preco = tabela.preco_de(modelo) if modelo else None
                if preco:
                    total += custo(preco, tokens_entrada, tokens_saida)
                else:
                    sem_preco += quantidade
        escritor.writerow(
            (
                processo,
                usuario,
                sum(por_acao.values()),
                json.dumps(por_acao, sort_keys=True),
                por_acao.get(AcaoAuditoria.CHAMADA_MODELO, 0),
                sem_preco,
                total,
                tabela.moeda,
                tabela.versao,
            )
        )
    return saida.getvalue()
