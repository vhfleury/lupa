"""Fixtures das telas: API simulada pelo `respx` e sessões sintéticas por papel."""

import asyncio
from collections.abc import Iterator
from typing import Any

import pytest
import respx
from django.test import Client

from lupa_web import cliente_api

API = "http://api:8000"
COOKIE_SINTETICO = "sessao-sintetica"

PERMISSOES = {
    "assessor": ["anotar", "subir_processo", "ver_processo"],
    "desembargador": [
        "anotar",
        "gerir_assessor",
        "resetar_assessor",
        "subir_processo",
        "ver_auditoria",
        "ver_processo",
    ],
}


def sessao_da_api(papel: str = "assessor", troca: bool = False) -> dict[str, Any]:
    """Corpo sintético de `GET /auth/sessao` para o papel.

    Args:
        papel: `assessor` ou `desembargador`.
        troca: Se a troca de senha é obrigatória.

    Returns:
        Dados da sessão como a API devolve.
    """
    return {
        "usuario_id": "ab" * 32,
        "nome_usuario": f"{papel}.sintetico",
        "papel": papel,
        "troca_senha_obrigatoria": troca,
        "permissoes": PERMISSOES[papel],
    }


@pytest.fixture(autouse=True)
def api_simulada(monkeypatch: pytest.MonkeyPatch) -> Iterator[respx.MockRouter]:
    """API simulada em `LUPA_WEB_API_URL`, com cliente novo por teste."""
    monkeypatch.setenv("LUPA_WEB_API_URL", API)
    asyncio.run(cliente_api.encerrar_cliente())
    with respx.mock(base_url=API, assert_all_called=False) as roteador:
        yield roteador
    asyncio.run(cliente_api.encerrar_cliente())


@pytest.fixture
def navegador() -> Client:
    """Navegador com o cookie de sessão sintético da API."""
    cliente = Client()
    cliente.cookies[cliente_api.NOME_COOKIE] = COOKIE_SINTETICO
    return cliente


@pytest.fixture
def logado(api_simulada: respx.MockRouter) -> respx.MockRouter:
    """API que reconhece a sessão de um assessor."""
    api_simulada.get("/auth/sessao").respond(200, json=sessao_da_api("assessor"))
    return api_simulada
