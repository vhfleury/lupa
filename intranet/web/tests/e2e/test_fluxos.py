"""E2E de acesso e gestão de assessores contra a stack real, pelo proxy (RNF-09, RF-INT-01).

O desembargador vem de `e2e_preparar.py` e cria o assessor pela interface.
"""

import re
import secrets
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Browser, Locator, Page, expect

from tests.e2e.apoio_e2e import (
    ARGUMENTOS_DO_CONTEXTO,
    Conta,
    cadastrar_autenticador,
    contexto_como,
    enviar_senha,
    primeiro_acesso,
    trocar_senha,
    variavel,
)
from tests.e2e.conftest import DESEMBARGADOR

pytestmark = pytest.mark.e2e

SUFIXO = secrets.token_hex(3)
ASSESSOR = f"ass.e2e.{SUFIXO}"
MENSAGEM_RECUSA = "Não foi possível entrar com os dados informados. Confira e tente novamente."
MENSAGEM_BLOQUEIO = re.compile(r"Muitas tentativas")
SENHA_ERRADA = "senha-errada-de-proposito"
TENTATIVAS_ANTES_DO_BLOQUEIO = 4
TAMANHO_MINIMO_DA_SENHA = 12
temporarias: dict[str, str] = {}


def _menu(page: Page) -> Locator:
    return page.get_by_role("navigation", name="Menu principal")


def _linha(page: Page, usuario: str) -> Locator:
    return page.locator(f'tr[data-usuario="{usuario}"]')


def _ler_senha_temporaria(page: Page) -> str:
    valor = (page.get_by_test_id("senha-temporaria-valor").text_content() or "").strip()
    assert len(valor) >= TAMANHO_MINIMO_DA_SENHA
    expect(page.get_by_text("não será exibida de novo")).to_be_visible()
    page.get_by_role("link", name=re.compile("Já anotei")).click()
    expect(page.get_by_test_id("senha-temporaria")).to_have_count(0)
    expect(page.get_by_text(valor)).to_have_count(0)
    return valor


def _alerta(page: Page) -> str:
    alerta = page.get_by_role("alert")
    expect(alerta).to_be_visible()
    return (alerta.text_content() or "").strip()


def test_rota_protegida_leva_ao_login(page: Page) -> None:
    """RNF-09: sem sessão, a raiz leva ao login; o proxy responde a própria saúde."""
    page.goto("/")
    expect(page).to_have_url(re.compile(r"/login$"))
    expect(page.get_by_role("form", name="Entrar")).to_be_visible()
    assert page.request.get("/saude").status == 200


def test_primeiro_acesso_do_desembargador_exige_codigo_e_troca(
    page: Page, contas: dict[str, Conta]
) -> None:
    """RNF-09: código errado é recusado e a troca de senha vem antes de qualquer outra tela."""
    usuario = variavel("LUPA_E2E_DES_USUARIO")
    temporaria = variavel("LUPA_E2E_DES_SENHA")
    enviar_senha(page, usuario, temporaria)
    autenticador = cadastrar_autenticador(page)
    page.get_by_label("Código de 6 dígitos").fill(autenticador.errado())
    page.get_by_role("button", name="Confirmar autenticador").click()
    expect(page.get_by_role("alert")).to_have_text(MENSAGEM_RECUSA)
    page.get_by_label("Código de 6 dígitos").fill(autenticador.proximo())
    page.get_by_role("button", name="Confirmar autenticador").click()
    expect(page).to_have_url(re.compile(r"/trocar-senha$"))
    page.goto("/usuarios")
    expect(page).to_have_url(re.compile(r"/trocar-senha$"))
    senha = trocar_senha(page, temporaria)
    expect(page.get_by_test_id("usuario-papel")).to_have_text("Desembargador")
    expect(page.get_by_test_id("estado-sessao")).to_contain_text("Sessão ativa")
    expect(_menu(page).get_by_role("link", name="Usuários")).to_be_visible()
    expect(_menu(page).get_by_role("link", name="Auditoria")).to_be_visible()
    contas[DESEMBARGADOR] = Conta(usuario, senha, autenticador, page.context.storage_state())


