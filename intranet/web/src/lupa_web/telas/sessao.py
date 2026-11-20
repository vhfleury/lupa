"""Sessão da API nas telas autenticadas e contexto da moldura (A1, passo 7).

Toda tela autenticada consulta `GET /auth/sessao` antes de qualquer outra chamada: sem sessão o
`cliente_api` manda ao login; com troca de senha pendente a tela manda a `/trocar-senha`.
"""

import functools
from collections.abc import Callable, Coroutine
from typing import Any, Concatenate, ParamSpec

import httpx
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from lupa_web import cliente_api

CAMINHO_TROCA = "/trocar-senha"
ROTULO_PAPEL = {"assessor": "Assessor", "desembargador": "Desembargador"}
ITENS_DO_MENU = (
    ("/", "Início", ""),
    ("/processos", "Processos", "ver_processo"),
    ("/usuarios", "Usuários", "gerir_assessor"),
    ("/auditoria", "Auditoria", "ver_auditoria"),
)

Sessao = dict[str, Any]
Parametros = ParamSpec("Parametros")
Resposta = Coroutine[Any, Any, HttpResponse]
TelaComSessao = Callable[Concatenate[HttpRequest, Sessao, Parametros], Resposta]
Tela = Callable[Concatenate[HttpRequest, Parametros], Resposta]


async def obter_sessao(request: HttpRequest) -> Sessao:
    """Dados da sessão corrente na API.

    Args:
        request: Pedido do navegador.

    Returns:
        Corpo de `GET /auth/sessao`.
    """
    resposta = await cliente_api.chamar(request, "GET", "/auth/sessao")
    dados: Sessao = resposta.json()
    return dados


def tem(sessao: Sessao, permissao: str) -> bool:
    """Se o papel da sessão tem a permissão (só para esconder ações; a API reconfere).

    Args:
        sessao: Dados da sessão.
        permissao: Nome da permissão da matriz da API.

    Returns:
        Verdadeiro se a permissão está na sessão.
    """
    return permissao in sessao.get("permissoes", [])


def tela_autenticada(view: TelaComSessao[Parametros]) -> Tela[Parametros]:
    """Envolve a view: confere a sessão e exige a troca de senha pendente antes de tudo.

    Args:
        view: View que recebe o pedido e os dados da sessão.

    Returns:
        View que recebe só o pedido.
    """

    async def envolvida(
        request: HttpRequest, /, *args: Parametros.args, **kwargs: Parametros.kwargs
    ) -> HttpResponse:
        sessao = await obter_sessao(request)
        if sessao.get("troca_senha_obrigatoria") and request.path != CAMINHO_TROCA:
            return cliente_api.redirecionar(request, CAMINHO_TROCA)
        return await view(request, sessao, *args, **kwargs)

    functools.update_wrapper(envolvida, view)
    return envolvida


def contexto_da_moldura(request: HttpRequest, sessao: Sessao) -> dict[str, Any]:
    """Contexto do cabeçalho e do menu lateral, conforme o papel.

    Args:
        request: Pedido do navegador.
        sessao: Dados da sessão.

    Returns:
        `sessao`, `moldura`, `rotulo_papel` e os `itens_menu` permitidos, com o item corrente.
    """
    caminho = request.path
    itens = [
        {
            "href": href,
            "rotulo": rotulo,
            "atual": caminho == href or (href != "/" and caminho.startswith(f"{href}/")),
        }
        for href, rotulo, permissao in ITENS_DO_MENU
        if not permissao or tem(sessao, permissao)
    ]
    return {
        "sessao": sessao,
        "moldura": not sessao.get("troca_senha_obrigatoria"),
        "rotulo_papel": ROTULO_PAPEL.get(str(sessao.get("papel")), ""),
        "itens_menu": itens,
    }


def nao_encontrado(request: HttpRequest, sessao: Sessao) -> HttpResponse:
    """Página "não encontrado" com a moldura, status 404.

    Args:
        request: Pedido do navegador.
        sessao: Dados da sessão.

    Returns:
        Resposta 404.
    """
    contexto = contexto_da_moldura(request, sessao)
    return render(request, "erros/nao_encontrado.html", contexto, status=404)


async def obter(request: HttpRequest, caminho: str) -> httpx.Response:
    """`GET` na API em nome do navegador.

    Args:
        request: Pedido do navegador.
        caminho: Caminho da rota na API.

    Returns:
        Resposta da API.
    """
    return await cliente_api.chamar(request, "GET", caminho)
