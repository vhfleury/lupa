"""Estado e diagnóstico pelo contrato público."""

import pytest

from tests.ingestao.conftest import Autos


@pytest.mark.integracao
def test_diagnostico_relatorio_e_alertas_do_zip(autos_civeis: Autos) -> None:
    """RF-ING-03, RF-ING-06: o estado final e os totais pertencem ao arquivo enviado."""
    c = autos_civeis.cliente
    base = autos_civeis.url + "/arquivos/" + autos_civeis.arquivo.hex()
    assert c.get(base + "/diagnostico").json()["total_paginas"] == 6
    r = c.get(base + "/relatorio").json()
    assert r["estado"] == "concluido" and r["relatorio"]["paginas_faltando_lista"] == []
    assert c.get(base + "/alertas").status_code == 200
