"""Capturas de tela dos guias e conferência visual das telas, sobre os processos sintéticos.

`test_gera_capturas_dos_guias` grava em `LUPA_CAPTURAS_DIR` os PNGs que `docs/guias/*.md`
referenciam; `test_retrata_as_telas_nos_temas_e_no_celular` grava cada tela nos temas claro e
escuro e na largura de celular em `LUPA_CAPTURAS_VISUAL`. Rodam pelo `capturas.sh`, numa stack
nova (RNF-09); não conferem regra, só navegam e fotografam.
"""

import os
import re
import tempfile
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, ViewportSize, expect

from tests.e2e.apoio_e2e import ARGUMENTOS_DO_CONTEXTO, Conta, contexto_como, variavel

pytestmark = pytest.mark.e2e

JANELA_DOS_GUIAS: ViewportSize = {"width": 1200, "height": 760}
LARGURA_DO_CELULAR = 375
LARGURA_DA_MESA = 1200
PRAZO_DA_CAPA_MS = 60_000
TEMAS = ("claro", "escuro")


def _pasta(variavel_de_ambiente: str, padrao: str) -> Path:
    pasta = Path(os.environ.get(variavel_de_ambiente) or Path(tempfile.gettempdir()) / padrao)
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def foto(page: Page, pasta: Path, nome: str, inteira: bool = False) -> None:
    """Grava a tela atual como PNG, depois de a rede sossegar.

    Args:
        page: Página do navegador.
        pasta: Pasta de saída.
        nome: Nome do arquivo sem extensão.
        inteira: Se captura a página inteira, além da janela.
    """
    page.wait_for_load_state("networkidle")
    page.screenshot(
        path=pasta / f"{nome}.png", animations="disabled", scale="css", full_page=inteira
    )


def test_gera_capturas_dos_guias(
    browser: Browser, assessor_processos: Conta, desembargador: Conta
) -> None:
    """RNF-09: as onze capturas de `docs/imagens/` saem das telas reais com dados sintéticos."""
    pasta = _pasta("LUPA_CAPTURAS_DIR", "lupa-capturas")
    processo = variavel("LUPA_E2E_PROC_ID")
    chat = variavel("LUPA_E2E_CHAT_PROCESSO")
    janela = ARGUMENTOS_DO_CONTEXTO | {"viewport": JANELA_DOS_GUIAS}
    anonimo = browser.new_context(**janela)
    page = anonimo.new_page()
    page.goto("/login")
    expect(page.get_by_label("Usuário")).to_be_visible()
    foto(page, pasta, "login")
    anonimo.close()

    contexto, page = contexto_como(browser, assessor_processos)
    page.set_viewport_size(JANELA_DOS_GUIAS)
    page.goto("/processos")
    expect(page.get_by_role("link", name=re.compile(r"\d{7}-\d{2}")).first).to_be_visible()
    page.locator("summary", has_text="Novo processo").click()
    expect(page.get_by_label(re.compile("Arquivo PDF ou ZIP"))).to_be_visible()
    foto(page, pasta, "processos")
    page.goto(f"/processos/{processo}")
    expect(page.get_by_role("heading", name="Enviar autos")).to_be_visible()
    expect(page.get_by_text("Terceira Câmara Cível").first).to_be_visible(timeout=PRAZO_DA_CAPA_MS)
    foto(page, pasta, "processo")
    page.goto(f"/processos/{processo}/dossie")
    expect(page.get_by_test_id("indice-pecas").locator("tbody tr").first).to_be_visible()
    foto(page, pasta, "dossie")
    page.get_by_test_id("evento").first.click()
    expect(page.get_by_test_id("destaque-evidencia").first).to_be_visible()
    foto(page, pasta, "visualizador")
    page.goto(f"/processos/{processo}/validacoes")
    expect(page.get_by_test_id("achado").first).to_be_visible()
    foto(page, pasta, "validacoes")
    fato_de_data = (
        page.get_by_test_id("fato").filter(has_text=re.compile(r"\d{2}/\d{2}/\d{4}")).first
    )
    fato_de_data.locator("summary", has_text="Corrigir").click()
    expect(fato_de_data.get_by_label("Valor corrigido")).to_be_visible()
    foto(page, pasta, "corrigir-fato")
    contexto.close()

    contexto, page = contexto_como(browser, desembargador)
    page.set_viewport_size(JANELA_DOS_GUIAS)
    page.goto(f"/processos/{chat}/chat")
    expect(page.get_by_role("heading", name="Chat sobre os autos")).to_be_visible()
    for pergunta in ("Quando a parte apelada foi intimada?", "Como devo votar neste recurso?"):
        mensagens = page.get_by_test_id("conversa-atual").get_by_test_id("mensagem")
        antes = mensagens.count()
        page.get_by_label("Pergunta", exact=True).fill(pergunta)
        page.get_by_role("button", name="Perguntar").click()
        expect(mensagens).to_have_count(antes + 2)
    expect(page.get_by_test_id("citacao")).to_be_visible()
    foto(page, pasta, "chat")
    page.goto("/auditoria")
    expect(page.get_by_test_id("evento").first).to_be_visible()
    foto(page, pasta, "auditoria")
    page.get_by_label("Por").select_option("processo")
    page.get_by_label("Identificador").fill(chat)
    page.get_by_role("button", name="Gerar relatório").click()
    custo = page.get_by_test_id("custo-estimado")
    expect(custo).to_be_visible()
    custo.evaluate("(el) => el.scrollIntoView({ block: 'end' })")
    expect(custo).to_be_in_viewport()
    foto(page, pasta, "relatorio-uso")
    page.goto("/usuarios")
    expect(page.get_by_test_id("linha-usuario").first).to_be_visible()
    foto(page, pasta, "usuarios")
    contexto.close()


