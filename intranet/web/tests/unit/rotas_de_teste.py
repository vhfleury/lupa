"""Rotas só de teste: uma tela que chama a API pelo `cliente_api`."""

from django.http import HttpRequest, HttpResponse
from django.urls import path

from lupa_web import cliente_api


async def tela_que_chama_a_api(request: HttpRequest) -> HttpResponse:
    """Chama a API no caminho de `?caminho=` e devolve o texto da resposta.

    Args:
        request: Pedido do navegador; `?longo=1` usa o prazo do chat.

    Returns:
        Resposta com o texto da API.
    """
    caminho = request.GET.get("caminho", "/auth/sessao")
    longo = request.GET.get("longo") == "1"
    resposta_api = await cliente_api.chamar(request, "GET", caminho, longo=longo)
    return HttpResponse(resposta_api.text)


urlpatterns = [path("tela", tela_que_chama_a_api)]
