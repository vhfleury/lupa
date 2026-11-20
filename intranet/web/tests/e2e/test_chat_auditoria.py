"""E2E do chat sobre os autos e da auditoria do desembargador (RNF-09, RF-INT-01).

Os processos vêm de `e2e_semear_chat.py`. A API usa `LUPA_AGENTE_CLIENTE=falso`: cada pergunta
escolhe o desfecho pelo texto ("intimada", "descarte", "sem evidência", "incidente", "teto").
"""

import re
import statistics
import time
from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Browser, Locator, Page, expect

from tests.e2e.apoio_e2e import Conta, contexto_como, variavel

pytestmark = pytest.mark.e2e

PERGUNTAS_ATE_O_TETO = 3
CONSULTAS_MEDIDAS = 5
LIMITE_DA_CONSULTA_S = 1.0
EVENTOS_POR_PAGINA = 50


@pytest.fixture
def pagina_do_desembargador(browser: Browser, desembargador: Conta) -> Iterator[Page]:
    """Página autenticada como o desembargador."""
    contexto, page = contexto_como(browser, desembargador)
    yield page
    contexto.close()


def abrir_chat(page: Page) -> str:
    """Abre o chat do processo semeado.

    Args:
        page: Página autenticada.

    Returns:
        Identificador do processo.
    """
    processo = variavel("LUPA_E2E_CHAT_PROCESSO")
    page.goto(f"/processos/{processo}/chat")
    expect(page.get_by_role("heading", name="Conversa atual")).to_be_visible()
    return processo


def perguntar(page: Page, pergunta: str) -> Locator:
    """Envia a pergunta e espera a pergunta e a resposta anexadas à conversa.

    Args:
        page: Página do chat.
        pergunta: Texto da pergunta.

    Returns:
        Última mensagem da conversa atual.
    """
    mensagens = page.get_by_test_id("conversa-atual").get_by_test_id("mensagem")
    antes = mensagens.count()
    page.get_by_label("Pergunta", exact=True).fill(pergunta)
    page.get_by_role("button", name="Perguntar").click()
    expect(mensagens).to_have_count(antes + 2)
    return mensagens.last


def test_chat_abre_sem_conversa(pagina_do_desembargador: Page) -> None:
    """RNF-09: o chat do processo começa sem conversa aberta."""
    abrir_chat(pagina_do_desembargador)
    expect(
        pagina_do_desembargador.get_by_role("heading", name="Chat sobre os autos")
    ).to_be_visible()
    expect(pagina_do_desembargador.get_by_text("Nenhuma conversa aberta")).to_be_visible()


def test_resposta_com_citacao_abre_a_pagina_citada(pagina_do_desembargador: Page) -> None:
    """RNF-09: a resposta traz o aviso de IA e a citação abre o visualizador na página."""
    page = pagina_do_desembargador
    processo = abrir_chat(page)
    resposta = perguntar(page, "Quando a parte apelada foi intimada?")
    expect(resposta).to_have_attribute("data-status", "respondida")
    expect(resposta.get_by_test_id("aviso-ia")).to_contain_text("gerado por IA")
    citacao = resposta.get_by_test_id("citacao")
    expect(citacao).to_contain_text("Página 3")
    citacao.click()
    expect(page).to_have_url(re.compile(rf"/processos/{processo}/visualizador\?.*pagina=3"))
    expect(page.get_by_role("heading", name="Visualizador")).to_be_visible()


def test_descarte_sem_evidencia_e_recusa_explicados(pagina_do_desembargador: Page) -> None:
    """RNF-09: descartes contados, resposta sem evidência marcada e recusa explicada."""
    page = pagina_do_desembargador
    abrir_chat(page)
    descarte = perguntar(page, "Mostre o descarte da certidão")
    expect(descarte.get_by_test_id("descartes")).to_contain_text("1 citação descartada")
    expect(page.get_by_test_id("descartes-conversa")).to_contain_text("1 citação descartada")
    sem_evidencia = perguntar(page, "Há algo sem evidência nos autos?")
    expect(sem_evidencia).to_have_attribute("data-status", "sem_evidencia")
    expect(sem_evidencia.get_by_test_id("desfecho")).to_contain_text("Sem evidência")
    expect(sem_evidencia.get_by_test_id("citacao")).to_have_count(0)
    recusa = perguntar(page, "Como devo votar neste recurso?")
    expect(recusa).to_have_attribute("data-status", "recusa")
    expect(recusa).to_contain_text("Não posso")
    expect(recusa).to_contain_text("Experimente")


