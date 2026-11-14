"""Gestão de assessores pelo desembargador e papéis na API (RF-ACE-03, RF-ACE-04)."""

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from apoio_comum import UsuarioTeste, eventos_do_banco
from lupa_pipeline.dominio.chaves import chave_hash
from lupa_pipeline.dominio.enums import PapelUsuario
from tests.conftest import criar_usuario_teste, logar

pytestmark = pytest.mark.integracao


def _cliente_logado(app: FastAPI, engine: Engine, usuario: UsuarioTeste) -> TestClient:
    cliente = TestClient(app, base_url="https://testserver")
    logar(cliente, engine, usuario)
    return cliente


def _nome() -> str:
    return f"novo_{uuid4().hex[:10]}"


@pytest.fixture
def desembargador(engine_teste: Engine) -> UsuarioTeste:
    """Desembargador com MFA configurado."""
    return criar_usuario_teste(engine_teste, PapelUsuario.DESEMBARGADOR)


def test_desembargador_cria_assessor_com_troca_obrigatoria(
    app_teste: FastAPI, engine_teste: Engine, desembargador: UsuarioTeste
) -> None:
    """RF-ACE-04: o assessor nasce com senha temporária, exibida uma vez, e troca obrigatória."""
    cliente = _cliente_logado(app_teste, engine_teste, desembargador)
    nome = _nome()
    resposta = cliente.post("/usuarios", json={"nome_usuario": nome, "papel": "assessor"})
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert (corpo["papel"], corpo["troca_senha_obrigatoria"]) == ("assessor", True)
    assert corpo["id"] == chave_hash([nome]).hex()
    assert len(corpo["senha_temporaria"]) >= 20
    assert nome in {u["nome_usuario"] for u in cliente.get("/usuarios").json()}
    repetido = cliente.post("/usuarios", json={"nome_usuario": nome, "papel": "assessor"})
    assert repetido.status_code == 409
    invalido = cliente.post("/usuarios", json={"nome_usuario": "A B", "papel": "assessor"})
    assert invalido.status_code == 422
    criados = eventos_do_banco(engine_teste, usuario_id=desembargador.id, acao="usuario_criado")
    assert [e.objeto_id for e in criados] == [corpo["id"]]


def test_assessor_criado_entra_e_so_troca_a_senha(
    app_teste: FastAPI, engine_teste: Engine, desembargador: UsuarioTeste
) -> None:
    """RF-ACE-04: com a senha temporária, o login pede MFA e a sessão só troca a senha."""
    cliente = _cliente_logado(app_teste, engine_teste, desembargador)
    nome = _nome()
    temporaria = cliente.post("/usuarios", json={"nome_usuario": nome}).json()["senha_temporaria"]
    novo = TestClient(app_teste, base_url="https://testserver")
    passo1 = novo.post("/auth/login", json={"nome_usuario": nome, "senha": temporaria})
    assert passo1.json()["etapa"] == "configurar_mfa"


def test_desembargador_nao_cria_outro_desembargador_pela_api(
    app_teste: FastAPI, engine_teste: Engine, desembargador: UsuarioTeste
) -> None:
    """RF-ACE-05: desembargador só nasce pelo script; a tentativa negada fica na auditoria."""
    cliente = _cliente_logado(app_teste, engine_teste, desembargador)
    resposta = cliente.post("/usuarios", json={"nome_usuario": _nome(), "papel": "desembargador"})
    assert resposta.status_code == 403
    negados = eventos_do_banco(
        engine_teste, usuario_id=desembargador.id, acao="usuario_criado", resultado="negado"
    )
    assert len(negados) == 1
    administrador = cliente.post("/usuarios", json={"nome_usuario": _nome(), "papel": "admin"})
    assert administrador.status_code == 422


def test_assessor_recebe_403_na_gestao_de_usuarios(
    app_teste: FastAPI, engine_teste: Engine
) -> None:
    """RF-ACE-03: assessor não lista, não cria e não altera usuários."""
    assessor = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    outro = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    cliente = _cliente_logado(app_teste, engine_teste, assessor)
    assert cliente.get("/usuarios").status_code == 403
    criar = cliente.post("/usuarios", json={"nome_usuario": _nome(), "papel": "assessor"})
    assert criar.status_code == 403
    for acao in ("desativar", "reativar", "resetar-senha", "resetar-mfa"):
        assert cliente.post(f"/usuarios/{outro.id}/{acao}").status_code == 403, acao


