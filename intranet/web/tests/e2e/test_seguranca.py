"""E2E de segurança do front: sem `/api` no navegador, cabeçalhos, CSP e texto hostil (RF-INT-01).

O processo hostil de `e2e_semear_chat.py` traz marcação HTML e Markdown na página citada e uma
URL na segunda página, que a conferência do chat recusa.
"""

import re
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, expect

from tests.e2e.apoio_e2e import ARGUMENTOS_DO_CONTEXTO, Conta, contexto_como, variavel

pytestmark = pytest.mark.e2e

ROTAS_COM_CABECALHOS = ("/", "/login", "/processos", "/static/js/tema.js", "/static/favicon.svg")
FONTES_FROUXAS = ("'unsafe-inline'", "'unsafe-eval'", "'unsafe-hashes'", "*", "data:", "blob:")
CSP_ESPERADA = {
    "default-src": ["'none'"],
    "script-src": ["'self'"],
    "style-src": ["'self'"],
    "object-src": ["'none'"],
    "frame-ancestors": ["'none'"],
    "base-uri": ["'none'"],
    "form-action": ["'self'"],
}
VIGIA_DA_CSP = """
window.__violacoes = [];
document.addEventListener('securitypolicyviolation', (e) => {
  window.__violacoes.push(e.violatedDirective + ' ' + e.blockedURI);
});
"""
HSTS_MINIMO = re.compile(r"max-age=(\d{8,})")


def telas_do_assessor() -> list[str]:
    """Telas que o assessor percorre: início, lista e as telas do processo sintético."""
    processo = variavel("LUPA_E2E_PROC_ID")
    base = f"/processos/{processo}"
    telas = ("", "/dossie", "/visualizador", "/validacoes", "/chat")
    return ["/", "/processos", *(f"{base}{tela}" for tela in telas)]


def telas_do_desembargador() -> list[str]:
    """Telas exclusivas do desembargador."""
    return ["/usuarios", "/auditoria", f"/processos/{variavel('LUPA_E2E_CHAT_PROCESSO')}/chat"]


def ler_csp(valor: str) -> dict[str, list[str]]:
    """Diretivas da CSP com suas fontes.

    Args:
        valor: Cabeçalho `Content-Security-Policy`.

    Returns:
        Fontes por diretiva.
    """
    diretivas = (parte.split() for parte in valor.split(";") if parte.strip())
    return {nome.lower(): fontes for nome, *fontes in diretivas}


def interagir(page: Page, caminho: str) -> None:
    """Abre os elementos que mudam o estilo da tela (cadastro, zoom e tema).

    Args:
        page: Página na tela.
        caminho: Caminho da tela.
    """
    if caminho == "/processos":
        page.locator("summary", has_text="Novo processo").click()
        expect(page.get_by_label(re.compile("Arquivo PDF ou ZIP"))).to_be_visible()
    if caminho.endswith("/visualizador"):
        page.get_by_role("link", name="Aumentar zoom").click()
    page.get_by_label("Tema").select_option("claro")


def percorrer(contexto: BrowserContext, page: Page, caminhos: list[str]) -> list[str]:
    """Percorre as telas guardando cada pedido do navegador e cada violação de CSP.

    Args:
        contexto: Contexto autenticado.
        page: Página do contexto.
        caminhos: Telas a abrir.

    Returns:
        Caminhos pedidos ao servidor seguidos das violações, prefixadas por `csp:`.
    """
    pedidos: list[str] = []
    contexto.on("request", lambda pedido: pedidos.append(urlparse(pedido.url).path))
    contexto.add_init_script(VIGIA_DA_CSP)
    violacoes: list[str] = []
    for caminho in caminhos:
        page.goto(caminho)
        expect(page.get_by_role("heading", level=1).first).to_be_visible()
        interagir(page, caminho)
        encontradas = page.evaluate("window.__violacoes || []")
        violacoes.extend(f"csp:{caminho}: {violacao}" for violacao in encontradas)
    return pedidos + violacoes


def test_navegador_nao_faz_requisicao_para_api(
    browser: Browser, assessor_processos: Conta, desembargador: Conta
) -> None:
    """RF-INT-01: nenhuma tela pede `/api` e o proxy responde 404 a `/api/saude`."""
    pedidos: list[str] = []
    for conta, caminhos in (
        (assessor_processos, telas_do_assessor()),
        (desembargador, telas_do_desembargador()),
    ):
        contexto, page = contexto_como(browser, conta)
        pedidos.extend(percorrer(contexto, page, caminhos))
        assert page.request.get("/api/saude").status == 404
        contexto.close()
    assert pedidos
    assert [p for p in pedidos if p == "/api" or p.startswith("/api/")] == []


def test_nenhuma_violacao_de_csp_ao_navegar_pelas_telas(
    browser: Browser, assessor_processos: Conta, desembargador: Conta
) -> None:
    """RF-INT-01: as telas e suas interações não violam a CSP (nada inline)."""
    violacoes: list[str] = []
    for conta, caminhos in (
        (assessor_processos, telas_do_assessor()),
        (desembargador, telas_do_desembargador()),
    ):
        contexto, page = contexto_como(browser, conta)
        violacoes.extend(p for p in percorrer(contexto, page, caminhos) if p.startswith("csp:"))
        contexto.close()
    assert violacoes == []


