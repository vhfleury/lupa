"""E2E de acessibilidade: axe-core nos dois temas, teclado com foco visível e tema manual (RNF-09).

Reutiliza as contas criadas pelos fluxos; a varredura não aceita violação séria ou crítica das
regras WCAG 2.1 A e AA, contraste incluído.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, expect

from tests.e2e.apoio_e2e import ARGUMENTOS_DO_CONTEXTO, Conta, contexto_como, variavel

pytestmark = pytest.mark.e2e

TEMAS = ("claro", "escuro")
AXE = files("axe_playwright_python").joinpath("axe.min.js").read_text(encoding="utf-8")
GRAVES = {"serious", "critical"}
REGRAS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
TABS_NO_CABECALHO = 12
TABS_ATE_A_PERGUNTA = 6
FOCO_VISIVEL = """() => {
  const el = document.activeElement;
  if (!el || el === document.body) return false;
  const estilo = getComputedStyle(el);
  return estilo.outlineStyle !== 'none' && parseFloat(estilo.outlineWidth) >= 2;
}"""
DESCREVER_FOCO = """() => {
  const el = document.activeElement;
  if (!el || el === document.body) return 'body:';
  const id = el.getAttribute('id');
  const rotulo = el.getAttribute('aria-label')
    ?? (id ? document.querySelector(`label[for="${id}"]`)?.textContent : null)
    ?? Array.from(el.childNodes)
      .filter((n) => !(n instanceof Element && n.getAttribute('aria-hidden') === 'true'))
      .map((n) => n.textContent).join('');
  return `${el.tagName.toLowerCase()}:${rotulo.trim().replace(/\\s+/g, ' ')}`;
}"""


@dataclass(frozen=True)
class Tela:
    """Tela varrida pelo axe: papel (vazio para anônimo), caminho e título `h1` esperado."""

    papel: str
    caminho: Callable[[], str]
    titulo: re.Pattern[str]


def _processo(tela: str = "") -> Callable[[], str]:
    return lambda: f"/processos/{variavel('LUPA_E2E_PROC_ID')}{tela}"


TELAS = (
    Tela("", lambda: "/login", re.compile(r"^Bem-vindo ao Lupa$")),
    Tela("assessor", lambda: "/", re.compile("Minha área de trabalho")),
    Tela("assessor", lambda: "/processos", re.compile(r"^Processos$")),
    Tela("assessor", _processo(), re.compile(r"\d{7}-\d{2}")),
    Tela("assessor", _processo("/dossie"), re.compile("Dossiê")),
    Tela("assessor", _processo("/visualizador"), re.compile("Visualizador")),
    Tela("assessor", _processo("/validacoes"), re.compile("Validações")),
    Tela(
        "desembargador",
        lambda: f"/processos/{variavel('LUPA_E2E_CHAT_PROCESSO')}/chat",
        re.compile("Chat sobre os autos"),
    ),
    Tela("desembargador", lambda: "/usuarios", re.compile("Usuários")),
    Tela("desembargador", lambda: "/auditoria", re.compile("Auditoria")),
)


def foco_visivel(page: Page) -> bool:
    """Se o elemento focado tem contorno visível de pelo menos 2 px."""
    return bool(page.evaluate(FOCO_VISIVEL))


def descrever_foco(page: Page) -> str:
    """`tag:nome acessível` do elemento focado; falha se o foco não estiver visível."""
    descricao = str(page.evaluate(DESCREVER_FOCO))
    if descricao != "body:":
        assert foco_visivel(page), f"foco invisível em {descricao}"
    return descricao


def abrir(
    browser: Browser, contas: dict[str, Conta], papel: str, tema: str
) -> tuple[BrowserContext, Page]:
    """Contexto da tela no tema pedido, autenticado quando a tela tem papel.

    Args:
        browser: Navegador.
        contas: Contas por papel (`assessor` e `desembargador`).
        papel: Papel da tela ou vazio.
        tema: `claro` ou `escuro`.

    Returns:
        Contexto e página.
    """
    if papel:
        return contexto_como(browser, contas[papel], tema)
    contexto = browser.new_context(**ARGUMENTOS_DO_CONTEXTO)
    contexto.add_init_script(f"window.localStorage.setItem('lupa.tema', '{tema}')")
    return contexto, contexto.new_page()


def varrer(page: Page) -> list[dict[str, Any]]:
    """Violações do axe-core (WCAG 2.1 A e AA) na página atual.

    Args:
        page: Página carregada.

    Returns:
        Violações como o `axe.run` devolve.
    """
    page.evaluate(AXE)
    opcoes = {"runOnly": {"type": "tag", "values": REGRAS_WCAG}, "resultTypes": ["violations"]}
    resultado = page.evaluate("(opcoes) => axe.run(document, opcoes)", opcoes)
    violacoes: list[dict[str, Any]] = resultado["violations"]
    return violacoes


@pytest.mark.parametrize("tema", TEMAS)
def test_axe_sem_violacao_grave_em_todas_as_telas(
    browser: Browser, assessor_processos: Conta, desembargador: Conta, tema: str
) -> None:
    """RNF-09: nenhuma violação séria ou crítica do axe em nenhuma tela, nos dois temas."""
    contas = {"assessor": assessor_processos, "desembargador": desembargador}
    achados: list[str] = []
    for tela in TELAS:
        contexto, page = abrir(browser, contas, tela.papel, tema)
        caminho = tela.caminho()
        page.goto(caminho)
        expect(page.get_by_role("heading", level=1).first).to_have_text(tela.titulo)
        if caminho == "/processos":
            page.locator("summary", has_text="Novo processo").click()
        expect(page.locator("html")).to_have_attribute("data-tema", tema)
        for violacao in varrer(page):
            if violacao["impact"] in GRAVES:
                alvos = " | ".join(" ".join(n["target"]) for n in violacao["nodes"][:5])
                achados.append(f"{caminho} [{tema}] {violacao['id']}: {alvos}")
        contexto.close()
    assert achados == [], "\n".join(achados)


def test_login_inteiro_pelo_teclado_com_foco_visivel(page: Page) -> None:
    """RNF-09: pular para o conteúdo, campos, botão e tema na ordem, com foco visível."""
    page.goto("/login")
    expect(page.get_by_label("Usuário")).to_be_focused()
    page.keyboard.press("Shift+Tab")
    pular = page.get_by_role("link", name="Pular para o conteúdo")
    expect(pular).to_be_focused()
    expect(pular).to_be_in_viewport()
    assert foco_visivel(page)
    focados = []
    for _ in range(4):
        page.keyboard.press("Tab")
        focados.append(descrever_foco(page))
    assert focados == ["input:Usuário", "input:Senha", "button:Continuar", "select:Tema"]
    page.get_by_label("Usuário").focus()
    page.keyboard.press("Enter")
    expect(page).to_have_url(re.compile("/login"))


def test_telas_internas_pelo_teclado(browser: Browser, desembargador: Conta) -> None:
    """RNF-09: cabeçalho e menu pelo teclado; pular leva ao conteúdo e à pergunta do chat."""
    contexto, page = contexto_como(browser, desembargador)
    vistos = set()
    for _ in range(TABS_NO_CABECALHO):
        page.keyboard.press("Tab")
        vistos.add(descrever_foco(page))
    esperados = {"a:Pular para o conteúdo", "a:Lupa", "select:Tema", "button:Sair"}
    assert esperados | {"a:Processos", "a:Auditoria"} <= vistos, vistos
    page.get_by_role("link", name="Pular para o conteúdo").focus()
    page.keyboard.press("Enter")
    expect(page.locator("main#conteudo")).to_be_focused()
    menu = page.get_by_role("navigation", name="Menu principal")
    for nome in ("Auditoria", "Usuários", "Processos"):
        page.keyboard.press("Shift+Tab")
        expect(menu.get_by_role("link", name=nome)).to_be_focused()
    page.keyboard.press("Enter")
    expect(page).to_have_url(re.compile(r"/processos$"))
    page.goto(f"/processos/{variavel('LUPA_E2E_HOSTIL_PROCESSO')}/chat")
    expect(page.get_by_label("Pergunta", exact=True)).to_be_enabled()
    page.get_by_role("link", name="Pular para o conteúdo").focus()
    page.keyboard.press("Enter")
    focados = []
    for _ in range(TABS_ATE_A_PERGUNTA):
        page.keyboard.press("Tab")
        focados.append(descrever_foco(page))
    assert "textarea:Pergunta" in focados, focados
    contexto.close()


def test_visualizador_pelo_teclado_com_foco_visivel(
    browser: Browser, assessor_processos: Conta
) -> None:
    """RNF-09 (D8): com o foco visível na moldura, + e - mudam o zoom e o foco volta à moldura."""
    contexto, page = contexto_como(browser, assessor_processos)
    page.goto(f"/processos/{variavel('LUPA_E2E_PROC_ID')}/visualizador")
    moldura = page.get_by_test_id("moldura-pagina")
    moldura.focus()
    expect(moldura).to_be_focused()
    assert foco_visivel(page)
    page.keyboard.press("+")
    expect(page.get_by_test_id("zoom")).to_have_text("125%")
    expect(page.get_by_test_id("moldura-pagina")).to_be_focused()
    page.keyboard.press("-")
    expect(page.get_by_test_id("zoom")).to_have_text("100%")
    contexto.close()


def test_tema_manual_persiste_so_no_local_storage(browser: Browser) -> None:
    """RNF-09: claro, escuro e sistema; a escolha volta na recarga e nunca vai em cookie."""
    contexto = browser.new_context(**ARGUMENTOS_DO_CONTEXTO, color_scheme="light")
    page = contexto.new_page()
    page.goto("/login")

    def fundo() -> str:
        return str(page.evaluate("getComputedStyle(document.body).backgroundColor"))

    seletor = page.get_by_label("Tema")
    expect(seletor).to_have_value("escuro")
    expect(page.locator("html")).to_have_attribute("data-tema", "escuro")
    escuro = fundo()
    seletor.select_option("claro")
    expect(page.locator("html")).to_have_attribute("data-tema", "claro")
    claro = fundo()
    assert claro != escuro
    assert page.evaluate("localStorage.getItem('lupa.tema')") == "claro"
    page.reload()
    expect(page.locator("html")).to_have_attribute("data-tema", "claro")
    expect(page.get_by_label("Tema")).to_have_value("claro")
    page.get_by_label("Tema").select_option("sistema")
    expect(page.locator("html")).not_to_have_attribute("data-tema", re.compile("."))
    assert fundo() == claro
    page.reload()
    expect(page.get_by_label("Tema")).to_have_value("sistema")
    assert fundo() == claro
    assert "lupa.tema" not in [cookie["name"] for cookie in contexto.cookies()]
    contexto.close()
