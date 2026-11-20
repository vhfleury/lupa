"""Fixtures da suíte E2E: contexto do navegador, ordem dos arquivos e contas compartilhadas.

Os arquivos rodam na ordem de `ORDEM` (acesso, processos, chat e auditoria, acessibilidade,
segurança, capturas). A conta de cada papel é criada uma vez: pelo teste de primeiro acesso
de `test_fluxos.py` e `test_processos.py` ou, quando um arquivo roda sozinho, pela fixture.
"""

from typing import Any

import pytest
from playwright.sync_api import Browser

from tests.e2e.apoio_e2e import ARGUMENTOS_DO_CONTEXTO, Conta, primeiro_acesso, variavel

ORDEM = (
    "test_fluxos.py",
    "test_processos.py",
    "test_chat_auditoria.py",
    "test_acessibilidade.py",
    "test_seguranca.py",
    "test_capturas.py",
)
DESEMBARGADOR = "desembargador"
ASSESSOR_PROCESSOS = "assessor-processos"
VARIAVEIS_DA_CONTA = {
    DESEMBARGADOR: ("LUPA_E2E_DES_USUARIO", "LUPA_E2E_DES_SENHA"),
    ASSESSOR_PROCESSOS: ("LUPA_E2E_PROC_USUARIO", "LUPA_E2E_PROC_SENHA"),
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Ordena os testes E2E pelos arquivos de `ORDEM`, mantendo a ordem dentro de cada um."""
    posicao = {nome: indice for indice, nome in enumerate(ORDEM)}
    items.sort(key=lambda item: posicao.get(item.path.name, -1) if "e2e" in item.path.parts else -1)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    """Contexto do `pytest-playwright` no proxy, aceitando o certificado interno do Caddy."""
    return browser_context_args | ARGUMENTOS_DO_CONTEXTO


@pytest.fixture(scope="session")
def contas() -> dict[str, Conta]:
    """Contas que já fizeram o primeiro acesso nesta execução, por papel."""
    return {}


def obter_conta(browser: Browser, contas: dict[str, Conta], papel: str) -> Conta:
    """Conta do papel; faz o primeiro acesso pela tela se ainda não houver.

    Args:
        browser: Navegador da sessão.
        contas: Contas já prontas.
        papel: `desembargador` ou `assessor-processos`.

    Returns:
        Conta pronta.
    """
    if papel not in contas:
        usuario, senha = (variavel(nome) for nome in VARIAVEIS_DA_CONTA[papel])
        contexto = browser.new_context(**ARGUMENTOS_DO_CONTEXTO)
        try:
            contas[papel] = primeiro_acesso(contexto.new_page(), usuario, senha)
        finally:
            contexto.close()
    return contas[papel]


@pytest.fixture
def desembargador(browser: Browser, contas: dict[str, Conta]) -> Conta:
    """Desembargador da instalação (`e2e_preparar.py`), já com o primeiro acesso feito."""
    return obter_conta(browser, contas, DESEMBARGADOR)


@pytest.fixture
def assessor_processos(browser: Browser, contas: dict[str, Conta]) -> Conta:
    """Assessor do processo sintético (`e2e_processos.py`), já com o primeiro acesso feito."""
    return obter_conta(browser, contas, ASSESSOR_PROCESSOS)
