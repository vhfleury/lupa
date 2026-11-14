"""Consulta e reclassificação manual das peças de um processo (RF-PEC-02)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from lupa_intranet.acesso.autorizacao import (
    AtorAutenticado,
    ContextoReq,
    SessaoBanco,
    exige_processo,
)
from lupa_intranet.acesso.erros import DadosInvalidosError, NaoEncontradoError
from lupa_intranet.acesso.servico import auditar
from lupa_intranet.api.middleware import auditar_rota
from lupa_intranet.auditoria.eventos import AcaoAuditoria
from lupa_pipeline.dominio.enums import OrigemPeca, TipoPeca
from lupa_pipeline.dominio.repositorios import processo_para_gravar
from lupa_pipeline.dominio.visoes import VisaoProcesso
from lupa_pipeline.ingestao import repositorio_pecas
from lupa_pipeline.ingestao.eventos.etapa import processar_eventos
from lupa_pipeline.ingestao.repositorio_pecas import (
    PedidoReclassificacao,
    ReclassificacaoInvalidaError,
)

router = APIRouter()
Processo = Annotated[VisaoProcesso, Depends(exige_processo)]


class CorpoReclassificacao(BaseModel):
    """Tipo, origem e intervalo solicitados para uma peça vigente."""

    model_config = ConfigDict(extra="forbid")
    tipo: TipoPeca | None = None
    origem: OrigemPeca | None = None
    pagina_inicial: int | None = Field(None, ge=1)
    pagina_final: int | None = Field(None, ge=1)


@router.get("/processos/{processo_id}/indice")
@auditar_rota(AcaoAuditoria.PROCESSO_ABERTO, conteudo=True)
def obter_indice(processo: Processo, sessao: SessaoBanco) -> dict[str, Any]:
    """Lista as peças vigentes em ordem de arquivo e de página."""
    return {
        "processo_id": processo.id,
        "pecas": repositorio_pecas.indice_processo(sessao, processo.hk_processo),
    }


@router.get("/processos/{processo_id}/pecas/{peca_id}")
@auditar_rota(AcaoAuditoria.PROCESSO_ABERTO, conteudo=True)
def obter_peca(processo: Processo, peca_id: str, sessao: SessaoBanco) -> dict[str, Any]:
    """Lê a peça do processo e o histórico de classificações."""
    peca = repositorio_pecas.obter_peca(sessao, processo.hk_processo, peca_id)
    if peca is None:
        raise NaoEncontradoError("peça não encontrada")
    return repositorio_pecas.detalhar_peca(sessao, peca)


@router.post("/processos/{processo_id}/pecas/{peca_id}/reclassificar", status_code=201)
def reclassificar_peca(
    processo: Processo,
    peca_id: str,
    corpo: CorpoReclassificacao,
    ator: AtorAutenticado,
    sessao: SessaoBanco,
    ctx: ContextoReq,
) -> dict[str, Any]:
    """Grava a revisão e atualiza os fatos e os achados na mesma transação."""
    processo_para_gravar(sessao, processo.hk_processo)
    peca = repositorio_pecas.obter_peca(sessao, processo.hk_processo, peca_id)
    if peca is None:
        raise NaoEncontradoError("peça não encontrada")
    try:
        nova = repositorio_pecas.reclassificar(
            sessao, peca, PedidoReclassificacao(**corpo.model_dump()), ator.hk_usuario
        )
    except ReclassificacaoInvalidaError as erro:
        raise DadosInvalidosError(str(erro)) from None
    auditar(
        sessao,
        ctx,
        AcaoAuditoria.PECA_RECLASSIFICADA,
        hk_usuario=ator.hk_usuario,
        hk_processo=processo.hk_processo,
        objeto_tipo="peca",
        objeto_id=nova.id,
    )
    processar_eventos(sessao, processo.hk_processo, ctx.agora.date())
    auditar(
        sessao,
        ctx,
        AcaoAuditoria.VALIDACAO_EXECUTADA,
        hk_usuario=ator.hk_usuario,
        hk_processo=processo.hk_processo,
        objeto_tipo="processo",
        objeto_id=processo.id,
    )
    return {
        "pecas": [repositorio_pecas.detalhar_peca(sessao, nova)],
        "substituidas": [peca_id] if nova.id != peca_id else [],
    }
