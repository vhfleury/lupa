"""Upload de originais e leitura do estado, diagnóstico e alertas de um arquivo do processo."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from lupa_api.acesso.autorizacao import (
    ContextoReq,
    SessaoBanco,
    carregar_processo,
    exige_papel,
    exige_processo,
)
from lupa_api.acesso.erros import ConflitoError, NaoEncontradoError
from lupa_api.acesso.papeis import Permissao
from lupa_api.acesso.servico import Ator, Contexto, auditar
from lupa_api.api.middleware import auditar_rota
from lupa_api.api.rotas.processos import gravar_processo
from lupa_api.auditoria.eventos import AcaoAuditoria, ResultadoEvento
from lupa_pipeline.config import Settings, get_settings
from lupa_pipeline.dominio.cnj import (
    NumeroCnjInvalidoError,
    formatar_numero_cnj,
    validar_numero_cnj,
)
from lupa_pipeline.dominio.enums import ClasseProcessual, StatusProcesso
from lupa_pipeline.dominio.gravacao import chave_do_hub
from lupa_pipeline.dominio.tabelas import hub_processo
from lupa_pipeline.dominio.visoes import VisaoArquivo, VisaoProcesso
from lupa_pipeline.ingestao import repositorio
from lupa_pipeline.ingestao.identificacao import LeituraRecusada, identificar, ler_capa
from lupa_pipeline.ingestao.recepcao import (
    ArquivoRecebido,
    MotivoRecusa,
    ProcessoDescartadoError,
    RecepcaoRecusadaError,
    lacrar,
    receber,
)
from lupa_pipeline.ingestao.storage import ObjectStorage

router = APIRouter()
RECUSAS = {
    MotivoRecusa.TAMANHO: (413, "arquivo acima do tamanho máximo"),
    MotivoRecusa.VAZIO: (422, "arquivo vazio"),
}
Processo = Annotated[VisaoProcesso, Depends(exige_processo)]
ProcessoEnvio = Annotated[VisaoProcesso, Depends(carregar_processo)]
Remetente = Annotated[Ator, Depends(exige_papel(Permissao.SUBIR_PROCESSO))]
Configuracao = Annotated[Settings, Depends(get_settings)]


TRAVA_CADASTRO = 0x4C554341


async def _receber_envio(
    request: Request,
    nome: str,
    settings: Settings,
    sessao: Session,
    ator: Ator,
    ctx: Contexto,
    hk_processo: bytes | None,
) -> ArquivoRecebido | JSONResponse:
    try:
        return await receber(
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
            hk_processo=hk_processo,
            objeto_tipo="arquivo",
        )
        status, mensagem = RECUSAS[recusa.motivo]
        return JSONResponse(
            status_code=status, content={"detail": mensagem, "motivo": recusa.motivo.value}
        )


def _lacrar_envio(
    sessao: Session,
    storage: ObjectStorage,
    recebido: ArquivoRecebido,
    nome: str,
    processo: VisaoProcesso,
    ator: Ator,
    ctx: Contexto,
) -> tuple[int, dict[str, Any]]:
    if processo.status == StatusProcesso.DESCARTADO.value:
        raise ConflitoError("processo descartado")
    try:
        lacre = lacrar(
            sessao,
            storage,
            recebido,
            hk_processo=processo.hk_processo,
            enviado_por=ator.hk_usuario,
            nome_original=nome,
        )
    except ProcessoDescartadoError:
        raise ConflitoError("processo descartado") from None
    if not lacre.duplicado:
        auditar(
            sessao,
            ctx,
            AcaoAuditoria.UPLOAD,
            hk_usuario=ator.hk_usuario,
            hk_processo=processo.hk_processo,
            objeto_tipo="arquivo",
            objeto_id=lacre.arquivo_id,
        )
    return (200 if lacre.duplicado else 201), {
        "arquivo_id": lacre.arquivo_id,
        "estado": lacre.estado,
        "sha256": recebido.sha256,
        "tamanho_bytes": recebido.tamanho_bytes,
        "mime": recebido.tipo.value,
        "duplicado": lacre.duplicado,
    }


def cadastrar_por_arquivo(
    sessao: Session,
    storage: ObjectStorage,
    recebido: ArquivoRecebido,
    nome: str,
    ator: Ator,
    ctx: Contexto,
    settings: Settings,
    numero_cnj: str | None = None,
    classe: ClasseProcessual | None = None,
) -> tuple[int, dict[str, Any]]:
    """Identifica o temporário, encontra ou cria o processo e lacra o original (RF-PRO-01)."""
    numero_informado = numero_cnj is not None
    if numero_cnj is not None:
        try:
            numero_cnj = validar_numero_cnj(formatar_numero_cnj(numero_cnj))
        except NumeroCnjInvalidoError as erro:
            return 422, {"detail": str(erro)}
    leitura = ler_capa(recebido, settings)
    if isinstance(leitura, LeituraRecusada):
        auditar(
            sessao,
            ctx,
            AcaoAuditoria.UPLOAD,
            ResultadoEvento.NEGADO,
            hk_usuario=ator.hk_usuario,
            objeto_tipo="arquivo",
            objeto_id=recebido.sha256,
        )
        return 422, {
            "detail": "Arquivo recusado: " + leitura.motivo.value.replace("_", " "),
            "motivo": leitura.motivo.value,
        }
    lido = identificar(leitura.paginas)
    numero_lido = formatar_numero_cnj(lido.numero_cnj) if lido.numero_cnj else None
    numero = numero_cnj or numero_lido
    classe_nova = classe or lido.classe
    if numero is None or classe_nova is None:
        auditar(
            sessao,
            ctx,
            AcaoAuditoria.UPLOAD,
            ResultadoEvento.FALHA,
            hk_usuario=ator.hk_usuario,
            objeto_tipo="arquivo",
            objeto_id=recebido.sha256,
        )
        campos = {"numero_cnj": numero, "classe": classe_nova}
        return 422, {
            "detail": "Complete a identificação do processo.",
            "motivo": "identificacao_incompleta",
            "lido": {"numero_cnj": numero_lido, "classe": lido.classe},
            "faltando": [k for k, v in campos.items() if v is None],
            "numeros_encontrados": [formatar_numero_cnj(n) for n in lido.numeros_encontrados],
        }
    hk = chave_do_hub(hub_processo, {"numero_cnj": numero})
    chave = int.from_bytes(hk[:4], "big", signed=True)
    sessao.execute(select(func.pg_advisory_xact_lock(TRAVA_CADASTRO, chave)))
    processo = sessao.get(VisaoProcesso, hk)
    criado = processo is None
    origem_classe = "existente"
    if processo is None:
        gravar_processo(sessao, numero, classe_nova, ator)
        processo = sessao.get_one(VisaoProcesso, hk)
        auditar(
            sessao,
            ctx,
            AcaoAuditoria.PROCESSO_CRIADO,
            hk_usuario=ator.hk_usuario,
            hk_processo=hk,
            objeto_tipo="processo",
            objeto_id=processo.id,
        )
        origem_classe = "informado" if classe is not None else "lido"
    status, arquivo = _lacrar_envio(sessao, storage, recebido, nome, processo, ator, ctx)
    return status, arquivo | {
        "processo_id": processo.id,
        "numero_cnj": formatar_numero_cnj(processo.numero_cnj),
        "classe": processo.classe,
        "processo_criado": criado,
        "origem": {
            "numero_cnj": "informado" if numero_informado else "lido",
            "classe": origem_classe,
        },
    }


@router.post("/processos/arquivos", status_code=201)
async def enviar_processo(
    request: Request,
    ator: Remetente,
    sessao: SessaoBanco,
    ctx: ContextoReq,
    settings: Configuracao,
    nome: Annotated[str, Query(min_length=1, max_length=255)],
    numero_cnj: str | None = None,
    classe: ClasseProcessual | None = None,
) -> JSONResponse:
    """Recebe o original e identifica o processo antes da primeira gravação (RF-PRO-01)."""
    recebido = await _receber_envio(request, nome, settings, sessao, ator, ctx, None)
    if isinstance(recebido, JSONResponse):
        return recebido
    try:
        status, corpo = await run_in_threadpool(
            cadastrar_por_arquivo,
            sessao,
            request.app.state.storage,
            recebido,
            nome,
            ator,
            ctx,
            settings,
            numero_cnj,
            classe,
        )
        return JSONResponse(status_code=status, content=corpo)
    finally:
        recebido.caminho.unlink(missing_ok=True)


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
    recebido = await _receber_envio(
        request, nome, settings, sessao, ator, ctx, processo.hk_processo
    )
    if isinstance(recebido, JSONResponse):
        return recebido
    try:
        status, corpo = await run_in_threadpool(
            _lacrar_envio, sessao, request.app.state.storage, recebido, nome, processo, ator, ctx
        )
        return JSONResponse(status_code=status, content=corpo)
    finally:
        recebido.caminho.unlink(missing_ok=True)


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
