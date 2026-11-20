"""Testes de `lupa_web.urls`: saúde e página de login."""

from django.test import Client


def test_saude_responde_ok_sem_chamar_a_api() -> None:
    """RNF-08: `/saude` responde 200 para o healthcheck do contêiner."""
    resposta = Client().get("/saude")
    assert resposta.status_code == 200
    assert resposta.content == b"ok"


def test_pagina_de_login_responde_html() -> None:
    """RF-INT-01: a página de login vem do front Django, em HTML, sem chamar a API."""
    resposta = Client().get("/login")
    assert resposta.status_code == 200
    assert "<title>Entrar · Lupa</title>" in resposta.content.decode()
