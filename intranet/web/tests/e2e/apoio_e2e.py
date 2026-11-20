"""Apoio da suíte E2E: ambiente preparado pelo `e2e.sh`, TOTP, contas e login pela tela."""

import base64
import hashlib
import hmac
import os
import re
import secrets
import struct
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Browser, BrowserContext, Page, StorageState, expect

URL_BASE = os.environ.get("LUPA_E2E_URL", "https://proxy:8443")
PERIODO_TOTP = 30
DIGITOS_TOTP = 6
PASSOS_DO_CODIGO_ERRADO = 50
INTERVALO_DE_ESPERA = 1.0
ARGUMENTOS_DO_CONTEXTO: dict[str, Any] = {
    "base_url": URL_BASE,
    "ignore_https_errors": True,
    "locale": "pt-BR",
}


def variavel(nome: str) -> str:
    """Valor de uma variável preparada pelo `e2e.sh`; falha se ausente.

    Args:
        nome: Nome da variável de ambiente.

    Returns:
        Valor não vazio.
    """
    valor = os.environ.get(nome, "")
    assert valor, f"{nome} ausente: rode via intranet/web/scripts/e2e.sh"
    return valor


def codigo_totp(segredo: str, passo: int) -> str:
    """Código TOTP (RFC 6238, SHA-1, 6 dígitos) do segredo base32 no passo dado.

    Args:
        segredo: Segredo base32 exibido na tela.
        passo: Número do passo de 30 s.

    Returns:
        Código de 6 dígitos.
    """
    chave = base64.b32decode(segredo.upper() + "=" * (-len(segredo) % 8))
    resumo = hmac.new(chave, struct.pack(">Q", passo), hashlib.sha1).digest()
    deslocamento = resumo[-1] & 0x0F
    numero = struct.unpack(">I", resumo[deslocamento : deslocamento + 4])[0] & 0x7FFFFFFF
    return str(numero % 10**DIGITOS_TOTP).zfill(DIGITOS_TOTP)


