"""Testes de `lupa_web.envios_pendentes`: arquivo guardado para o complemento (D16, A4)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from lupa_web import envios_pendentes

AGORA = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
COOKIE = "sessao-sintetica"


@pytest.fixture(autouse=True)
def pasta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pasta temporária no lugar do volume `envios-pendentes`."""
    monkeypatch.setenv("LUPA_WEB_ENVIOS_PENDENTES", str(tmp_path))
    return tmp_path


def _guardar(pasta: Path, agora: datetime = AGORA, cookie: str = COOKIE) -> str:
    origem = pasta / f"origem-{agora.timestamp()}"
    origem.write_bytes(b"%PDF-1.4 sintetico")
    return envios_pendentes.guardar(origem, "autos.pdf", cookie, agora)


def test_pendente_guardado_e_recuperado_pela_mesma_sessao(pasta: Path) -> None:
    """RF-INT-04 (D16): o código de 32 bytes recupera o mesmo arquivo e o nome."""
    codigo = _guardar(pasta)
    pendente = envios_pendentes.recuperar(codigo, COOKIE, AGORA + timedelta(minutes=5))
    assert len(codigo) == 64
    assert pendente is not None
    assert pendente.nome == "autos.pdf"
    assert pendente.caminho.read_bytes() == b"%PDF-1.4 sintetico"
    assert COOKIE not in "".join(p.read_text(errors="ignore") for p in pasta.iterdir())


def test_pendente_vencido_ou_de_outra_sessao_nao_e_recuperado(pasta: Path) -> None:
    """RF-INT-04 (D16): vencido (2 h), de outra sessão, inexistente ou mal formado: nada."""
    codigo = _guardar(pasta)
    assert envios_pendentes.recuperar(codigo, "outra-sessao", AGORA) is None
    assert envios_pendentes.recuperar(codigo, COOKIE, AGORA + timedelta(hours=2, seconds=1)) is None
    assert envios_pendentes.recuperar("f" * 64, COOKIE, AGORA) is None
    assert envios_pendentes.recuperar("../../etc/passwd", COOKIE, AGORA) is None
    assert envios_pendentes.recuperar(codigo, "", AGORA) is None


def test_pendente_e_apagado_apos_aceite_e_vencidos_no_envio_novo(pasta: Path) -> None:
    """RF-INT-04 (D16): `apagar` remove o aceito; `apagar_vencidos` remove os de mais de 2 h."""
    aceito = _guardar(pasta)
    antigo = _guardar(pasta, AGORA - timedelta(hours=3))
    recente = _guardar(pasta, AGORA - timedelta(minutes=30))
    envios_pendentes.apagar(aceito)
    assert envios_pendentes.apagar_vencidos(AGORA) == 1
    assert envios_pendentes.recuperar(aceito, COOKIE, AGORA) is None
    assert envios_pendentes.recuperar(antigo, COOKIE, AGORA - timedelta(hours=3)) is None
    assert envios_pendentes.recuperar(recente, COOKIE, AGORA) is not None
    envios_pendentes.apagar("nao-e-codigo")
