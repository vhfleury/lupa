"""Integração com o proxy do compose: o navegador só alcança o front (D2)."""

import os

import httpx
import pytest

URL_PROXY = os.environ.get("LUPA_PROXY_URL", "https://proxy:8443")

pytestmark = pytest.mark.integracao


def _pedir(caminho: str) -> httpx.Response:
    try:
        return httpx.get(f"{URL_PROXY}{caminho}", verify=False, timeout=5)  # noqa: S501
    except httpx.TransportError as erro:
        motivo = f"proxy inacessível em {URL_PROXY}: {type(erro).__name__}"
        if os.environ.get("LUPA_EXIGIR_INTEGRACAO") == "1":
            pytest.fail(motivo, pytrace=False)
        pytest.skip(motivo)


def test_proxy_responde_404_para_api() -> None:
    """RF-INT-01 (D2): `/api/saude` pelo proxy cai no front e responde 404, sem chegar à API."""
    resposta = _pedir("/api/saude")
    assert resposta.status_code == 404
    assert "application/json" not in resposta.headers.get("content-type", "")


def test_proxy_entrega_o_front() -> None:
    """RF-INT-01 (D2): a raiz pelo proxy vem do front Django."""
    resposta = _pedir("/")
    assert resposta.status_code == 200
    assert "<title>Lupa</title>" in resposta.text
