"""Visualizador: página do arquivo como imagem desenhada pela API e destaque da evidência.

A imagem é repassada da API pelo front (A6, D2). O destaque é um SVG sobre a imagem, com os
retângulos em fração da página nos atributos `x`, `y`, `width` e `height`, sem estilo inline.
"""

from dataclasses import dataclass
from typing import Any

import httpx
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from lupa_web import cliente_api, rotulos
from lupa_web.telas.sessao import (
    Sessao,
    contexto_da_moldura,
    nao_encontrado,
    obter,
    tela_autenticada,
)

ZOOM_MINIMO = 50
ZOOM_MAXIMO = 300
PASSO_ZOOM = 25
ZOOM_PADRAO = 100
ESTADOS_LEGIVEIS = frozenset({"concluido", "em_revisao"})
CASAS_DA_FRACAO = 4
TIPO_PADRAO = "image/png"
CACHE_PADRAO = "private"


def zoom_pedido(valor: str | None) -> int:
    """Zoom da URL, aceito só nos passos de 25% entre 50% e 300%.

    Args:
        valor: Parâmetro `zoom` da URL.

    Returns:
        O zoom em percentual, ou 100.
    """
    try:
        zoom = int(valor or "")
    except ValueError:
        return ZOOM_PADRAO
    if ZOOM_MINIMO <= zoom <= ZOOM_MAXIMO and zoom % PASSO_ZOOM == 0:
        return zoom
    return ZOOM_PADRAO


def _pagina_pedida(valor: str | None) -> int:
    try:
        return max(1, int(valor or ""))
    except ValueError:
        return 1


def _limitar(valor: float, maximo: float = 1.0) -> float:
    return min(max(valor, 0.0), maximo)


def retangulo_do_destaque(retangulo: dict[str, float]) -> dict[str, str]:
    """Retângulo recortado à página, em fração com ponto decimal, para os atributos do SVG.

    Args:
        retangulo: `{x, y, largura, altura}` em fração da página.

    Returns:
        Os quatro valores com quatro casas decimais.
    """
    x = _limitar(retangulo["x"])
    y = _limitar(retangulo["y"])
    largura = _limitar(retangulo["largura"], 1.0 - x)
    altura = _limitar(retangulo["altura"], 1.0 - y)
    valores = {"x": x, "y": y, "largura": largura, "altura": altura}
    return {chave: f"{valor:.{CASAS_DA_FRACAO}f}" for chave, valor in valores.items()}


def _legiveis(arquivos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [a for a in arquivos if a.get("total_paginas") and a.get("estado") in ESTADOS_LEGIVEIS]


@dataclass(frozen=True)
class Navegacao:
    """Posição atual e os endereços da página anterior, da próxima e dos passos de zoom."""

    base: str
    arquivo_id: str
    pagina: int
    total: int | None
    zoom: int

    def link(self, pagina: int, zoom: int) -> str:
        """Endereço do visualizador numa página e num zoom.

        Args:
            pagina: Página.
            zoom: Zoom em percentual.

        Returns:
            Caminho com `arquivo`, `pagina` e `zoom`.
        """
        return f"{self.base}/visualizador?arquivo={self.arquivo_id}&pagina={pagina}&zoom={zoom}"

    def contexto(self) -> dict[str, str]:
        """Links de navegação; vazio quando o passo não existe.

        Returns:
            `anterior`, `proxima`, `menos_zoom` e `mais_zoom`.
        """
        tem_proxima = self.total is None or self.pagina < self.total
        return {
            "anterior": self.link(self.pagina - 1, self.zoom) if self.pagina > 1 else "",
            "proxima": self.link(self.pagina + 1, self.zoom) if tem_proxima else "",
            "menos_zoom": (
                self.link(self.pagina, self.zoom - PASSO_ZOOM) if self.zoom > ZOOM_MINIMO else ""
            ),
            "mais_zoom": (
                self.link(self.pagina, self.zoom + PASSO_ZOOM) if self.zoom < ZOOM_MAXIMO else ""
            ),
        }


async def _destaque(
    request: HttpRequest, base: str, evidencia: str
) -> tuple[dict[str, Any] | None, str]:
    resposta = await obter(request, f"{base}/evidencias/{evidencia}/bbox")
    if resposta.is_error:
        return None, cliente_api.detalhe_do_erro(resposta)
    dados: dict[str, Any] = resposta.json()
    return dados, ""


@require_GET
@tela_autenticada
async def visualizador(request: HttpRequest, sessao: Sessao, processo_id: str) -> HttpResponse:
    """Página do arquivo como imagem, com o trecho da evidência destacado (RF-DOS-05).

    Args:
        request: Pedido com `evidencia`, ou `arquivo` e `pagina`, e `zoom`.
        sessao: Dados da sessão.
        processo_id: Identificador público do processo.

    Returns:
        Página do visualizador, ou 404 se a API não encontra o processo.
    """
    base = f"/processos/{processo_id}"
    resposta = await obter(request, f"{base}/arquivos")
    if resposta.status_code == httpx.codes.NOT_FOUND:
        return nao_encontrado(request, sessao)
    arquivos = resposta.json()["arquivos"]
    legiveis = _legiveis(arquivos)
    evidencia = request.GET.get("evidencia", "")
    destaque, erro = (None, "")
    if rotulos.IDENTIFICADOR.fullmatch(evidencia):
        destaque, erro = await _destaque(request, base, evidencia)
    if destaque:
        arquivo_id, pagina = destaque["arquivo_id"], int(destaque["pagina"])
    else:
        pedido = request.GET.get("arquivo", "")
        padrao = legiveis[0]["arquivo_id"] if legiveis else ""
        arquivo_id = pedido if rotulos.IDENTIFICADOR.fullmatch(pedido) else padrao
        pagina = _pagina_pedida(request.GET.get("pagina"))
    arquivo = next((a for a in arquivos if a["arquivo_id"] == arquivo_id), None)
    total = arquivo.get("total_paginas") if arquivo else None
    zoom = zoom_pedido(request.GET.get("zoom"))
    contexto = contexto_da_moldura(request, sessao) | {
        "processo_id": processo_id,
        "erro": erro,
        "legiveis": legiveis,
        "arquivo_id": arquivo_id,
        "pagina": pagina,
        "total": total,
        "zoom": zoom,
        "imagem": f"{base}/arquivos/{arquivo_id}/paginas/{pagina}/imagem",
        "destaque": destaque,
        "retangulos": [retangulo_do_destaque(r) for r in (destaque or {}).get("retangulos", [])],
        **Navegacao(base, arquivo_id, pagina, total, zoom).contexto(),
    }
    return render(request, "processos/visualizador.html", contexto)


@require_GET
async def imagem(
    request: HttpRequest, processo_id: str, arquivo_id: str, numero: int
) -> HttpResponse:
    """PNG da página repassado da API, com o tipo e o cache dela (A6).

    Args:
        request: Pedido do navegador.
        processo_id: Identificador público do processo.
        arquivo_id: Identificador público do arquivo.
        numero: Página no arquivo.

    Returns:
        A imagem, ou o status da API sem corpo quando não é 200.
    """
    caminho = f"/processos/{processo_id}/arquivos/{arquivo_id}/paginas/{numero}/imagem"
    resposta = await cliente_api.chamar(request, "GET", caminho)
    if resposta.status_code != httpx.codes.OK:
        return HttpResponse(status=resposta.status_code)
    saida = HttpResponse(
        resposta.content, content_type=resposta.headers.get("content-type", TIPO_PADRAO)
    )
    saida["Cache-Control"] = resposta.headers.get("cache-control", CACHE_PADRAO)
    return saida
