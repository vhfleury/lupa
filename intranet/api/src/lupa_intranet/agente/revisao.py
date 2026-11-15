"""Incidentes de segurança do chat e liberação pelo desembargador (RF-CHA-08)."""

from typing import Any

from sqlalchemy.orm import Session

from lupa_intranet.acesso.erros import ConflitoError, NaoEncontradoError
from lupa_intranet.acesso.servico import Contexto, auditar
from lupa_intranet.auditoria.eventos import AcaoAuditoria, ResultadoEvento
from lupa_pipeline.dominio.enums import StatusProcesso
from lupa_pipeline.dominio.gravacao import gravar_satelite, travar_processo
from lupa_pipeline.dominio.tabelas import sat_processo_estado, sat_processo_revisao
from lupa_pipeline.dominio.visoes import VisaoProcesso

ORIGEM = "intranet.agente"
MSG_EM_REVISAO = (
    "Este processo está em revisão. O assistente bloqueou uma resposta por conter uma instrução "
    "dos autos ou identificador de outro processo. O desembargador pode liberar o chat e os "
    "resumos."
)


def em_revisao(processo: VisaoProcesso) -> bool:
    """Indica se há incidente do agente pendente de liberação."""
    return processo.em_revisao or processo.status == StatusProcesso.EM_REVISAO.value


def situacao(processo: VisaoProcesso) -> dict[str, Any]:
    """Situação da revisão para a interface, com o motivo vigente ao abrir o incidente."""
    aberta = em_revisao(processo)
    return {
        "processo_id": processo.id,
        "status": processo.status,
        "em_revisao": aberta,
        "motivo": processo.motivo_revisao if aberta else None,
        "aberta_em": processo.revisao_em.isoformat() if aberta and processo.revisao_em else None,
    }


def processo_para_escrita(session: Session, hk_processo: bytes) -> VisaoProcesso:
    """Obtém a trava do processo e recusa acesso caso um descarte tenha vencido a corrida."""
    processo = travar_processo(session, hk_processo)
    if processo is None or processo.status == StatusProcesso.DESCARTADO.value:
        raise NaoEncontradoError("conteúdo indisponível")
    return processo


def abrir(
    session: Session, ctx: Contexto, processo: VisaoProcesso, motivo: str, hk_usuario: bytes
) -> None:
    """Grava o incidente e o status anterior para restauração, sob a trava da chamada."""
    if em_revisao(processo):
        return
    hk = processo.hk_processo
    dados = {
        "situacao": "aberta",
        "motivo": motivo,
        "status_anterior": processo.status,
        "hk_usuario": hk_usuario,
    }
    gravar_satelite(session, sat_processo_revisao, hk, dados, ORIGEM)
    gravar_satelite(
        session, sat_processo_estado, hk, {"status": StatusProcesso.EM_REVISAO.value}, ORIGEM
    )
    auditar(
        session,
        ctx,
        AcaoAuditoria.PROCESSO_EM_REVISAO,
        ResultadoEvento.BLOQUEADO,
        hk_usuario=hk_usuario,
        hk_processo=hk,
        objeto_tipo="processo",
        objeto_id=processo.id,
    )
    session.refresh(processo)


def liberar(
    session: Session, ctx: Contexto, processo: VisaoProcesso, hk_usuario: bytes
) -> dict[str, Any]:
    """Libera a revisão restaurando o status que o incidente interrompeu."""
    processo = processo_para_escrita(session, processo.hk_processo)
    if not em_revisao(processo) or processo.status_anterior_revisao is None:
        raise ConflitoError("o processo não está em revisão")
    hk = processo.hk_processo
    anterior = processo.status_anterior_revisao
    dados = {
        "situacao": "liberada",
        "motivo": processo.motivo_revisao,
        "status_anterior": anterior,
        "hk_usuario": hk_usuario,
    }
    gravar_satelite(session, sat_processo_revisao, hk, dados, ORIGEM)
    gravar_satelite(session, sat_processo_estado, hk, {"status": anterior}, ORIGEM)
    auditar(
        session,
        ctx,
        AcaoAuditoria.REVISAO_LIBERADA,
        hk_usuario=hk_usuario,
        hk_processo=hk,
        objeto_tipo="processo",
        objeto_id=processo.id,
    )
    session.refresh(processo)
    return situacao(processo)