def passo_atual() -> int:
    """Passo TOTP do relógio real (o servidor confere pelo mesmo relógio)."""
    return int(time.time() // PERIODO_TOTP)


def segredo_da_uri(uri: str) -> str:
    """Segredo da URI `otpauth://` exibida no cadastro do autenticador.

    Args:
        uri: URI completa.

    Returns:
        Segredo base32.
    """
    partes = urlparse(uri)
    assert partes.scheme == "otpauth", "URI não é otpauth://"
    return parse_qs(partes.query)["secret"][0]


@dataclass
class Autenticador:
    """Aplicativo autenticador que nunca repete passo (o servidor recusa passo já usado)."""

    segredo: str
    ultimo: int = -1

    def proximo(self) -> str:
        """Código do passo corrente, esperando o passo seguinte se o corrente já foi usado."""
        while passo_atual() <= self.ultimo:
            time.sleep(INTERVALO_DE_ESPERA)
        self.ultimo = passo_atual()
        return codigo_totp(self.segredo, self.ultimo)

    def errado(self) -> str:
        """Código de um passo distante, certamente recusado."""
        return codigo_totp(self.segredo, passo_atual() + PASSOS_DO_CODIGO_ERRADO)


@dataclass
class Conta:
    """Conta que já fez o primeiro acesso, com a sessão do navegador guardada."""

    usuario: str
    senha: str
    autenticador: Autenticador
    estado: StorageState | None = None


def senha_nova() -> str:
    """Senha pessoal sintética com mais de 12 caracteres."""
    return f"frase-e2e-{secrets.token_urlsafe(9)}-lupa"


def enviar_senha(page: Page, usuario: str, senha: str) -> None:
    """Abre o login e envia usuário e senha (primeiro passo).

    Args:
        page: Página do navegador.
        usuario: Nome de usuário.
        senha: Senha.
    """
    page.goto("/login")
    page.get_by_label("Usuário").fill(usuario)
    page.get_by_label("Senha", exact=True).fill(senha)
    page.get_by_role("button", name="Continuar").click()


def cadastrar_autenticador(page: Page) -> Autenticador:
    """Lê o segredo do cadastro do MFA e devolve o autenticador correspondente.

    Args:
        page: Página no cadastro do autenticador.

    Returns:
        Autenticador com o segredo exibido.
    """
    expect(page.get_by_role("heading", name="Cadastre o autenticador")).to_be_visible()
    expect(page.locator(".qr svg")).to_be_visible()
    segredo = segredo_da_uri((page.get_by_test_id("uri-mfa").text_content() or "").strip())
    expect(page.get_by_test_id("segredo-mfa")).to_have_text(segredo)
    return Autenticador(segredo)


def trocar_senha(page: Page, atual: str) -> str:
    """Preenche a troca obrigatória de senha e devolve a senha nova.

    Args:
        page: Página na troca de senha.
        atual: Senha temporária.

    Returns:
        Senha pessoal definida.
    """
    senha = senha_nova()
    page.get_by_label("Senha atual").fill(atual)
    page.get_by_label("Nova senha", exact=True).fill(senha)
    page.get_by_label("Confirme a nova senha").fill(senha)
    page.get_by_role("button", name="Salvar nova senha").click()
    return senha


def primeiro_acesso(page: Page, usuario: str, temporaria: str) -> Conta:
    """Primeiro acesso completo: senha temporária, autenticador e troca de senha.

    Args:
        page: Página do navegador.
        usuario: Nome de usuário.
        temporaria: Senha temporária.

    Returns:
        Conta pronta, com a sessão do contexto.
    """
    enviar_senha(page, usuario, temporaria)
    autenticador = cadastrar_autenticador(page)
    page.get_by_label("Código de 6 dígitos").fill(autenticador.proximo())
    page.get_by_role("button", name="Confirmar autenticador").click()
    expect(page).to_have_url(re.compile(r"/trocar-senha$"))
    expect(page.get_by_text("defina uma senha pessoal")).to_be_visible()
    senha = trocar_senha(page, temporaria)
    expect(page.get_by_test_id("usuario-nome")).to_have_text(usuario)
    return Conta(usuario, senha, autenticador, page.context.storage_state())


def entrar(page: Page, conta: Conta) -> None:
    """Entrada com senha e código TOTP; guarda a sessão nova na conta.

    Args:
        page: Página do navegador.
        conta: Conta que já fez o primeiro acesso.
    """
    enviar_senha(page, conta.usuario, conta.senha)
    expect(page.get_by_role("heading", name="Verificação em duas etapas")).to_be_visible()
    page.get_by_label("Código de 6 dígitos").fill(conta.autenticador.proximo())
    page.get_by_role("button", name="Entrar").click()
    expect(page.get_by_test_id("usuario-nome")).to_have_text(conta.usuario)
    conta.estado = page.context.storage_state()


def contexto_como(
    browser: Browser, conta: Conta, tema: str = "", largura: int = 0
) -> tuple[BrowserContext, Page]:
    """Contexto autenticado na conta: reaproveita a sessão guardada ou entra pela tela.

    Args:
        browser: Navegador da sessão de testes.
        conta: Conta que já fez o primeiro acesso.
        tema: `claro` ou `escuro` gravado no `localStorage` antes da pintura; vazio mantém o padrão.
        largura: Largura da janela em pixels; zero mantém a padrão.

    Returns:
        Contexto e página prontos.
    """
    argumentos = ARGUMENTOS_DO_CONTEXTO | {"storage_state": conta.estado}
    if largura:
        argumentos["viewport"] = {"width": largura, "height": 812}
    contexto = browser.new_context(**argumentos)
    if tema:
        contexto.add_init_script(f"window.localStorage.setItem('lupa.tema', '{tema}')")
    page = contexto.new_page()
    page.goto("/")
    if urlparse(page.url).path == "/login":
        entrar(page, conta)
    return contexto, page
