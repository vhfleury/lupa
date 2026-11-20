"""Consulta da revisão e liberação pelo desembargador (RF-CHA-08)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from lupa_api.acesso.autorizacao import ContextoReq, SessaoBanco, exige_papel, exige_processo
from lupa_api.acesso.papeis import Permissao
from lupa_api.acesso.servico import Ator
from lupa_api.agente import revisao
from lupa_pipeline.dominio.visoes import VisaoProcesso

router = APIRouter()

Processo = Annotated[VisaoProcesso, Depends(exige_processo)]
Revisor = Annotated[Ator, Depends(exige_papel(Permissao.VER_AUDITORIA))]


@router.get("/processos/{processo_id}/revisao")
def situacao_revisao(processo: Processo) -> dict[str, Any]:
    """Se o processo está em revisão e por quê.

    Args:
        processo: Processo autorizado.

    Returns:
        Situação de revisão.
    """
    return revisao.situacao(processo)


@router.post("/processos/{processo_id}/liberar-revisao")
def liberar_revisao(
    processo: Processo, ator: Revisor, sessao: SessaoBanco, ctx: ContextoReq
) -> dict[str, Any]:
    """Libera o processo em revisão.

    Args:
        processo: Processo autorizado.
        ator: Desembargador.
        sessao: Sessão da requisição.
        ctx: Contexto (auditoria).

    Returns:
        Situação depois da liberação.
    """
    return revisao.liberar(sessao, ctx, processo, ator.hk_usuario)
