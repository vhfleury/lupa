"""CSRF dos formulários do front (A2, D4)."""

import respx
from django.test import Client


def test_post_sem_csrf_e_recusado_sem_chamar_api(api_simulada: respx.MockRouter) -> None:
    """RF-INT-03 (A2.3): POST sem token CSRF recebe 403 e não chega à API."""
    resposta = Client(enforce_csrf_checks=True).post(
        "/login", {"nome_usuario": "assessor", "senha": "x"}
    )
    assert resposta.status_code == 403
    assert not api_simulada.calls


def test_post_com_csrf_chega_a_api(api_simulada: respx.MockRouter) -> None:
    """RF-INT-03 (A2.2): com o token emitido pelo GET, o POST segue para a API."""
    api_simulada.post("/auth/login").respond(200, json={"etapa": "mfa", "desafio": "d"})
    cliente = Client(enforce_csrf_checks=True)
    cliente.get("/login")
    token = cliente.cookies["csrftoken"].value
    resposta = cliente.post(
        "/login", {"nome_usuario": "assessor", "senha": "x", "csrfmiddlewaretoken": token}
    )
    assert resposta.status_code == 200
    assert len(api_simulada.calls) == 1
