"""`exige_processo`: processo pelo id em hex, 404 auditado e DEK aberta (D12, D14; RF-PRO-03)."""

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from apoio_comum import criar_processo, eventos_do_banco
from lupa_intranet.acesso.autorizacao import exige_processo
from lupa_pipeline.dominio.enums import PapelUsuario
from lupa_pipeline.dominio.gravacao import gravar_satelite
from lupa_pipeline.dominio.tabelas import sat_processo_estado
from lupa_pipeline.dominio.visoes import VisaoProcesso
from lupa_pipeline.seguranca.contexto import dek_de, dek_para_gravar, limpar_contexto_padrao
from tests.conftest import criar_usuario_teste, logar

pytestmark = pytest.mark.integracao


def _com_rota_de_processo(app: FastAPI) -> None:
    def _abrir(processo: Annotated[VisaoProcesso, Depends(exige_processo)]) -> dict[str, str]:
        hk, dek = dek_para_gravar()
        return {"id": processo.id, "ativo": hk.hex(), "dek_confere": str(dek == dek_de(hk))}

    app.add_api_route("/teste/processos/{processo_id}", _abrir, methods=["GET"])


def _processo(fabrica: sessionmaker[Session], status: str | None = None) -> bytes:
    with fabrica() as session, session.begin():
        hk = criar_processo(session)
        if status is not None:
            gravar_satelite(session, sat_processo_estado, hk, {"status": status}, "teste")
    limpar_contexto_padrao()
    return hk


@pytest.fixture
def cliente_logado(app_teste: FastAPI, engine_teste: Engine) -> TestClient:
    """Assessor logado com a rota de teste que depende de `exige_processo`."""
    _com_rota_de_processo(app_teste)
    cliente = TestClient(app_teste, base_url="https://testserver")
    logar(cliente, engine_teste, criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR))
    return cliente


def test_processo_aberto_pelo_id_em_hex_ativa_a_dek(
    cliente_logado: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    """D12, D14: qualquer usuário abre o processo pelo hex do `hk` e a DEK dele fica ativa."""
    hk = _processo(fabrica_sessao)
    resposta = cliente_logado.get(f"/teste/processos/{hk.hex()}")
    assert resposta.status_code == 200
    assert resposta.json() == {"id": hk.hex(), "ativo": hk.hex(), "dek_confere": "True"}


def test_processo_inexistente_da_404_e_fica_na_auditoria(
    cliente_logado: TestClient, engine_teste: Engine
) -> None:
    """RF-AUD-01: a tentativa de abrir processo inexistente é recusada e registrada."""
    inexistente = "ab" * 32
    assert cliente_logado.get(f"/teste/processos/{inexistente}").status_code == 404
    negados = eventos_do_banco(engine_teste, objeto_id=inexistente, resultado="negado")
    assert [e.acao for e in negados] == ["processo_aberto"]


def test_processo_descartado_da_404(
    cliente_logado: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    """RF-PRO-05: processo descartado responde como conteúdo indisponível."""
    hk = _processo(fabrica_sessao, status="descartado")
    resposta = cliente_logado.get(f"/teste/processos/{hk.hex()}")
    assert (resposta.status_code, resposta.json()["detail"]) == (404, "processo descartado")
