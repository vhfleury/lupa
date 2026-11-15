"""Consulta do índice e reclassificação com histórico pelo contrato público (A12)."""

import pytest

from tests.ingestao.conftest import Autos

pytestmark = pytest.mark.integracao


def test_peca_manual_preserva_historico_e_recalcula_fatos(autos_civeis: Autos) -> None:
    """RF-PEC-02: tipo novo mantém id e autoria, intervalo inválido é recusado."""
    c, base = autos_civeis.cliente, autos_civeis.url
    pecas = c.get(base + "/indice").json()["pecas"]
    assert len(pecas) == 6
    p = next(x for x in pecas if x["tipo"] == "certidao")
    caminho = base + "/pecas/" + p["id"]
    assert c.post(caminho + "/reclassificar", json={"pagina_inicial": 100}).status_code == 422
    r = c.post(caminho + "/reclassificar", json={"tipo": "outros"})
    assert r.status_code == 201, r.text
    salvo = c.get(caminho).json()
    assert salvo["id"] == p["id"] and salvo["metodo"] == "manual"
    assert any(h["tipo"] == "certidao" for h in salvo["historico"])
    assert all(f["tipo"] != "data_intimacao" for f in c.get(base + "/fatos").json()["fatos"])
