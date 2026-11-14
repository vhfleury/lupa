"""Abertura do processo e auditoria automática das rotas marcadas (RF-PRO-03, RF-AUD-01)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from apoio_comum import UsuarioTeste, criar_processo_teste, eventos_do_banco
from lupa_intranet.api.middleware import auditar_rota
from lupa_intranet.auditoria.eventos import AcaoAuditoria
from lupa_pipeline.dominio.enums import PapelUsuario
from tests.conftest import criar_usuario_teste, logar

pytestmark = pytest.mark.integracao


def _cliente(app: FastAPI, engine: Engine, usuario: UsuarioTeste) -> TestClient:
    cliente = TestClient(app, base_url="https://testserver")
    logar(cliente, engine, usuario)
    return cliente


@pytest.mark.parametrize("papel", [PapelUsuario.ASSESSOR, PapelUsuario.DESEMBARGADOR])
def test_usuario_abre_processo_de_que_nao_e_responsavel_e_acesso_e_registrado(
    app_teste: FastAPI, engine_teste: Engine, papel: PapelUsuario
) -> None:
    """RF-PRO-03: responsável não restringe acesso; 200 e `processo_aberto` com IP e local."""
    autor = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    leitor = criar_usuario_teste(engine_teste, papel)
    processo = criar_processo_teste(engine_teste, autor)
    resposta = _cliente(app_teste, engine_teste, leitor).get(f"/processos/{processo.hex()}")
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert (corpo["id"], corpo["classe"], corpo["status"]) == (
        processo.hex(),
        "apelacao_civel",
        "criado",
    )
    assert "materia" not in corpo and "sigiloso" not in corpo and "gabinete_id" not in corpo
    eventos = eventos_do_banco(engine_teste, processo_id=processo.hex(), usuario_id=leitor.id)
    assert [(e.acao, e.resultado) for e in eventos] == [("processo_aberto", "ok")]
    assert eventos[0].localizacao == "Cidade Fictícia, Estado Fictício, País Fictício"
    assert eventos[0].ip == "testclient"


def test_processo_inexistente_responde_404_e_a_tentativa_e_registrada(
    app_teste: FastAPI, engine_teste: Engine
) -> None:
    """RF-AUD-01: 404 com o evento `processo_aberto` negado, sem processo na cadeia."""
    assessor = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    inexistente = "ab" * 32
    resposta = _cliente(app_teste, engine_teste, assessor).get(f"/processos/{inexistente}")
    assert resposta.status_code == 404
    tentativas = eventos_do_banco(engine_teste, usuario_id=assessor.id, objeto_id=inexistente)
    assert [(e.acao, e.resultado, e.hk_processo) for e in tentativas] == [
        ("processo_aberto", "negado", None)
    ]


def test_middleware_registra_busca_sem_processo(app_teste: FastAPI, engine_teste: Engine) -> None:
    """RF-AUD-01: rota marcada sem processo grava o evento do usuário com o caminho."""
    from lupa_intranet.acesso.autorizacao import AtorAutenticado

    @app_teste.get("/busca-teste")
    @auditar_rota(AcaoAuditoria.BUSCA, conteudo=False)
    def _busca(ator: AtorAutenticado) -> dict[str, str]:
        return {"ok": "sim"}

    assessor = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    cliente = _cliente(app_teste, engine_teste, assessor)
    assert cliente.get("/busca-teste").status_code == 200
    eventos = eventos_do_banco(engine_teste, usuario_id=assessor.id, acao="busca")
    assert [(e.objeto_id, e.hk_processo) for e in eventos] == [("/busca-teste", None)]


def test_auditar_rota_recusa_acao_nao_automatica() -> None:
    """RF-AUD-01: só `processo_aberto`, `pagina_vista` e `busca` são automáticas."""
    with pytest.raises(ValueError, match="não é registrada automaticamente"):
        auditar_rota(AcaoAuditoria.LOGIN_OK, conteudo=False)