def _telas_do_assessor(processo: str) -> list[tuple[str, str]]:
    base = f"/processos/{processo}"
    return [
        ("inicio-assessor", "/"),
        ("processos", "/processos"),
        ("processo", base),
        ("dossie", f"{base}/dossie"),
        ("visualizador", f"{base}/visualizador"),
        ("validacoes", f"{base}/validacoes"),
        ("acesso-negado", "/usuarios"),
        ("trocar-senha", "/trocar-senha"),
    ]


def _telas_do_desembargador(processo: str, chat: str) -> list[tuple[str, str]]:
    return [
        ("inicio-desembargador", "/"),
        ("chat", f"/processos/{chat}/chat"),
        ("descartar", f"/processos/{processo}/descartar"),
        ("auditoria", "/auditoria?relatorio_tipo=processo&relatorio_id=" + chat),
        ("usuarios", "/usuarios"),
        ("nao-encontrado", "/processos/" + "0" * 64),
    ]


def _retratar(page: Page, pasta: Path, sufixo: str, telas: list[tuple[str, str]]) -> None:
    for nome, caminho in telas:
        page.goto(caminho)
        foto(page, pasta, f"{nome}-{sufixo}", inteira=True)


def test_retrata_as_telas_nos_temas_e_no_celular(
    browser: Browser, assessor_processos: Conta, desembargador: Conta
) -> None:
    """RNF-09: cada tela em página inteira, claro e escuro, na mesa e no celular (375 px)."""
    pasta = _pasta("LUPA_CAPTURAS_VISUAL", "lupa-visual")
    processo = variavel("LUPA_E2E_PROC_ID")
    chat = variavel("LUPA_E2E_CHAT_PROCESSO")
    for tema in TEMAS:
        for largura in (LARGURA_DA_MESA, LARGURA_DO_CELULAR):
            sufixo = f"{tema}-{largura}"
            anonimo = browser.new_context(
                **ARGUMENTOS_DO_CONTEXTO, viewport={"width": largura, "height": 812}
            )
            anonimo.add_init_script(f"window.localStorage.setItem('lupa.tema', '{tema}')")
            page = anonimo.new_page()
            page.goto("/login")
            foto(page, pasta, f"login-{sufixo}", inteira=True)
            page.get_by_label("Usuário").fill(desembargador.usuario)
            page.get_by_label("Senha", exact=True).fill(desembargador.senha)
            page.get_by_role("button", name="Continuar").click()
            expect(page.get_by_role("heading", name="Verificação em duas etapas")).to_be_visible()
            foto(page, pasta, f"codigo-{sufixo}", inteira=True)
            anonimo.close()
            for conta, telas in (
                (assessor_processos, _telas_do_assessor(processo)),
                (desembargador, _telas_do_desembargador(processo, chat)),
            ):
                contexto, page = contexto_como(browser, conta, tema, largura)
                _retratar(page, pasta, sufixo, telas)
                contexto.close()