def test_desembargador_cria_desativa_reativa_e_redefine_o_assessor(
    browser: Browser, desembargador: Conta
) -> None:
    """RNF-09: gestão de assessores pela tela, com confirmação antes de desativar."""
    contexto, page = contexto_como(browser, desembargador)
    _menu(page).get_by_role("link", name="Usuários").click()
    expect(page.get_by_role("heading", name="Novo assessor")).to_be_visible()
    expect(page.get_by_label("Papel")).to_have_count(0)
    page.get_by_label("Nome de usuário").fill(ASSESSOR)
    page.get_by_role("button", name="Criar assessor").click()
    primeira = _ler_senha_temporaria(page)
    linha = _linha(page, ASSESSOR)
    expect(linha.get_by_test_id("situacao")).to_have_text("Ativo · troca de senha pendente")
    linha.get_by_role("link", name=f"Desativar {ASSESSOR}").click()
    confirmacao = page.get_by_test_id("confirmacao")
    expect(confirmacao).to_contain_text(ASSESSOR)
    confirmacao.get_by_role("link", name="Cancelar").click()
    expect(linha.get_by_test_id("situacao")).to_have_text(re.compile(r"^Ativo"))
    linha.get_by_role("link", name=f"Desativar {ASSESSOR}").click()
    page.get_by_test_id("confirmacao").get_by_role("button", name="Desativar").click()
    expect(linha.get_by_test_id("situacao")).to_have_text(re.compile(r"^Inativo"))
    linha.get_by_role("button", name=f"Reativar {ASSESSOR}").click()
    expect(linha.get_by_test_id("situacao")).to_have_text(re.compile(r"^Ativo"))
    linha.get_by_role("button", name=f"Resetar senha de {ASSESSOR}").click()
    temporarias[ASSESSOR] = _ler_senha_temporaria(page)
    assert temporarias[ASSESSOR] != primeira
    linha.get_by_role("button", name=f"Resetar autenticador de {ASSESSOR}").click()
    expect(page.get_by_role("status")).to_contain_text("autenticador apagado")
    propria = _linha(page, desembargador.usuario)
    expect(propria.get_by_role("button")).to_have_count(0)
    expect(propria.get_by_role("link")).to_have_count(0)
    contexto.close()


def test_assessor_entra_apos_o_reset_e_nao_ve_a_gestao(
    page: Page, contas: dict[str, Conta]
) -> None:
    """RNF-09: o assessor faz o primeiro acesso e a tela de usuários lhe é negada."""
    contas[ASSESSOR] = primeiro_acesso(page, ASSESSOR, temporarias[ASSESSOR])
    expect(page.get_by_test_id("usuario-papel")).to_have_text("Assessor")
    expect(_menu(page).get_by_role("link")).to_have_text(["Início", "Processos"])
    page.goto("/usuarios")
    expect(page.get_by_role("heading", name="Acesso negado")).to_be_visible()


def test_sessao_apagada_volta_ao_login(browser: Browser, desembargador: Conta) -> None:
    """RNF-09: sem o cookie de sessão, a próxima navegação vai ao login."""
    contexto, page = contexto_como(browser, desembargador)
    desembargador.estado = contexto.storage_state()
    contexto.clear_cookies()
    _menu(page).get_by_role("link", name="Usuários").click()
    expect(page).to_have_url(re.compile(r"/login$"))
    contexto.close()


def test_mensagens_identicas_e_bloqueio_sem_revelar_o_usuario(
    browser: Browser, contas: dict[str, Conta]
) -> None:
    """RNF-09: recusa igual para usuário existente e inexistente; bloqueio após cinco falhas."""
    contexto = browser.new_context(**ARGUMENTOS_DO_CONTEXTO)
    page = contexto.new_page()
    fantasma = f"ninguem.{SUFIXO}"
    enviar_senha(page, ASSESSOR, SENHA_ERRADA)
    existente = _alerta(page)
    enviar_senha(page, fantasma, SENHA_ERRADA)
    assert existente == MENSAGEM_RECUSA
    assert _alerta(page) == existente
    for _ in range(TENTATIVAS_ANTES_DO_BLOQUEIO):
        for usuario in (fantasma, ASSESSOR):
            enviar_senha(page, usuario, SENHA_ERRADA)
            expect(page.get_by_role("alert")).to_have_text(MENSAGEM_RECUSA)
    enviar_senha(page, fantasma, SENHA_ERRADA)
    bloqueio_inexistente = _alerta(page)
    enviar_senha(page, ASSESSOR, contas[ASSESSOR].senha)
    assert MENSAGEM_BLOQUEIO.search(bloqueio_inexistente)
    assert _alerta(page) == bloqueio_inexistente
    assert urlparse(page.url).path == "/login"
    contexto.close()