def test_desembargador_recebe_a_lista_de_usuarios(
    app_teste: FastAPI, engine_teste: Engine, desembargador: UsuarioTeste
) -> None:
    """RF-ACE-03: o desembargador vê todos os usuários, sem segredos."""
    assessor = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    cliente = _cliente_logado(app_teste, engine_teste, desembargador)
    resposta = cliente.get("/usuarios")
    assert resposta.status_code == 200
    por_id = {u["id"]: u for u in resposta.json()}
    assert {desembargador.id, assessor.id} <= set(por_id)
    assert set(por_id[assessor.id]) == {
        "id",
        "nome_usuario",
        "papel",
        "ativo",
        "mfa_confirmado",
        "troca_senha_obrigatoria",
    }


def test_desembargador_reseta_senha_e_mfa_do_assessor(
    app_teste: FastAPI, engine_teste: Engine, desembargador: UsuarioTeste
) -> None:
    """RF-ACE-04: reset de senha força troca e derruba as sessões; reset de MFA exige cadastro."""
    assessor = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    sessao_assessor = _cliente_logado(app_teste, engine_teste, assessor)
    cliente = _cliente_logado(app_teste, engine_teste, desembargador)
    reset = cliente.post(f"/usuarios/{assessor.id}/resetar-senha")
    assert reset.status_code == 200
    assert reset.json()["troca_senha_obrigatoria"] is True
    assert sessao_assessor.get("/auth/sessao").status_code == 401
    temporaria = reset.json()["senha_temporaria"]
    login = sessao_assessor.post(
        "/auth/login", json={"nome_usuario": assessor.nome, "senha": temporaria}
    )
    assert login.json()["etapa"] == "mfa"
    mfa = cliente.post(f"/usuarios/{assessor.id}/resetar-mfa")
    assert mfa.status_code == 200 and mfa.json()["mfa_confirmado"] is False
    login = sessao_assessor.post(
        "/auth/login", json={"nome_usuario": assessor.nome, "senha": temporaria}
    )
    assert login.json()["etapa"] == "configurar_mfa"
    acoes = {e.acao for e in eventos_do_banco(engine_teste, usuario_id=desembargador.id)}
    assert {"senha_resetada", "mfa_resetado"} <= acoes


def test_desativar_impede_login_e_reativar_devolve_acesso(
    app_teste: FastAPI, engine_teste: Engine, desembargador: UsuarioTeste
) -> None:
    """RF-ACE-04: desativado não entra; reativado entra; a auditoria dele continua lá."""
    assessor = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    sessao_assessor = _cliente_logado(app_teste, engine_teste, assessor)
    cliente = _cliente_logado(app_teste, engine_teste, desembargador)
    assert cliente.post(f"/usuarios/{assessor.id}/desativar").json()["ativo"] is False
    assert sessao_assessor.get("/auth/sessao").status_code == 401
    tentativa = TestClient(app_teste, base_url="https://testserver")
    with pytest.raises(AssertionError):
        logar(tentativa, engine_teste, assessor)
    assert eventos_do_banco(engine_teste, usuario_id=assessor.id, acao="mfa_ok")
    assert cliente.post(f"/usuarios/{assessor.id}/reativar").json()["ativo"] is True
    logar(tentativa, engine_teste, assessor)
    assert eventos_do_banco(engine_teste, usuario_id=assessor.id, acao="login_falha")
    acoes = {e.acao for e in eventos_do_banco(engine_teste, objeto_id=assessor.id)}
    assert {"usuario_desativado", "usuario_reativado"} <= acoes


def test_ninguem_gere_a_si_mesmo_nem_outro_desembargador(
    app_teste: FastAPI, engine_teste: Engine, desembargador: UsuarioTeste
) -> None:
    """RF-ACE-04: a gestão alcança só assessores; usuário inexistente dá 404."""
    outro = criar_usuario_teste(engine_teste, PapelUsuario.DESEMBARGADOR)
    cliente = _cliente_logado(app_teste, engine_teste, desembargador)
    assert cliente.post(f"/usuarios/{desembargador.id}/desativar").status_code == 403
    assert cliente.post(f"/usuarios/{outro.id}/resetar-senha").status_code == 403
    assert cliente.post(f"/usuarios/{'0' * 64}/desativar").status_code == 404
