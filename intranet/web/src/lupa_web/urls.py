"""Rotas do front: saúde do contêiner e página inicial; as telas entram a partir da T10.6."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import path


async def saude(request: HttpRequest) -> HttpResponse:
    """Responde `ok` para o healthcheck do contêiner, sem chamar a API.

    Args:
        request: Pedido HTTP.

    Returns:
        Resposta 200 em texto puro.
    """
    return HttpResponse("ok", content_type="text/plain; charset=utf-8")


async def inicio(request: HttpRequest) -> HttpResponse:
    """Mostra a página inicial mínima do front.

    Args:
        request: Pedido HTTP.

    Returns:
        Página HTML com o nome do sistema.
    """
    return render(request, "inicio.html")


urlpatterns = [
    path("saude", saude, name="saude"),
    path("", inicio, name="inicio"),
]
