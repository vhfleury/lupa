"""Rotas do front: saúde do contêiner e uma rota por tela da RF-INT-02."""

from django.http import HttpRequest, HttpResponse
from django.urls import path

from lupa_web.telas import acesso


async def saude(request: HttpRequest) -> HttpResponse:
    """Responde `ok` para o healthcheck do contêiner, sem chamar a API.

    Args:
        request: Pedido HTTP.

    Returns:
        Resposta 200 em texto puro.
    """
    return HttpResponse("ok", content_type="text/plain; charset=utf-8")


urlpatterns = [
    path("saude", saude, name="saude"),
    path("login", acesso.login, name="login"),
    path("login/codigo", acesso.login_codigo, name="login_codigo"),
    path("trocar-senha", acesso.trocar_senha, name="trocar_senha"),
    path("sair", acesso.sair, name="sair"),
    path("", acesso.inicio, name="inicio"),
]
