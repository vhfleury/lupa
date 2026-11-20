"""Testes de `lupa_web.cliente_api`: chamada do Django à API (A1, D3, D13)."""

import asyncio
import logging
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
import respx
from django.http import HttpResponse
from django.test import Client, RequestFactory

from lupa_web import cliente_api

pytestmark = pytest.mark.urls("tests.unit.rotas_de_teste")

API = "http://api:8000"
COOKIE_NAVEGADOR = "sessao-sintetica-do-navegador"
COOKIE_RENOVADO = "sessao-sintetica-renovada"
ATRIBUTOS_DO_COOKIE = "HttpOnly; Path=/; SameSite=strict; Secure"


@pytest.fixture(autouse=True)
def api_simulada(monkeypatch: pytest.MonkeyPatch) -> Iterator[respx.MockRouter]:
    """API simulada pelo `respx` em `LUPA_WEB_API_URL`, com cliente novo por teste."""
    monkeypatch.setenv("LUPA_WEB_API_URL", API)
    asyncio.run(cliente_api.encerrar_cliente())
    with respx.mock(base_url=API, assert_all_called=False) as roteador:
        yield roteador
    asyncio.run(cliente_api.encerrar_cliente())


def _atender(
    caminho: str = "/auth/sessao",
    longo: bool = False,
    cookie: str | None = None,
    **cabecalhos: Any,
) -> HttpResponse:
    cliente = Client(**cabecalhos)
    if cookie is not None:
        cliente.cookies[cliente_api.NOME_COOKIE] = cookie
    consulta = {"caminho": caminho, "longo": "1" if longo else "0"}
    resposta = cliente.get("/tela", consulta)
    assert isinstance(resposta, HttpResponse)
    return resposta


def test_cookie_da_api_e_repassado_e_set_cookie_volta(api_simulada: respx.MockRouter) -> None:
    """RF-INT-03 (D3): o cookie do navegador vai à API e o `Set-Cookie` da API volta."""
    rota = api_simulada.get("/auth/sessao").respond(
        200,
        json={"usuario": "sintetico"},
        headers={"set-cookie": f"lupa_sessao={COOKIE_RENOVADO}; {ATRIBUTOS_DO_COOKIE}"},
    )
    resposta = _atender(cookie=COOKIE_NAVEGADOR)

    assert rota.calls.last.request.headers["cookie"] == f"lupa_sessao={COOKIE_NAVEGADOR}"
    cookie = resposta.cookies[cliente_api.NOME_COOKIE]
    assert cookie.value == COOKIE_RENOVADO
    assert cookie["httponly"] is True
    assert cookie["secure"] is True
    assert cookie["samesite"] == "strict"


def test_cliente_compartilhado_nao_guarda_cookie_entre_pedidos(
    api_simulada: respx.MockRouter,
) -> None:
    """RF-INT-03 (D1): o cookie devolvido a um usuário não vai no pedido de outro."""
    rota = api_simulada.get("/auth/sessao").respond(
        200, headers={"set-cookie": f"lupa_sessao={COOKIE_RENOVADO}; Path=/"}
    )
    _atender()
    _atender()
    assert rota.call_count == 2
    assert "cookie" not in rota.calls.last.request.headers


def test_x_forwarded_for_e_repassado(api_simulada: respx.MockRouter) -> None:
    """RF-INT-03 (P4): o IP do cliente posto pelo Caddy chega à API em `X-Forwarded-For`."""
    rota = api_simulada.get("/auth/sessao").respond(200, json={})
    _atender(HTTP_X_FORWARDED_FOR="203.0.113.7")
    assert rota.calls.last.request.headers["x-forwarded-for"] == "203.0.113.7"


def test_sem_x_forwarded_for_repassa_o_ip_da_conexao(api_simulada: respx.MockRouter) -> None:
    """RF-INT-03 (P4): sem o cabeçalho do proxy, vai o endereço da conexão."""
    rota = api_simulada.get("/auth/sessao").respond(200, json={})
    _atender(REMOTE_ADDR="198.51.100.2")
    assert rota.calls.last.request.headers["x-forwarded-for"] == "198.51.100.2"


@pytest.mark.parametrize(
    "falha",
    [httpx.ConnectError("recusada"), httpx.ReadTimeout("prazo esgotado")],
)
def test_api_fora_do_ar_mostra_servico_indisponivel(
    api_simulada: respx.MockRouter, falha: Exception, caplog: pytest.LogCaptureFixture
) -> None:
    """RF-INT-03 (A1.3): falha ou prazo esgotado vira 502 "Serviço indisponível", uma chamada."""
    rota = api_simulada.get("/auth/sessao").mock(side_effect=falha)
    with caplog.at_level(logging.WARNING):
        resposta = _atender(cookie=COOKIE_NAVEGADOR)

    assert resposta.status_code == 502
    assert "Serviço indisponível" in resposta.content.decode()
    assert rota.call_count == 1
    assert "api_indisponivel" in caplog.text
    assert COOKIE_NAVEGADOR not in caplog.text


def test_sessao_expirada_redireciona_para_login(api_simulada: respx.MockRouter) -> None:
    """RF-INT-03 (A1.5): 401 da API vira 303 para `/login`, com o `Set-Cookie` copiado."""
    api_simulada.get("/auth/sessao").respond(
        401, headers={"set-cookie": "lupa_sessao=; Max-Age=0; Path=/"}
    )
    resposta = _atender()
    assert resposta.status_code == 303
    assert resposta["Location"] == "/login"
    assert resposta.cookies[cliente_api.NOME_COOKIE]["max-age"] == "0"


