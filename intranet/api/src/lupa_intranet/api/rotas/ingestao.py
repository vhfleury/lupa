"""Upload de originais e leitura do estado, diagnóstico e alertas de um arquivo do processo."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from lupa_intranet.acesso.autorizacao import (
    ContextoReq,
    SessaoBanco,
    carregar_processo,
    exige_papel,
    exige_processo,
)
from lupa_intranet.acesso.erros import ConflitoError, NaoEncontradoError
from lupa_intranet.acesso.papeis import Permissao
from lupa_intranet.acesso.servico import Ator, auditar
from lupa_intranet.api.middleware import auditar_rota
from lupa_intranet.auditoria.eventos import AcaoAuditoria, ResultadoEvento
from lupa_pipeline.config import Settings, get_settings
from lupa_pipeline.dominio.enums import StatusProcesso
from lupa_pipeline.dominio.visoes import VisaoArquivo, VisaoProcesso
from lupa_pipeline.ingestao import repositorio
from lupa_pipeline.ingestao.recepcao import (
    MotivoRecusa,
    ProcessoDescartadoError,
    RecepcaoRecusadaError,
    lacrar,
    receber,
)
from lupa_pipeline.seguranca.contexto import ativar_processo

router = APIRouter()
RECUSAS = {
    MotivoRecusa.TAMANHO: (413, "arquivo acima do tamanho máximo"),
    MotivoRecusa.VAZIO: (422, "arquivo vazio"),
}
Processo = Annotated[VisaoProcesso, Depends(exige_processo)]
ProcessoEnvio = Annotated[VisaoProcesso, Depends(carregar_processo)]
Remetente = Annotated[Ator, Depends(exige_papel(Permissao.SUBIR_PROCESSO))]
Configuracao = Annotated[Settings, Depends(get_settings)]


@router.post("/processos/{processo_id}/arquivos", status_code=201)
async def enviar_arquivo(
    request: Request,
    processo: ProcessoEnvio,
    ator: Remetente,
    sessao: SessaoBanco,
    ctx: ContextoReq,
    settings: Configuracao,
    nome: Annotated[str, Query(min_length=1, max_length=255)],
) -> JSONResponse:
    """Lacra o corpo em streaming e registra o upload na transação do arquivo (A3)."""
    if processo.status == StatusProcesso.DESCARTADO.value:
        raise ConflitoError("processo descartado")
    try:
        recebido = await receber(
            request.stream(), nome, settings.upload_limite_bytes, settings.ingestao_dir_temporario
        )
    except RecepcaoRecusadaError as recusa:
        await run_in_threadpool(
            auditar,
            sessao,
            ctx,
            AcaoAuditoria.UPLOAD,
            ResultadoEvento.NEGADO,
            hk_usuario=ator.hk_usuario,
            hk_processo=processo.hk_processo,
            objeto_tipo="arquivo",
        )
        status, mensagem = RECUSAS[recusa.motivo]
        return JSONResponse(
            status_code=status, content={"detail": mensagem, "motivo": recusa.motivo.value}
        )
    try:
        await run_in_threadpool(ativar_processo, processo.hk_processo, processo.chave_dados_cifrada)
        lacre = await run_in_threadpool(
            lacrar,
            sessao,
            request.app.state.storage,
            recebido,
            hk_processo=processo.hk_processo,
            enviado_por=ator.hk_usuario,
            nome_original=nome,
        )
    except ProcessoDescartadoError:
        raise ConflitoError("processo descartado") from None
    finally:
        recebido.caminho.unlink(missing_ok=True)
    if not lacre.duplicado:
        await run_in_threadpool(
            auditar,
            sessao,
            ctx,
            AcaoAuditoria.UPLOAD,
            hk_usuario=ator.hk_usuario,
            hk_processo=processo.hk_processo,
            objeto_tipo="arquivo",
            objeto_id=lacre.arquivo_id,
        )
    return JSONResponse(
        status_code=200 if lacre.duplicado else 201,
        content={
            "arquivo_id": lacre.arquivo_id,
            "estado": lacre.estado,
            "sha256": recebido.sha256,
            "tamanho_bytes": recebido.tamanho_bytes,
            "mime": recebido.tipo.value,
            "duplicado": lacre.duplicado,
        },
    )


def _arquivo_do_processo(arquivo_id: str, processo: Processo, sessao: SessaoBanco) -> VisaoArquivo:
    consulta = select(VisaoArquivo).where(
        VisaoArquivo.id == arquivo_id.lower(),
        VisaoArquivo.hk_processo == processo.hk_processo,
    )
    arquivo = sessao.scalars(consulta).one_or_none()
    if arquivo is None:
        raise NaoEncontradoError("arquivo não encontrado")
    return arquivo


Arquivo = Annotated[VisaoArquivo, Depends(_arquivo_do_processo)]


@router.get("/processos/{processo_id}/arquivos/{arquivo_id}/diagnostico")
@auditar_rota(AcaoAuditoria.PROCESSO_ABERTO, conteudo=True)
def obter_diagnostico(arquivo: Arquivo) -> dict[str, Any]:
    """Lê o diagnóstico mais recente do arquivo em `v_arquivo` (RF-ING-03)."""
    if arquivo.cenario is None:
        raise NaoEncontradoError("diagnóstico ainda não disponível")
    return {
        "arquivo_id": arquivo.id,
        "cenario": arquivo.cenario,
        "total_paginas": arquivo.total_paginas_diagnostico,
        "tem_indice": arquivo.tem_indice,
        "sinais": arquivo.sinais,
        "fronteiras_origem": arquivo.fronteiras_origem,
        "metadados_descartados": arquivo.metadados_descartados,
    }


@router.get("/processos/{processo_id}/arquivos/{arquivo_id}/relatorio")
@auditar_rota(AcaoAuditoria.PROCESSO_ABERTO, conteudo=False)
def obter_relatorio(arquivo: Arquivo) -> dict[str, Any]:
    """Exibe estado, versão e relatório de qualidade do arquivo (RF-ING-06)."""
    return {
        "arquivo_id": arquivo.id,
        "estado": arquivo.estado,
        "versao_extrator": arquivo.versao_extrator,
        "relatorio": arquivo.relatorio,
    }


@router.get("/processos/{processo_id}/arquivos/{arquivo_id}/alertas")
@auditar_rota(AcaoAuditoria.PROCESSO_ABERTO, conteudo=False)
def obter_alertas(arquivo: Arquivo, sessao: SessaoBanco) -> dict[str, Any]:
    """Exibe sinais de injeção e metadados suspeitos do arquivo (RF-ING-05)."""
    return repositorio.alertas_arquivo(sessao, arquivo)
