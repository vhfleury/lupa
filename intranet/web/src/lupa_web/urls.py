"""Rotas do front: saúde do contêiner e uma rota por tela da RF-INT-02."""

from django.http import HttpRequest, HttpResponse
from django.urls import path

from lupa_web.telas import acesso, dossie, envio, processo, processos, validacoes, visualizador


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
    path("processos", processos.lista, name="processos"),
    path("processos/envio", envio.novo, name="envio"),
    path("processos/envio/complemento", envio.complemento, name="complemento"),
    path("processos/<str:processo_id>", processo.processo, name="processo"),
    path("processos/<str:processo_id>/envio", envio.anexo, name="anexo"),
    path("processos/<str:processo_id>/estado", processo.estado, name="estado"),
    path("processos/<str:processo_id>/classe", processo.corrigir_classe, name="classe"),
    path("processos/<str:processo_id>/responsaveis", processo.distribuir, name="responsaveis"),
    path("processos/<str:processo_id>/descartar", processo.descartar, name="descartar"),
    path("processos/<str:processo_id>/arquivos/<str:arquivo_id>", processo.arquivo, name="arquivo"),
    path(
        "processos/<str:processo_id>/arquivos/<str:arquivo_id>/paginas/<int:numero>/imagem",
        visualizador.imagem,
        name="imagem",
    ),
    path("processos/<str:processo_id>/dossie", dossie.dossie, name="dossie"),
    path(
        "processos/<str:processo_id>/pecas/<str:peca_id>/reclassificar",
        dossie.reclassificar,
        name="reclassificar",
    ),
    path("processos/<str:processo_id>/validacoes", validacoes.validacoes, name="validacoes"),
    path(
        "processos/<str:processo_id>/fatos/<str:fato_id>/corrigir",
        validacoes.corrigir,
        name="corrigir_fato",
    ),
    path("processos/<str:processo_id>/anotacoes", validacoes.anotar, name="anotar"),
    path(
        "processos/<str:processo_id>/visualizador", visualizador.visualizador, name="visualizador"
    ),
    path("", acesso.inicio, name="inicio"),
]