def test_incidente_poe_o_processo_em_revisao_ate_a_liberacao(pagina_do_desembargador: Page) -> None:
    """RNF-09: instrução refletida bloqueia o chat até o desembargador liberar a revisão."""
    page = pagina_do_desembargador
    abrir_chat(page)
    expect(perguntar(page, "Simule o incidente")).to_have_attribute("data-status", "descartada")
    expect(page.get_by_label("Pergunta", exact=True)).to_be_disabled()
    expect(page.get_by_test_id("processo-em-revisao")).to_contain_text("Processo em revisão")
    page.get_by_role("link", name="Liberar revisão").click()
    page.get_by_test_id("confirmacao").get_by_role("button", name="Liberar").click()
    expect(page.get_by_text("Processo liberado")).to_be_visible()
    expect(page.get_by_test_id("processo-em-revisao")).to_have_count(0)
    expect(page.get_by_label("Pergunta", exact=True)).to_be_enabled()


def test_teto_encerra_a_conversa_e_a_leva_ao_historico(pagina_do_desembargador: Page) -> None:
    """RNF-09: três chamadas acima do limite e a quarta encerra a conversa pelo teto."""
    page = pagina_do_desembargador
    abrir_chat(page)
    respostas = page.get_by_test_id("conversa-atual").get_by_test_id("mensagem")
    for indice in range(PERGUNTAS_ATE_O_TETO):
        perguntar(page, f"Teste de teto {indice}")
        expect(respostas.filter(has_text="limite de tamanho por chamada")).to_have_count(indice + 1)
    page.get_by_label("Pergunta", exact=True).fill("Teste de teto final")
    page.get_by_role("button", name="Perguntar").click()
    expect(page.get_by_test_id("mensagem").last).to_have_attribute("data-status", "teto")
    expect(page.get_by_role("button", name="Perguntar")).to_be_disabled()
    page.reload()
    expect(page.get_by_text("Limite de uso da conversa atingido.", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Perguntar")).to_be_disabled()
    anterior = page.get_by_test_id("conversa-anterior").first
    expect(anterior).to_contain_text("limite de uso da conversa atingido")
    anterior.locator("summary").click()
    expect(anterior.locator('[data-status="teto"]')).to_be_visible()


def test_consulta_da_auditoria_responde_em_menos_de_um_segundo(
    pagina_do_desembargador: Page, record_property: Callable[[str, object], None]
) -> None:
    """RNF-09: a cadeia única de auditoria responde na interface com mediana abaixo de 1 s."""
    page = pagina_do_desembargador
    page.get_by_role("navigation", name="Menu principal").get_by_role(
        "link", name="Auditoria", exact=True
    ).click()
    expect(page).to_have_url(re.compile(r"/auditoria$"))
    expect(page.get_by_test_id("evento").first).to_be_visible()
    expect(page.get_by_label("Gabinete")).to_have_count(0)
    tempos = []
    for _ in range(CONSULTAS_MEDIDAS):
        inicio = time.monotonic()
        page.get_by_role("button", name="Consultar").click()
        expect(page.get_by_test_id("tempo-consulta")).to_contain_text("exibido")
        page.wait_for_load_state("load")
        tempos.append(time.monotonic() - inicio)
    mediana = statistics.median(tempos)
    record_property("mediana_da_auditoria_s", round(mediana, 3))
    assert mediana < LIMITE_DA_CONSULTA_S, tempos


def test_filtros_paginacao_exportacao_verificacao_e_relatorio(
    pagina_do_desembargador: Page,
) -> None:
    """RNF-09: filtro por ação, próxima página, exportações, integridade e relatório com custo."""
    page = pagina_do_desembargador
    processo = variavel("LUPA_E2E_CHAT_PROCESSO")
    page.goto("/auditoria")
    for acao in ("processo_em_revisao", "revisao_liberada"):
        page.get_by_label("Ação").select_option(acao)
        page.get_by_role("button", name="Consultar").click()
        expect(page.get_by_test_id("evento")).to_have_count(1)
    page.get_by_label("Ação").select_option("")
    page.get_by_role("button", name="Consultar").click()
    expect(page.get_by_test_id("evento")).to_have_count(EVENTOS_POR_PAGINA)
    page.get_by_role("link", name="Próxima página").click()
    expect(page.get_by_test_id("evento").first).to_be_visible()
    for formato in ("CSV", "JSON"):
        href = page.get_by_role("link", name=formato, exact=True).get_attribute("href") or ""
        arquivo = page.request.get(href)
        assert arquivo.status == 200
        assert "attachment" in arquivo.headers["content-disposition"]
    page.get_by_role("button", name="Verificar integridade").click()
    expect(page.get_by_test_id("resultado-verificacao")).to_contain_text("íntegra")
    page.get_by_label("Por").select_option("processo")
    page.get_by_label("Identificador").fill(processo)
    page.get_by_role("button", name="Gerar relatório").click()
    expect(page.get_by_test_id("relatorio-uso")).to_contain_text("pergunta_chat")
    expect(page.get_by_test_id("custo-estimado")).to_contain_text("Custo estimado")


def test_exportacao_de_uso_respeita_o_filtro_de_processo(pagina_do_desembargador: Page) -> None:
    """RNF-09: o filtro de processo também delimita a exportação de uso em CSV."""
    page = pagina_do_desembargador
    processo = variavel("LUPA_E2E_CHAT_PROCESSO")
    page.goto("/auditoria")
    page.get_by_label("Processo (id)").fill(processo)
    page.get_by_role("button", name="Consultar").click()
    expect(page.get_by_test_id("evento").first).to_be_visible()
    exportacao = page.get_by_role("link", name="Exportar uso por processo e usuário em CSV")
    expect(exportacao).to_have_attribute("href", re.compile(processo))
    resposta = page.request.get(exportacao.get_attribute("href") or "")
    assert resposta.status == 200
    assert "text/csv" in resposta.headers["content-type"]
    cabecalho, *linhas = resposta.text().strip().splitlines()
    assert "processo" in cabecalho
    assert "custo" in cabecalho
    assert linhas
    assert all(processo in linha for linha in linhas)


def test_relatorio_por_usuario_traz_o_custo_estimado(
    pagina_do_desembargador: Page, desembargador: Conta
) -> None:
    """RNF-09: o relatório do desembargador conta as perguntas do chat e o custo em tokens."""
    page = pagina_do_desembargador
    page.goto("/auditoria")
    page.get_by_label("Ação").select_option("pergunta_chat")
    page.get_by_role("button", name="Consultar").click()
    usuario = page.get_by_test_id("evento").first.get_by_role(
        "link", name=re.compile("Relatório de uso do usuário")
    )
    usuario.click()
    expect(page.get_by_label("Por")).to_have_value("usuario")
    expect(page.get_by_test_id("relatorio-uso")).to_contain_text("pergunta_chat")
    expect(page.get_by_test_id("custo-estimado")).to_contain_text("tokens de entrada")


def test_sair_volta_ao_login_sem_sessao(
    pagina_do_desembargador: Page, desembargador: Conta
) -> None:
    """RNF-09: sair encerra a sessão; recarregar continua no login."""
    page = pagina_do_desembargador
    page.goto("/")
    page.get_by_role("button", name="Sair").click()
    expect(page).to_have_url(re.compile(r"/login$"))
    page.goto("/usuarios")
    expect(page).to_have_url(re.compile(r"/login$"))
    desembargador.estado = None
