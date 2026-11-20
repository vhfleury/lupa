"""Regressões do contrato A16 para o banco de conversas da 0.2."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from apoio_comum import criar_processo_teste
from lupa_api.agente.cliente import ClienteFalso, Roteiro, resposta_json
from lupa_pipeline.config import Settings, get_settings
from lupa_pipeline.dominio.enums import PapelUsuario
from tests.conftest import criar_usuario_teste, logar


def test_teto_da_conversa_nao_abre_outra_automaticamente(
    app_teste: FastAPI, engine_teste: Engine, settings_ficticias: Settings
) -> None:
    """RF-CHA-06: nova pergunta na conversa encerrada devolve o aviso sem chamar o modelo."""
    agente = ClienteFalso([Roteiro(resposta=resposta_json("Texto sem base."), tokens=(900, 200))])
    app_teste.state.cliente_agente = agente
    app_teste.dependency_overrides[get_settings] = lambda: settings_ficticias.model_copy(
        update={"agente_max_tokens_conversa": 1_000}
    )
    assessor = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    processo = criar_processo_teste(engine_teste, assessor)
    with TestClient(app_teste, base_url="https://testserver") as cliente:
        logar(cliente, engine_teste, assessor)
        rota = f"/processos/{processo.hex()}/chat"
        primeira = cliente.post(rota, json={"pergunta": "Onde está a sentença?"})
        assert primeira.status_code == 200
        assert primeira.json()["conversa_encerrada"] is True
        segunda = cliente.post(rota, json={"pergunta": "E o recurso?"})
        assert segunda.json()["status"] == "teto"
        assert segunda.json()["conversa_id"] == primeira.json()["conversa_id"]
    assert len(agente.pedidos) == 1
