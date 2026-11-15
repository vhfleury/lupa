"""Rota da sessão corrente consumida pela interface (RF-ACE-01, RF-ACE-03)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from lupa_pipeline.dominio.enums import PapelUsuario
from tests.conftest import criar_usuario_teste, logar

pytestmark = pytest.mark.integracao


def test_sessao_devolve_usuario_e_permissoes_do_papel(
    app_teste: FastAPI, engine_teste: Engine
) -> None:
    """RF-ACE-03: desembargador vê as próprias permissões; sem cookie, 401."""
    cliente = TestClient(app_teste, base_url="https://testserver")
    assert cliente.get("/auth/sessao").status_code == 401
    usuario = criar_usuario_teste(engine_teste, PapelUsuario.DESEMBARGADOR)
    logar(cliente, engine_teste, usuario)
    corpo = cliente.get("/auth/sessao").json()
    assert (corpo["usuario_id"], corpo["nome_usuario"]) == (usuario.id, usuario.nome)
    assert corpo["papel"] == "desembargador"
    assert corpo["troca_senha_obrigatoria"] is False
    assert {"gerir_assessor", "ver_auditoria"} <= set(corpo["permissoes"])
    assert "gabinete_id" not in corpo


def test_sessao_do_assessor_nao_tem_permissoes_do_desembargador(
    app_teste: FastAPI, engine_teste: Engine
) -> None:
    """RF-ACE-03: o assessor vê só as permissões de trabalho nos processos."""
    cliente = TestClient(app_teste, base_url="https://testserver")
    logar(cliente, engine_teste, criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR))
    permissoes = cliente.get("/auth/sessao").json()["permissoes"]
    assert permissoes == ["anotar", "subir_processo", "ver_processo"]


def test_sessao_responde_mesmo_com_troca_de_senha_pendente(
    app_teste: FastAPI, engine_teste: Engine
) -> None:
    """RF-ACE-04: a interface precisa saber que deve levar à troca de senha."""
    cliente = TestClient(app_teste, base_url="https://testserver")
    usuario = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR, troca_senha=True)
    logar(cliente, engine_teste, usuario)
    assert cliente.get("/auth/sessao").json()["troca_senha_obrigatoria"] is True
