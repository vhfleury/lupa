"""Correções e anotações com histórico pelo contrato público (A11)."""

from datetime import date

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from apoio_comum import eventos_do_banco
from lupa_pipeline.dominio.visoes import VisaoPagina, VisaoProcesso
from lupa_pipeline.ingestao.eventos.etapa import processar_eventos
from lupa_pipeline.seguranca.contexto import ativar_processo
from tests.ingestao.conftest import Autos

pytestmark = pytest.mark.integracao


def test_correcao_e_historico_com_evidencia_atualizada(
    autos_civeis: Autos, engine_teste: Engine
) -> None:
    """RF-FAT-03: valor e evidência mudam sob o mesmo id e o catálogo é executado novamente."""
    c, base = autos_civeis.cliente, autos_civeis.url
    fatos = c.get(base + "/fatos").json()["fatos"]
    fato = next(f for f in fatos if f["tipo"] == "data_intimacao")
    e = fato["evidencias"][0]
    rota = f"{base}/fatos/{fato['id']}/corrigir"
    assert c.post(rota, json={"status": "corrigido", "valor": "2025-03-06"}).status_code == 422
    pedido = {
        "status": "corrigido",
        "valor": "2025-03-06",
        "pagina_id": e["pagina_id"],
        "inicio": e["inicio"],
        "fim": e["fim"],
        "trecho": "incompatível",
    }
    assert c.post(rota, json=pedido).status_code == 422
    with Session(engine_teste) as s:
        hk = autos_civeis.processo
        ativar_processo(hk, s.get_one(VisaoProcesso, hk).chave_dados_cifrada)
        pagina = s.get_one(VisaoPagina, bytes.fromhex(e["pagina_id"]))
        assert pagina.texto
        inicio = pagina.texto.index("06/03/2025")
    pedido.update(trecho="06/03/2025", inicio=inicio, fim=inicio + 10)
    r = c.post(rota, json=pedido)
    assert r.status_code == 201, r.text
    assert r.json()["fato"]["id"] == fato["id"]
    assert r.json()["achados_gravados"] >= 1
    versoes = [x for x in c.get(base + "/fatos/historico").json()["fatos"] if x["id"] == fato["id"]]
    assert [(v["vigente"], v["valor"]) for v in versoes] == [
        (False, "2025-03-04"),
        (True, "2025-03-06"),
    ]
    historico = c.get(base + "/achados/historico").json()["achados"]
    tempestividade = [a for a in historico if a["validacao"] == "tempestividade_recurso"]
    assert len(tempestividade) >= 2 and sum(a["vigente"] for a in tempestividade) == 1
    assert len({a["id"] for a in tempestividade}) == 1
    with Session(engine_teste) as s, s.begin():
        ativar_processo(hk, s.get_one(VisaoProcesso, hk).chave_dados_cifrada)
        assert processar_eventos(s, hk, date(2025, 4, 30))["achados_gravados"] == 0
    atual = next(f for f in c.get(base + "/fatos").json()["fatos"] if f["id"] == fato["id"])
    assert atual["valor"] == "2025-03-06" and atual["evidencias"][0]["trecho"] == "06/03/2025"
    assert c.post(rota, json={"status": "confirmado"}).json()["fato"]["status"] == "confirmado"
    for tipo, alvo in (("fato_id", fato["id"]), ("achado_id", tempestividade[0]["id"])):
        nota = c.post(base + "/anotacoes", json={tipo: alvo, "texto": "Conferência sintética."})
        assert nota.status_code == 201, nota.text
        assert nota.json()[tipo] == alvo and len(nota.json()["id"]) == 64
    assert len(c.get(base + "/anotacoes").json()["anotacoes"]) == 2
    assert {"fato_corrigido", "validacao_executada", "anotacao"} <= {
        ev.acao for ev in eventos_do_banco(engine_teste, hk_processo=autos_civeis.processo)
    }
