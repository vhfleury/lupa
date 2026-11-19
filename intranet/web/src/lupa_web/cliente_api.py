"""Chamada do Django à API do Lupa (A1, D1, D3, D13).

Um `httpx.AsyncClient` único por processo, sem guardar cookie: cada chamada leva o cookie de
sessão do navegador e o `X-Forwarded-For` do proxy. O middleware `DesviosDaApi` copia para a
resposta todo `Set-Cookie` da API e transforma 401, 403 e falha de conexão nas respostas da tela.
"""

import http.cookiejar
import logging
import os
from typing import Any

import httpx
from django.http import HttpRequest, HttpResponse, HttpResponseBase, HttpResponseRedirect
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin

NOME_COOKIE = "lupa_sessao"
URL_API_PADRAO = "http://api:8000"
PRAZO_API_PADRAO = "30"
PRAZO_CHAT_PADRAO = "180"
CHAVE_SET_COOKIE = "lupa_web.set_cookie"
CAMINHO_LOGIN = "/login"

logger = logging.getLogger(__name__)

_clientes: list[httpx.AsyncClient] = []


class DesvioDaApiError(Exception):
    """Resposta da API que interrompe a tela (A1, passos 3, 5 e 6)."""


class ApiIndisponivelError(DesvioDaApiError):
    """A API não respondeu no prazo ou a conexão falhou."""


class SessaoExpiradaError(DesvioDaApiError):
    """A API respondeu 401."""


class AcessoNegadoError(DesvioDaApiError):
    """A API respondeu 403."""


def prazo(longo: bool) -> float:
    """Prazo da chamada em segundos (D13).

    Args:
        longo: Verdadeiro para a pergunta do chat e o envio de arquivo.

    Returns:
        `LUPA_WEB_TIMEOUT_CHAT` (padrão 180) se longo, senão `LUPA_WEB_TIMEOUT_API` (padrão 30).
    """
    if longo:
        return float(os.environ.get("LUPA_WEB_TIMEOUT_CHAT", PRAZO_CHAT_PADRAO))
    return float(os.environ.get("LUPA_WEB_TIMEOUT_API", PRAZO_API_PADRAO))


def obter_cliente() -> httpx.AsyncClient:
    """Cliente HTTP do processo, criado na primeira chamada e sem pote de cookies.

    Returns:
        O `httpx.AsyncClient` compartilhado, apontado para `LUPA_WEB_API_URL`.
    """
    if not _clientes:
        recusa_tudo = http.cookiejar.DefaultCookiePolicy(allowed_domains=[])
        _clientes.append(
            httpx.AsyncClient(
                base_url=os.environ.get("LUPA_WEB_API_URL", URL_API_PADRAO),
                cookies=http.cookiejar.CookieJar(policy=recusa_tudo),
            )
        )
    return _clientes[0]


async def encerrar_cliente() -> None:
    """Fecha o cliente compartilhado, se houver; a próxima chamada cria outro."""
    while _clientes:
        await _clientes.pop().aclose()


def cabecalhos_de_repasse(request: HttpRequest) -> dict[str, str]:
    """Cabeçalhos que acompanham o pedido do navegador até a API (A1, passo 1).

    Args:
        request: Pedido do navegador.

    Returns:
        `X-Forwarded-For` do proxy (ou o IP da conexão) e o cookie de sessão, se houver.
    """
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR", "")
    cabecalhos = {"X-Forwarded-For": encaminhado}
    sessao = request.COOKIES.get(NOME_COOKIE)
    if sessao:
        cabecalhos["Cookie"] = f"{NOME_COOKIE}={sessao}"
    return cabecalhos


async def chamar(
    request: HttpRequest,
    metodo: str,
    caminho: str,
    *,
    longo: bool = False,
    **opcoes: Any,
) -> httpx.Response:
    """Chama a API em nome do navegador, sem tentar de novo (A1, passos 2 a 6).

    Args:
        request: Pedido do navegador.
        metodo: Método HTTP.
        caminho: Caminho da rota na API.
        longo: Usa o prazo do chat e do envio de arquivo (D13).
        **opcoes: Corpo e parâmetros repassados ao `httpx` (`json`, `data`, `params`...).

    Returns:
        Resposta da API, com status diferente de 401 e 403.

    Raises:
        ApiIndisponivelError: Prazo esgotado ou falha de conexão.
        SessaoExpiradaError: A API respondeu 401.
        AcessoNegadoError: A API respondeu 403.
    """
    try:
        resposta = await obter_cliente().request(
            metodo,
            caminho,
            headers=cabecalhos_de_repasse(request),
            timeout=prazo(longo),
            **opcoes,
        )
    except httpx.TransportError as erro:
        logger.warning(
            "api_indisponivel metodo=%s caminho=%s erro=%s",
            metodo,
            caminho.split("?", 1)[0],
            type(erro).__name__,
        )
        raise ApiIndisponivelError from erro
    request.META.setdefault(CHAVE_SET_COOKIE, []).extend(resposta.headers.get_list("set-cookie"))
    if resposta.status_code == httpx.codes.UNAUTHORIZED:
        raise SessaoExpiradaError
    if resposta.status_code == httpx.codes.FORBIDDEN:
        raise AcessoNegadoError
    return resposta


def redirecionar_para_login(request: HttpRequest) -> HttpResponse:
    """Manda o navegador para `/login`: 303 ou, em pedido HTMX, `HX-Redirect` (A1, passo 5).

    Args:
        request: Pedido do navegador.

    Returns:
        Resposta de redirecionamento.
    """
    if request.headers.get("HX-Request") == "true":
        resposta = HttpResponse()
        resposta["HX-Redirect"] = CAMINHO_LOGIN
        return resposta
    resposta = HttpResponseRedirect(CAMINHO_LOGIN)
    resposta.status_code = 303
    return resposta


class DesviosDaApi(MiddlewareMixin):
    """Transforma os desvios da API em respostas e copia o `Set-Cookie` da API (A1)."""

    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse | None:
        """Resposta da tela para cada desvio da API; outras exceções seguem adiante.

        Args:
            request: Pedido do navegador.
            exception: Exceção levantada pela view.

        Returns:
            502, redirecionamento para `/login` ou 403; `None` para exceção que não é da API.
        """
        if isinstance(exception, ApiIndisponivelError):
            return render(request, "erros/servico_indisponivel.html", status=502)
        if isinstance(exception, SessaoExpiradaError):
            return redirecionar_para_login(request)
        if isinstance(exception, AcessoNegadoError):
            return render(request, "erros/acesso_negado.html", status=403)
        return None

    def process_response(
        self, request: HttpRequest, response: HttpResponseBase
    ) -> HttpResponseBase:
        """Copia cada `Set-Cookie` recebido da API para a resposta ao navegador (A1, passo 4).

        Args:
            request: Pedido do navegador.
            response: Resposta da tela.

        Returns:
            A mesma resposta, com os cookies da API.
        """
        for valor in request.META.get(CHAVE_SET_COOKIE, []):
            response.cookies.load(valor)
        return response