def test_pedido_htmx_com_sessao_expirada_recebe_hx_redirect(
    api_simulada: respx.MockRouter,
) -> None:
    """RF-INT-03 (A1.5): em pedido HTMX o 401 vira o cabeçalho `HX-Redirect: /login`."""
    api_simulada.get("/auth/sessao").respond(401)
    resposta = _atender(HTTP_HX_REQUEST="true")
    assert resposta.status_code == 200
    assert resposta["HX-Redirect"] == "/login"


def test_acesso_negado_mostra_pagina_com_403(api_simulada: respx.MockRouter) -> None:
    """RF-INT-03 (A1.6): 403 da API vira a página "Acesso negado" com status 403."""
    api_simulada.get("/auditoria").respond(403, json={"detail": "sem permissão"})
    resposta = _atender(caminho="/auditoria")
    assert resposta.status_code == 403
    assert "Acesso negado" in resposta.content.decode()


def test_resposta_comum_volta_para_a_tela(api_simulada: respx.MockRouter) -> None:
    """RF-INT-03 (A1.9): resposta 200 chega à view como veio da API."""
    api_simulada.get("/auth/sessao").respond(200, text="conteudo-sintetico")
    resposta = _atender()
    assert resposta.status_code == 200
    assert resposta.content == b"conteudo-sintetico"


def test_prazos_vem_das_variaveis_de_ambiente(
    api_simulada: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RF-INT-03 (D13): prazo comum de `LUPA_WEB_TIMEOUT_API`, longo de `LUPA_WEB_TIMEOUT_CHAT`."""
    monkeypatch.setenv("LUPA_WEB_TIMEOUT_API", "7")
    monkeypatch.setenv("LUPA_WEB_TIMEOUT_CHAT", "90")
    rota = api_simulada.get("/auth/sessao").respond(200)
    _atender()
    assert rota.calls.last.request.extensions["timeout"]["read"] == 7.0
    _atender(longo=True)
    assert rota.calls.last.request.extensions["timeout"]["read"] == 90.0


def test_prazos_padrao_sao_30_e_180_segundos(monkeypatch: pytest.MonkeyPatch) -> None:
    """RF-INT-03 (D13): sem variável, 30 s para as rotas comuns e 180 s para chat e envio."""
    monkeypatch.delenv("LUPA_WEB_TIMEOUT_API", raising=False)
    monkeypatch.delenv("LUPA_WEB_TIMEOUT_CHAT", raising=False)
    assert cliente_api.prazo(longo=False) == 30.0
    assert cliente_api.prazo(longo=True) == 180.0


def test_excecao_que_nao_e_da_api_segue_adiante() -> None:
    """RF-INT-03 (A1): o middleware só trata os desvios da API; o resto chega ao Django."""
    middleware = cliente_api.DesviosDaApi(lambda pedido: HttpResponse())
    assert middleware.process_exception(RequestFactory().get("/"), ValueError()) is None


@pytest.mark.parametrize(
    ("resposta", "esperado"),
    [
        (httpx.Response(422, json={"detail": "senha muito comum"}), "Senha muito comum."),
        (httpx.Response(409, json={"detail": "Recarregue a lista."}), "Recarregue a lista."),
        (httpx.Response(422, json={"detail": [{"msg": "x"}]}), cliente_api.MENSAGEM_GENERICA),
        (httpx.Response(500, text="sem json"), cliente_api.MENSAGEM_GENERICA),
        (httpx.Response(400, json=["lista"]), cliente_api.MENSAGEM_GENERICA),
    ],
)
def test_detalhe_do_erro_vira_frase_da_tela(resposta: httpx.Response, esperado: str) -> None:
    """RF-INT-03 (A1.8): o `detail` em texto da API vira frase; o resto, mensagem genérica."""
    assert cliente_api.detalhe_do_erro(resposta) == esperado


def test_cliente_e_um_por_loop_de_eventos() -> None:
    """RF-INT-03 (D1): no mesmo loop o cliente é o mesmo; num loop novo, outro cliente."""

    async def cliente_duas_vezes() -> tuple[httpx.AsyncClient, httpx.AsyncClient]:
        return cliente_api.obter_cliente(), cliente_api.obter_cliente()

    primeiro, repetido = asyncio.run(cliente_duas_vezes())
    segundo, _ = asyncio.run(cliente_duas_vezes())
    assert primeiro is repetido
    assert segundo is not primeiro
    asyncio.run(cliente_api.encerrar_cliente())


def test_encerrar_fecha_o_cliente_do_proprio_loop() -> None:
    """RF-INT-03 (D1): no `lifespan.shutdown`, o cliente do loop do servidor é fechado."""

    async def criar_e_encerrar() -> httpx.AsyncClient:
        cliente = cliente_api.obter_cliente()
        await cliente_api.encerrar_cliente()
        return cliente

    assert asyncio.run(criar_e_encerrar()).is_closed


def test_log_do_httpx_nao_registra_a_consulta(
    api_simulada: respx.MockRouter, caplog: pytest.LogCaptureFixture
) -> None:
    """RF-INT-04: nome do arquivo e número CNJ na consulta da API não vão para o log."""
    api_simulada.get("/auth/sessao").respond(200)
    with caplog.at_level(logging.INFO):
        _atender(caminho="/auth/sessao?nome=autos-0000001.pdf&numero_cnj=0000001")
    assert "autos-0000001" not in caplog.text
    assert "numero_cnj" not in caplog.text
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
