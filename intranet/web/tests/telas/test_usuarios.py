"""Gestão de assessores: senha temporária exibida uma vez, ações e recusas (RF-INT-03)."""

import pytest
import respx
from django.test import Client

from tests.telas.conftest import sessao_da_api
from tests.telas.test_paridade import (
    ASSESSOR,
    SENHA_TEMPORARIA,
    USUARIO_ASSESSOR,
    USUARIOS,
)


@pytest.fixture
def desembargador(api_simulada: respx.MockRouter) -> respx.MockRouter:
    """API que reconhece a sessão do desembargador e lista os usuários."""
    api_simulada.get("/auth/sessao").respond(200, json=sessao_da_api("desembargador"))
    api_simulada.get("/usuarios").respond(200, json=USUARIOS)
    return api_simulada


def test_senha_temporaria_nao_fica_em_cache(
    desembargador: respx.MockRouter, navegador: Client
) -> None:
    """RF-ACE-03: a página com a senha temporária não é guardada pelo navegador."""
    criado = USUARIO_ASSESSOR | {"senha_temporaria": SENHA_TEMPORARIA}
    desembargador.post("/usuarios").respond(201, json=criado)
    resposta = navegador.post("/usuarios", {"nome_usuario": "nova.sintetica"})
    assert SENHA_TEMPORARIA in resposta.content.decode()
    assert resposta["Cache-Control"] == "no-store"
    assert SENHA_TEMPORARIA not in navegador.get("/usuarios").content.decode()


def test_criacao_recusada_mostra_a_mensagem_da_api(
    desembargador: respx.MockRouter, navegador: Client
) -> None:
    """RF-ACE-03 (A1.8): nome repetido volta à tela com a mensagem e o status da API."""
    desembargador.post("/usuarios").respond(409, json={"detail": "nome de usuário já existe"})
    resposta = navegador.post("/usuarios", {"nome_usuario": "assessora.sintetica"})
    assert resposta.status_code == 409
    assert "Nome de usuário já existe." in resposta.content.decode()


@pytest.mark.parametrize(
    ("acao", "mensagem"),
    [
        ("desativar", "Usuário assessora.sintetica desativado."),
        ("reativar", "Usuário assessora.sintetica reativado."),
        ("resetar-mfa", "com autenticador apagado; o próximo login cadastra outro."),
    ],
)
def test_aviso_da_acao_cita_o_usuario(
    desembargador: respx.MockRouter, navegador: Client, acao: str, mensagem: str
) -> None:
    """RF-ACE-03: depois da ação, a lista confirma o que mudou para quem."""
    html = navegador.get("/usuarios", {"aviso": acao, "usuario": ASSESSOR}).content.decode()
    assert mensagem in html


def test_aviso_de_usuario_desconhecido_nao_aparece(
    desembargador: respx.MockRouter, navegador: Client
) -> None:
    """RF-ACE-03: aviso de ação sobre usuário que não está na lista é ignorado."""
    html = navegador.get("/usuarios", {"aviso": "reativar", "usuario": "x"}).content.decode()
    assert "reativado" not in html


def test_acao_desconhecida_responde_nao_encontrado(
    desembargador: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02: ação fora das previstas não chega à API."""
    assert navegador.post(f"/usuarios/{ASSESSOR}/apagar").status_code == 404


def test_confirmacao_de_desativar_usuario_desconhecido(
    desembargador: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02: a confirmação de usuário fora da lista responde 404."""
    assert navegador.get("/usuarios/x/desativar").status_code == 404


def test_acao_recusada_mostra_a_mensagem_da_api(
    desembargador: respx.MockRouter, navegador: Client
) -> None:
    """RF-ACE-03 (A1.8): recusa da API na ação volta à lista com a mensagem."""
    desembargador.post(f"/usuarios/{ASSESSOR}/reativar").respond(
        409, json={"detail": "usuário já está ativo"}
    )
    resposta = navegador.post(f"/usuarios/{ASSESSOR}/reativar")
    assert resposta.status_code == 409
    assert "Usuário já está ativo." in resposta.content.decode()
