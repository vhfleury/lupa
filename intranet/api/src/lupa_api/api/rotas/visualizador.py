"""Renderização de páginas e localização de evidências do processo (RF-DOS-05)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select

from lupa_api.acesso.autorizacao import SessaoBanco, exige_processo
from lupa_api.acesso.erros import NaoEncontradoError
from lupa_api.api.middleware import auditar_rota
from lupa_api.auditoria.eventos import AcaoAuditoria
from lupa_pipeline.dominio.visoes import VisaoArquivo, VisaoEvidencia, VisaoPagina, VisaoProcesso
from lupa_pipeline.ingestao import renderizacao
from lupa_pipeline.ingestao.recepcao import TipoArquivo
from lupa_pipeline.ingestao.storage import chave_objeto

router = APIRouter()

Processo = Annotated[VisaoProcesso, Depends(exige_processo)]
MENSAGEM_INDISPONIVEL = "página indisponível para visualização"


def _linhas(coordenadas: dict[str, Any]) -> list[dict[str, Any]]:
    if "blocos" in coordenadas:
        return [linha for bloco in coordenadas["blocos"] for linha in bloco.get("linhas", [])]
    return list(coordenadas.get("linhas", []))


def caixas_da_evidencia(
    coordenadas: dict[str, Any], inicio: int, fim: int
) -> list[tuple[float, float, float, float]]:
    """Caixas (em pontos) das linhas que contêm algum caractere de `[inicio, fim)`.

    Args:
        coordenadas: `pagina.coordenadas`.
        inicio: Offset inicial no texto da página.
        fim: Offset final (exclusivo).

    Returns:
        Caixas `(x0, y0, x1, y1)` na ordem das linhas; vazia se não há coordenadas.
    """
    caixas = []
    for linha in _linhas(coordenadas):
        if "inicio" not in linha or "fim" not in linha or "bbox" not in linha:
            continue
        if int(linha["inicio"]) < fim and int(linha["fim"]) > inicio:
            x0, y0, x1, y1 = (float(v) for v in linha["bbox"])
            caixas.append((x0, y0, x1, y1))
    return caixas


def fracao(
    caixa: tuple[float, float, float, float], largura: float, altura: float
) -> dict[str, float]:
    """Converte uma caixa em pontos para fração da página, recortada a `[0, 1]`.

    Args:
        caixa: `(x0, y0, x1, y1)` em pontos.
        largura: Largura da página em pontos.
        altura: Altura da página em pontos.

    Returns:
        `{x, y, largura, altura}` em fração da página.
    """

    def _limitar(valor: float) -> float:
        return min(max(valor, 0.0), 1.0)

    x0, y0 = _limitar(caixa[0] / largura), _limitar(caixa[1] / altura)
    x1, y1 = _limitar(caixa[2] / largura), _limitar(caixa[3] / altura)
    return {"x": x0, "y": y0, "largura": max(x1 - x0, 0.0), "altura": max(y1 - y0, 0.0)}


def _uniao(caixas: list[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    return (
        min(c[0] for c in caixas),
        min(c[1] for c in caixas),
        max(c[2] for c in caixas),
        max(c[3] for c in caixas),
    )


def _origem(arquivo: VisaoArquivo, pagina: VisaoPagina) -> tuple[str, int]:
    """Chave do PDF de origem no storage e o número da página dentro dele."""
    if not arquivo.chave_storage:
        raise NaoEncontradoError(MENSAGEM_INDISPONIVEL)
    if arquivo.mime != TipoArquivo.ZIP.value or not pagina.origem_arquivo:
        return arquivo.chave_storage, pagina.pagina_origem or pagina.numero
    for entrada in arquivo.manifesto or []:
        if entrada.get("nome") == pagina.origem_arquivo:
            chave = chave_objeto(arquivo.hk_processo, entrada["sha256"])
            return chave, pagina.pagina_origem or 1
    raise NaoEncontradoError(MENSAGEM_INDISPONIVEL)


def _pagina(
    sessao: SessaoBanco, processo: VisaoProcesso, arquivo_id: str, numero: int
) -> tuple[VisaoArquivo, VisaoPagina]:
    arquivo = sessao.scalar(
        select(VisaoArquivo).where(
            VisaoArquivo.id == arquivo_id, VisaoArquivo.hk_processo == processo.hk_processo
        )
    )
    if arquivo is None or arquivo.processo_id != processo.id:
        raise NaoEncontradoError("arquivo não encontrado")
    pagina = sessao.scalar(
        select(VisaoPagina).where(
            VisaoPagina.arquivo_id == arquivo_id, VisaoPagina.numero == numero
        )
    )
    if pagina is None:
        raise NaoEncontradoError("página não encontrada")
    return arquivo, pagina


@router.get("/processos/{processo_id}/arquivos/{arquivo_id}/paginas/{numero}/imagem")
@auditar_rota(AcaoAuditoria.PAGINA_VISTA, conteudo=True)
def imagem_pagina(
    request: Request,
    processo: Processo,
    arquivo_id: str,
    numero: int,
    sessao: SessaoBanco,
    zoom: Annotated[
        float, Query(ge=renderizacao.ZOOM_MINIMO, le=renderizacao.ZOOM_MAXIMO)
    ] = renderizacao.ZOOM_PADRAO,
) -> Response:
    """PNG da página do arquivo, renderizado no servidor a partir do original.

    Args:
        request: Requisição (storage da aplicação).
        processo: Processo autorizado.
        arquivo_id: Arquivo do processo.
        numero: Página no arquivo (numeração contínua da ingestão).
        sessao: Sessão da requisição.
        zoom: Escala (1.0 = 72 dpi).

    Returns:
        `image/png` com `Cache-Control: private`, ou 503 se a página não pôde ser desenhada.
    """
    arquivo, pagina = _pagina(sessao, processo, arquivo_id, numero)
    chave, numero_origem = _origem(arquivo, pagina)
    try:
        imagem = renderizacao.renderizar(request.app.state.storage, chave, numero_origem, zoom)
    except renderizacao.RenderizacaoError:
        return JSONResponse(status_code=503, content={"detail": MENSAGEM_INDISPONIVEL})
    return Response(
        content=imagem.png,
        media_type="image/png",
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
            "X-Lupa-Pagina-Largura": f"{imagem.largura:.2f}",
            "X-Lupa-Pagina-Altura": f"{imagem.altura:.2f}",
        },
    )


@router.get("/processos/{processo_id}/evidencias/{evidencia_id}/bbox")
@auditar_rota(AcaoAuditoria.PROCESSO_ABERTO, conteudo=True)
def bbox_evidencia(
    request: Request, processo: Processo, evidencia_id: str, sessao: SessaoBanco
) -> dict[str, Any]:
    """Onde está o trecho da evidência: arquivo, página e retângulos em fração da página.

    Args:
        request: Requisição (storage, para o tamanho da página).
        processo: Processo autorizado.
        evidencia_id: Evidência de fato ou de peça do processo.
        sessao: Sessão da requisição.

    Returns:
        `{evidencia_id, arquivo_id, pagina, trecho, uniao, retangulos, sistema}`; `uniao` é
        None quando a página não tem coordenadas (página vazia ou sem texto localizável).

    Raises:
        NaoEncontradoError: Evidência inexistente ou de outro processo.
    """
    linha = sessao.execute(
        select(VisaoEvidencia, VisaoPagina, VisaoArquivo)
        .join(VisaoPagina, VisaoPagina.id == VisaoEvidencia.pagina_id)
        .join(VisaoArquivo, VisaoArquivo.id == VisaoPagina.arquivo_id)
        .where(
            VisaoEvidencia.id == evidencia_id, VisaoEvidencia.hk_processo == processo.hk_processo
        )
    ).one_or_none()
    if linha is None or linha[2].processo_id != processo.id:
        raise NaoEncontradoError("evidência não encontrada")
    evidencia, pagina, arquivo = linha
    caixas = caixas_da_evidencia(pagina.coordenadas or {}, evidencia.inicio, evidencia.fim)
    corpo: dict[str, Any] = {
        "evidencia_id": str(evidencia.id),
        "arquivo_id": str(arquivo.id),
        "pagina": pagina.numero,
        "trecho": evidencia.trecho,
        "sistema": "fracao_da_pagina_origem_superior_esquerda",
        "uniao": None,
        "retangulos": [],
    }
    if not caixas:
        return corpo
    chave, numero_origem = _origem(arquivo, pagina)
    try:
        medida = renderizacao.renderizar(request.app.state.storage, chave, numero_origem)
    except renderizacao.RenderizacaoError:
        return corpo
    corpo["uniao"] = fracao(_uniao(caixas), medida.largura, medida.altura)
    corpo["retangulos"] = [fracao(c, medida.largura, medida.altura) for c in caixas]
    return corpo
