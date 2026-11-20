"""Descarte do processo pelo desembargador e retomada da limpeza de objetos (A13)."""

from typing import Annotated

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, Path, Request

from lupa_api.acesso.autorizacao import ContextoReq, SessaoBanco, exige_papel
from lupa_api.acesso.erros import NaoEncontradoError
from lupa_api.acesso.papeis import Permissao
from lupa_api.acesso.servico import Ator, auditar
from lupa_api.api.banco import sessao_aplicacao
from lupa_api.auditoria.eventos import AcaoAuditoria, ResultadoEvento
from lupa_pipeline.dominio.enums import StatusProcesso
from lupa_pipeline.dominio.gravacao import travar_processo
from lupa_pipeline.seguranca.descarte import apagar_objetos, descartar

router = APIRouter()
Revisor = Annotated[Ator, Depends(exige_papel(Permissao.VER_AUDITORIA))]


@router.post("/processos/{processo_id}/descartar")
def descartar_processo(
    processo_id: Annotated[str, Path(pattern=r"^[0-9a-fA-F]{64}$")],
    request: Request,
    ator: Revisor,
    sessao: SessaoBanco,
    ctx: ContextoReq,
) -> dict[str, str | int]:
    """Confirma o descarte e a auditoria juntos e apaga os objetos, inclusive nas retentativas."""
    hk = bytes.fromhex(processo_id)
    processo = travar_processo(sessao, hk)
    if processo is None:
        raise NaoEncontradoError("processo não encontrado")
    if processo.status != StatusProcesso.DESCARTADO.value:
        descartar(sessao, hk)
        auditar(
            sessao,
            ctx,
            AcaoAuditoria.PROCESSO_DESCARTADO,
            hk_usuario=ator.hk_usuario,
            hk_processo=hk,
            objeto_tipo="processo",
            objeto_id=hk.hex(),
        )
    sessao.commit()
    try:
        quantidade = apagar_objetos(request.app.state.storage, hk)
    except (BotoCoreError, ClientError, OSError) as erro:
        with sessao_aplicacao(request.app.state.fabrica_sessao) as recuperacao:
            auditar(
                recuperacao,
                ctx,
                AcaoAuditoria.DESCARTE_OBJETOS_PENDENTE,
                ResultadoEvento.FALHA,
                hk_usuario=ator.hk_usuario,
                hk_processo=hk,
                objeto_tipo="processo",
                objeto_id=hk.hex(),
            )
        raise HTTPException(
            status_code=503,
            detail="processo descartado; repita o descarte para concluir a limpeza dos objetos",
        ) from erro
    return {
        "processo_id": hk.hex(),
        "status": StatusProcesso.DESCARTADO.value,
        "objetos_apagados": quantidade,
    }
