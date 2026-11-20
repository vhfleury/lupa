"""Consulta e exportação da auditoria do gabinete pelo desembargador."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from sqlalchemy import select

from lupa_api.acesso.autorizacao import ContextoReq, SessaoBanco, exige_papel
from lupa_api.acesso.erros import DadosInvalidosError
from lupa_api.acesso.papeis import Permissao
from lupa_api.acesso.servico import Ator, Contexto, auditar
from lupa_api.auditoria import consulta
from lupa_api.auditoria.consulta import CursorInvalidoError, FiltroAuditoria
from lupa_api.auditoria.eventos import AcaoAuditoria
from lupa_api.auditoria.registrador import ResultadoVerificacao, verificar_cadeia
from lupa_pipeline.dominio.esquemas import EventoAuditoria
from lupa_pipeline.dominio.visoes import VisaoProcesso

router = APIRouter(prefix="/auditoria")
Auditor = Annotated[Ator, Depends(exige_papel(Permissao.VER_AUDITORIA))]
Identificador = Annotated[str | None, Query(pattern=r"^[0-9a-fA-F]{64}$")]


class PaginaSaida(BaseModel):
    """Página de eventos da cadeia."""

    eventos: list[EventoAuditoria]
    proximo_cursor: str | None


def filtros(
    usuario_id: Identificador = None,
    processo_id: Identificador = None,
    acao: AcaoAuditoria | None = None,
    inicio: datetime | None = None,
    fim: datetime | None = None,
    ip: str | None = Query(default=None, max_length=64),
) -> FiltroAuditoria:
    """Recebe ids públicos, período, ação e IP para a consulta."""
    return FiltroAuditoria(usuario_id, processo_id, acao, inicio, fim, ip)


Filtro = Annotated[FiltroAuditoria, Depends(filtros)]


def _auditar_ato(
    session: SessaoBanco,
    ctx: Contexto,
    ator: Ator,
    acao: AcaoAuditoria,
    filtro: FiltroAuditoria,
    objeto_tipo: str = "auditoria",
) -> None:
    hk_processo = None
    if filtro.processo_id:
        hk_processo = session.scalar(
            select(VisaoProcesso.hk_processo).where(
                VisaoProcesso.hk_processo == bytes.fromhex(filtro.processo_id)
            )
        )
    auditar(
        session,
        ctx,
        acao,
        hk_usuario=ator.hk_usuario,
        hk_processo=hk_processo,
        objeto_tipo=objeto_tipo,
        objeto_id=filtro.processo_id or filtro.usuario_id,
    )


@router.get("")
def listar(
    ator: Auditor,
    filtro: Filtro,
    session: SessaoBanco,
    ctx: ContextoReq,
    cursor: str | None = Query(default=None, max_length=200),
    limite: int = Query(default=consulta.LIMITE_PADRAO, ge=1, le=consulta.LIMITE_MAXIMO),
) -> PaginaSaida:
    """Lista eventos filtrados por ordem de ocorrência e registra a consulta."""
    try:
        pagina = consulta.consultar(session, filtro, cursor, limite)
    except CursorInvalidoError as erro:
        raise DadosInvalidosError(str(erro)) from erro
    _auditar_ato(session, ctx, ator, AcaoAuditoria.AUDITORIA_CONSULTADA, filtro)
    return PaginaSaida(eventos=pagina.eventos, proximo_cursor=pagina.proximo_cursor)


@router.get("/exportar")
def exportar(
    ator: Auditor,
    filtro: Filtro,
    session: SessaoBanco,
    ctx: ContextoReq,
    formato: Literal["csv", "json"] = "csv",
) -> Response:
    """Exporta os eventos filtrados e registra a exportação."""
    eventos = consulta.iterar_para_exportacao(session, filtro)
    if formato == "csv":
        corpo, tipo = consulta.exportar_csv(eventos), "text/csv; charset=utf-8"
    else:
        corpo, tipo = consulta.exportar_json(eventos), "application/json"
    _auditar_ato(session, ctx, ator, AcaoAuditoria.AUDITORIA_EXPORTADA, filtro)
    return Response(
        content=corpo,
        media_type=tipo,
        headers={"Content-Disposition": f'attachment; filename="auditoria.{formato}"'},
    )


@router.get("/verificar")
def verificar(_ator: Auditor, session: SessaoBanco) -> ResultadoVerificacao:
    """Informa a primeira sequência inconsistente na cadeia única."""
    return verificar_cadeia(session)


@router.get("/relatorio-uso", response_model=None)
def relatorio_uso(
    ator: Auditor,
    session: SessaoBanco,
    ctx: ContextoReq,
    processo: Identificador = None,
    usuario: Identificador = None,
    inicio: datetime | None = None,
    fim: datetime | None = None,
    formato: Literal["json", "csv"] = "json",
) -> dict[str, object] | Response:
    """Exporta o período em CSV ou detalha o uso de um processo ou usuário em JSON."""
    filtro = FiltroAuditoria(usuario_id=usuario, processo_id=processo, inicio=inicio, fim=fim)
    if formato == "csv":
        corpo = consulta.exportar_uso(session, filtro)
        _auditar_ato(session, ctx, ator, AcaoAuditoria.AUDITORIA_EXPORTADA, filtro, "relatorio_uso")
        return Response(
            content=corpo,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="relatorio-uso.csv"'},
        )
    if (processo is None) == (usuario is None):
        raise DadosInvalidosError("informe um processo ou um usuário")
    return {"processo": processo, "usuario": usuario, **consulta.relatorio_uso(session, filtro)}