def test_cabecalhos_de_seguranca_com_csp_restritiva(browser: Browser) -> None:
    """RF-INT-01: o proxy põe HSTS, CSP sem exceção e os demais cabeçalhos em todas as rotas."""
    contexto = browser.new_context(**ARGUMENTOS_DO_CONTEXTO)
    for rota in ROTAS_COM_CABECALHOS:
        cabecalhos = contexto.request.get(rota, max_redirects=0).headers
        assert HSTS_MINIMO.search(cabecalhos.get("strict-transport-security", "")), rota
        for permissao in ("camera=()", "microphone=()", "geolocation=()"):
            assert permissao in cabecalhos.get("permissions-policy", ""), rota
        assert cabecalhos.get("cross-origin-opener-policy") == "same-origin", rota
        assert cabecalhos.get("x-content-type-options") == "nosniff", rota
        assert cabecalhos.get("referrer-policy") == "same-origin", rota
        assert cabecalhos.get("x-frame-options") == "DENY", rota
        assert "server" not in cabecalhos, rota
        csp = ler_csp(cabecalhos.get("content-security-policy", ""))
        assert {nome: csp.get(nome) for nome in CSP_ESPERADA} == CSP_ESPERADA, rota
        todas = [fonte for fontes in csp.values() for fonte in fontes]
        assert [f for f in FONTES_FROUXAS if f in todas] == [], rota
    contexto.close()


def test_html_sem_script_nem_estilo_inline(browser: Browser) -> None:
    """RF-INT-01: o HTML do front só carrega scripts e estilos por arquivo."""
    contexto = browser.new_context(**ARGUMENTOS_DO_CONTEXTO)
    html = contexto.request.get("/login").text()
    assert re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html) is None
    assert re.search(r"\sstyle=|<style", html) is None
    assert re.search(r"\son[a-z]+=", html) is None
    contexto.close()


def test_fontes_vem_da_propria_origem(browser: Browser) -> None:
    """RF-VIS-02: as fontes Source saem do próprio front e a CSP só admite `font-src 'self'`."""
    contexto = browser.new_context(**ARGUMENTOS_DO_CONTEXTO)
    page = contexto.new_page()
    fontes: list[str] = []
    page.on("request", lambda p: fontes.append(p.url) if p.resource_type == "font" else None)
    resposta = page.goto("/login")
    assert resposta is not None
    page.evaluate("document.fonts.ready.then(() => true)")
    origem = urlparse(page.url).netloc
    assert any(urlparse(url).path.endswith(".woff2") for url in fontes), fontes
    assert [url for url in fontes if urlparse(url).netloc != origem] == []
    assert page.evaluate("document.fonts.check('16px \"Source Sans 3\"')")
    csp = ler_csp(resposta.headers.get("content-security-policy", ""))
    assert csp.get("font-src") == ["'self'"]
    contexto.close()


def test_texto_hostil_dos_autos_sai_como_texto(browser: Browser, desembargador: Conta) -> None:
    """RF-INT-01: marcação dos autos citada no chat vira texto, sem script nem link externo."""
    processo = variavel("LUPA_E2E_HOSTIL_PROCESSO")
    contexto, page = contexto_como(browser, desembargador)
    contexto.add_init_script(VIGIA_DA_CSP)
    page.goto(f"/processos/{processo}/chat")
    mensagens = page.get_by_test_id("conversa-atual").get_by_test_id("mensagem")
    page.get_by_label("Pergunta", exact=True).fill("Quando a parte apelada foi intimada?")
    page.get_by_role("button", name="Perguntar").click()
    resposta = mensagens.last
    expect(resposta).to_have_attribute("data-status", "respondida")
    citacao = resposta.get_by_test_id("citacao")
    expect(citacao).to_contain_text("<script>window.__lupaXss = 1</script>")
    expect(citacao).to_contain_text("[link](#externo-e2e)")
    assert page.evaluate("window.__lupaXss") is None
    assert page.locator("main script").count() == 0
    assert page.locator('a[href^="http"]').count() == 0
    assert page.locator('a[href$="#externo-e2e"]').count() == 0
    destino = citacao.get_attribute("href") or ""
    assert destino.startswith(f"/processos/{processo}/visualizador?")
    assert re.search("script|exemplo|link", destino) is None
    page.reload()
    expect(page.get_by_test_id("citacao").first).to_contain_text("[link](#externo-e2e)")
    page.get_by_label("Pergunta", exact=True).fill("Qual é o endereço da certidão?")
    page.get_by_role("button", name="Perguntar").click()
    expect(mensagens.last).to_have_attribute("data-status", "descartada")
    expect(mensagens.last.get_by_test_id("citacao")).to_have_count(0)
    expect(page.get_by_test_id("processo-em-revisao")).to_be_visible()
    expect(page.locator("main")).not_to_contain_text("http://exemplo.invalid")
    assert page.locator('a[href^="http"]').count() == 0
    assert page.evaluate("window.__violacoes") == []
    contexto.close()
