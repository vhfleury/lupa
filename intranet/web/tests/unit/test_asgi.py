"""Testes de `lupa_web.asgi`: ciclo de vida do ASGI e repasse ao Django (D1)."""

import asyncio
import tempfile
from pathlib import Path
from typing import Any

import pytest

from lupa_web import asgi


@pytest.fixture(autouse=True)
def pendentes_isolados(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Volume dos pendentes numa pasta do teste e o `tempfile` restaurado depois."""
    monkeypatch.setenv("LUPA_WEB_ENVIOS_PENDENTES", str(tmp_path))
    monkeypatch.setattr(tempfile, "tempdir", None)
    return tmp_path


def _rodar(scope: dict[str, Any], entradas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    saidas: list[dict[str, Any]] = []
    fila = list(entradas)

    async def receive() -> dict[str, Any]:
        if not fila:
            await asyncio.Event().wait()
        return fila.pop(0)

    async def send(mensagem: Any) -> None:
        saidas.append(dict(mensagem))

    asyncio.run(asgi.application(scope, receive, send))
    return saidas


def test_ciclo_de_vida_confirma_partida_e_encerramento() -> None:
    """RNF-08 (D1): o uvicorn recebe `startup.complete` e `shutdown.complete`."""
    saidas = _rodar(
        {"type": "lifespan"},
        [{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}],
    )
    assert [s["type"] for s in saidas] == [
        "lifespan.startup.complete",
        "lifespan.shutdown.complete",
    ]


def test_partida_poe_os_temporarios_no_volume_dos_pendentes(pendentes_isolados: Path) -> None:
    """RF-INT-04 (D16): o corpo grande que o Django grava em temporário vai ao volume."""
    _rodar({"type": "lifespan"}, [{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}])
    destino = pendentes_isolados / "temporarios"
    assert tempfile.gettempdir() == str(destino)
    assert destino.is_dir()
    assert destino.stat().st_mode & 0o777 == 0o700


def test_pedido_http_chega_ao_django() -> None:
    """RNF-08 (D1): `GET /saude` pelo ASGI responde 200 com `ok`."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/saude",
        "raw_path": b"/saude",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"127.0.0.1")],
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 8000),
    }
    saidas = _rodar(scope, [{"type": "http.request", "body": b"", "more_body": False}])
    assert saidas[0]["status"] == 200
    assert saidas[1]["body"] == b"ok"
