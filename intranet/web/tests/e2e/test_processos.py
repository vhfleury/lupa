"""E2E de processos, cadastro por arquivo, dossiê, visualizador e validações (RNF-09, RF-INT-01).

O assessor e o processo sintético vêm de `e2e_processos.py`: o processo já está na fila do worker
real quando a suíte começa. O assessor faz o primeiro acesso pela tela.
"""

import os
import re
import secrets
import tempfile
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Browser, FilePayload, Page, expect

from tests.e2e.apoio_e2e import (
    ARGUMENTOS_DO_CONTEXTO,
    Conta,
    contexto_como,
    primeiro_acesso,
    variavel,
)
from tests.e2e.conftest import ASSESSOR_PROCESSOS

pytestmark = pytest.mark.e2e

ESTADOS_FINAIS = ("concluido", "em_revisao", "quarentena", "falho", "parcial")
PRAZO_DA_INGESTAO = 180.0
INTERVALO_DE_LEITURA = 0.25
MEGABYTES_GRANDE = int(os.environ.get("LUPA_E2E_UPLOAD_MB", "500"))
MEGABYTE = 1024 * 1024
MAIOR_INTERVALO_ENTRE_QUADROS_MS = 500
SEQUENCIAL_DA_CAPA = 9018754
EVENTOS_CONFERIDOS = 4
ANOS_RECUADOS = 11
PAGINA = re.compile(r"Página (\d+) de (\d+)")
PRAZO_DA_LISTA_MS = 120_000
processos_criados: list[str] = []


@pytest.fixture
def pagina_do_assessor(browser: Browser, assessor_processos: Conta) -> Iterator[Page]:
    """Página autenticada como o assessor do processo sintético."""
    contexto, page = contexto_como(browser, assessor_processos)
    yield page
    contexto.close()


def numero_cnj(sequencial: int, valido: bool) -> str:
    """Número CNJ sintético da 3ª Câmara (TJGO), com dígito verificador certo ou errado.

    Args:
        sequencial: Sequencial de 7 dígitos.
        valido: Se o dígito verificador confere.

    Returns:
        Número no formato `NNNNNNN-DD.AAAA.J.TR.OOOO`.
    """
    digito = 98 - int(f"{sequencial:07d}2025809000100") % 97
    if not valido:
        digito = (digito + 1) % 100
    return f"{sequencial:07d}-{digito:02d}.2025.8.09.0001"


def pdf_minimo(*linhas: str) -> bytes:
    """PDF de uma página com as linhas de texto, com os deslocamentos certos do xref.

    Args:
        *linhas: Linhas de texto ASCII.

    Returns:
        Bytes do PDF.
    """
    texto = " T* ".join(f"({linha}) Tj" for linha in linhas)
    conteudo = f"BT /F1 14 Tf 20 TL 72 720 Td {texto} ET"
    objetos = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(conteudo)} >>\nstream\n{conteudo}\nendstream",
    ]
    corpo = "%PDF-1.4\n"
    deslocamentos = []
    for indice, objeto in enumerate(objetos, start=1):
        deslocamentos.append(len(corpo.encode("latin-1")))
        corpo += f"{indice} 0 obj\n{objeto}\nendobj\n"
    xref = len(corpo.encode("latin-1"))
    corpo += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n"
    corpo += "".join(f"{d:010d} 00000 n \n" for d in deslocamentos)
    corpo += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return corpo.encode("latin-1")


def pdf(nome: str, conteudo: bytes) -> FilePayload:
    """Arquivo para o campo de envio.

    Args:
        nome: Nome do arquivo.
        conteudo: Bytes.

    Returns:
        Carga do `set_input_files`.
    """
    return {"name": nome, "mimeType": "application/pdf", "buffer": conteudo}


def arquivo_grande(megabytes: int) -> Path:
    """Arquivo sintético grande: cabeçalho PDF e bytes aleatórios, sem `%%EOF`.

    Args:
        megabytes: Tamanho em MiB.

    Returns:
        Caminho do arquivo temporário.
    """
    caminho = Path(tempfile.gettempdir()) / f"sintetico-{secrets.token_hex(4)}.pdf"
    bloco = secrets.token_bytes(MEGABYTE)
    with caminho.open("wb") as saida:
        saida.write(b"%PDF-1.7\n")
        for _ in range(megabytes):
            saida.write(bloco)
    return caminho


def estados_ate_o_final(page: Page, nome: str) -> list[str]:
    """Estados vistos na linha do arquivo até um estado final da ingestão.

    Args:
        page: Página do processo.
        nome: Trecho do nome do arquivo.

    Returns:
        Estados distintos, na ordem em que apareceram.
    """
    linha = page.get_by_test_id("lista-arquivos").locator("tr", has_text=nome)
    vistos: list[str] = []
    limite = time.monotonic() + PRAZO_DA_INGESTAO
    while time.monotonic() < limite:
        estado = linha.get_by_test_id("estado-arquivo").get_attribute("data-estado") or ""
        if not vistos or vistos[-1] != estado:
            vistos.append(estado)
        if estado in ESTADOS_FINAIS:
            return vistos
        page.wait_for_timeout(INTERVALO_DE_LEITURA * 1000)
    pytest.fail(f"{nome} sem estado final; vistos: {' → '.join(vistos)}")


def abrir_cadastro(page: Page) -> None:
    """Abre "+ Novo processo" na lista de processos.

    Args:
        page: Página da lista.
    """
    page.goto("/processos")
    page.locator("summary", has_text="Novo processo").click()
    expect(page.get_by_label(re.compile("Arquivo PDF ou ZIP"))).to_be_visible()


def enviar(page: Page, arquivo: FilePayload | Path) -> None:
    """Escolhe o arquivo no formulário visível e envia.

    Args:
        page: Página com o formulário de envio.
        arquivo: Carga ou caminho do arquivo.
    """
    formulario = page.locator("form.form-envio:visible")
    formulario.get_by_label(re.compile("Arquivo PDF ou ZIP")).set_input_files(arquivo)
    formulario.get_by_role("button", name="Enviar").click()


def test_primeiro_acesso_do_assessor_do_processo(page: Page, contas: dict[str, Conta]) -> None:
    """RNF-09: o assessor do processo sintético cadastra o autenticador e troca a senha."""
    usuario = variavel("LUPA_E2E_PROC_USUARIO")
    contas[ASSESSOR_PROCESSOS] = primeiro_acesso(page, usuario, variavel("LUPA_E2E_PROC_SENHA"))


def test_lista_mostra_o_processo_e_acompanha_a_fila(pagina_do_assessor: Page) -> None:
    """RNF-09: a lista mostra o processo sintético e a situação chega ao fim da ingestão."""
    page = pagina_do_assessor
    page.get_by_role("navigation", name="Menu principal").get_by_role(
        "link", name="Processos"
    ).click()
    expect(page).to_have_url(re.compile(r"/processos$"))
    linha = page.locator(f'tr[data-processo="{variavel("LUPA_E2E_PROC_ID")}"]')
    expect(linha).to_be_visible()
    expect(linha.get_by_test_id("situacao")).to_have_text(
        re.compile("Concluído|Com pendências"), timeout=PRAZO_DA_LISTA_MS
    )


def test_cadastro_completa_o_numero_e_acompanha_os_arquivos(pagina_do_assessor: Page) -> None:
    """RNF-09: número recusado pede outro; arquivo novo e truncado chegam ao estado final."""
    page = pagina_do_assessor
    sequencial = 1_000_000 + secrets.randbelow(8_000_000)
    abrir_cadastro(page)
    enviar(page, pdf("autos-sem-numero.pdf", pdf_minimo("Classe: Apelacao civel")))
    campo = page.get_by_label("Número CNJ")
    expect(campo).to_be_visible()
    expect(page.get_by_role("combobox", name="Classe", exact=True)).to_have_count(0)
    campo.fill(numero_cnj(sequencial, valido=False))
    page.get_by_role("button", name="Confirmar e reenviar").click()
    expect(page.locator(".resultado-envio").get_by_role("alert")).to_be_visible()
    page.get_by_label("Número CNJ").fill(numero_cnj(sequencial, valido=True))
    page.get_by_role("button", name="Confirmar e reenviar").click()
    expect(page).to_have_url(re.compile(r"/processos/[0-9a-f]{64}\?aviso=criado$"))
    expect(page.get_by_text("Processo criado e arquivo recebido.")).to_be_visible()
    processos_criados.append(urlparse(page.url).path.rsplit("/", 1)[-1])
    enviar(page, pdf("peca-e2e.pdf", pdf_minimo(f"Peca sintetica {sequencial}")))
    vistos = estados_ate_o_final(page, "peca-e2e.pdf")
    assert vistos[-1] in ("concluido", "em_revisao"), vistos
    enviar(page, pdf("truncado.pdf", b"%PDF-1.7\n1 0 obj << >> endobj\n"))
    assert "quarentena" in estados_ate_o_final(page, "truncado.pdf")
    linha = page.get_by_test_id("lista-arquivos").locator("tr", has_text="truncado.pdf")
    expect(linha.locator(".motivo")).to_have_text(re.compile("incompleto"))


def test_capa_reconhecida_leva_ao_mesmo_processo_e_classe_e_corrigida(
    pagina_do_assessor: Page,
) -> None:
    """RNF-09: criação, anexo e duplicata vão ao mesmo processo; a correção de classe fica."""
    page = pagina_do_assessor
    numero = numero_cnj(SEQUENCIAL_DA_CAPA, valido=True)
    primeiro = pdf_minimo(f"Numero do processo: {numero}", "Classe: Agravo interno")
    anexo = pdf_minimo(f"Numero do processo: {numero}", "Classe: Apelacao civel")
    destinos = set()
    for conteudo, aviso in (
        (primeiro, "Processo criado e arquivo recebido."),
        (anexo, "Arquivo anexado ao processo existente."),
        (anexo, "Este arquivo já foi enviado ao processo."),
    ):
        abrir_cadastro(page)
        enviar(page, pdf("autos.pdf", conteudo))
        expect(page.get_by_text(aviso)).to_be_visible()
        expect(page.get_by_role("heading", name=numero)).to_be_visible()
        destinos.add(urlparse(page.url).path)
    assert len(destinos) == 1
    page.locator("summary", has_text="Corrigir classe").click()
    page.get_by_label("Nova classe").select_option("agravo_instrumento")
    page.get_by_role("button", name="Salvar classe").click()
    expect(page.get_by_label("Última correção de classe")).to_contain_text("Agravo interno")


def test_envio_grande_mostra_progresso_sem_travar_a_interface(
    pagina_do_assessor: Page, record_property: Callable[[str, object], None]
) -> None:
    """RNF-09: o envio de centenas de MiB avança a barra e a página continua desenhando."""
    page = pagina_do_assessor
    assert processos_criados, "o cadastro anterior não criou processo"
    caminho = arquivo_grande(MEGABYTES_GRANDE)
    try:
        page.goto(f"/processos/{processos_criados[0]}")
        inicio = time.monotonic()
        enviar(page, caminho)
        barra = page.locator("form.form-envio .progresso progress")
        expect(barra).to_be_visible()
        maior = page.evaluate(
            """() => new Promise((resolver) => {
                let anterior = performance.now(); let maior = 0; const fim = anterior + 2000;
                const quadro = (agora) => {
                    maior = Math.max(maior, agora - anterior); anterior = agora;
                    if (agora < fim) requestAnimationFrame(quadro); else resolver(maior);
                };
                requestAnimationFrame(quadro);
            })"""
        )
        assert maior < MAIOR_INTERVALO_ENTRE_QUADROS_MS
        expect(barra).not_to_have_attribute("value", "0")
        expect(
            page.get_by_test_id("lista-arquivos").locator("tr", has_text="sintetico-")
        ).to_be_visible(timeout=540_000)
        record_property("segundos_do_envio", round(time.monotonic() - inicio, 1))
        record_property("maior_intervalo_entre_quadros_ms", round(maior))
        assert estados_ate_o_final(page, "sintetico-")[-1] in ("quarentena", "falho")
    finally:
        caminho.unlink()


def test_dossie_leva_cada_evento_a_pagina_certa(pagina_do_assessor: Page) -> None:
    """RNF-09: ficha, partes com evidência, índice e eventos abrindo a página citada."""
    page = pagina_do_assessor
    processo = variavel("LUPA_E2E_PROC_ID")
    page.goto(f"/processos/{processo}/dossie")
    expect(page.get_by_test_id("ficha")).to_contain_text(re.compile(r"\d{7}-\d{2}\.\d{4}"))
    partes = page.get_by_test_id("partes")
    expect(partes).to_contain_text(re.compile("Polo (ativo|passivo)", re.IGNORECASE))
    expect(partes.get_by_role("link").first).to_have_attribute(
        "href", re.compile(r"evidencia=[0-9a-f]{64}$")
    )
    partes.get_by_role("link").first.click()
    expect(page.get_by_test_id("destaque-evidencia").first).to_be_visible()
    page.goto(f"/processos/{processo}/dossie")
    expect(page.get_by_test_id("indice-pecas").locator("tbody tr").first).to_be_visible()
    total = min(page.get_by_test_id("evento").count(), EVENTOS_CONFERIDOS)
    assert total > 0
    for indice in range(total):
        page.goto(f"/processos/{processo}/dossie")
        evento = page.get_by_test_id("evento").nth(indice)
        folha = re.search(r"\(fl\. (\d+)\)", evento.text_content() or "")
        evento.click()
        expect(page).to_have_url(re.compile(r"/visualizador\?evidencia="))
        if folha:
            expect(page.get_by_test_id("pagina-atual")).to_have_text(
                re.compile(rf"^Página {folha.group(1)}\b")
            )
        expect(page.get_by_test_id("destaque-evidencia").first).to_be_visible()
        largura = page.get_by_test_id("imagem-pagina").evaluate("(img) => img.naturalWidth")
        assert largura > 0


def test_evidencia_de_cada_fato_abre_a_pagina_e_destaca_o_trecho(
    pagina_do_assessor: Page, browser: Browser
) -> None:
    """RNF-09: cada link de evidência destaca o trecho dentro da imagem PNG privada da página."""
    page = pagina_do_assessor
    page.goto(f"/processos/{variavel('LUPA_E2E_PROC_ID')}/validacoes")
    expect(page.get_by_test_id("achado").first).to_be_visible()
    links = page.get_by_test_id("link-evidencia").evaluate_all(
        "(els) => els.map((el) => [el.getAttribute('href'), el.textContent.trim()])"
    )
    unicos = dict(links)
    assert unicos
    for href, texto in unicos.items():
        page.goto(href)
        folha = texto.replace("fl. ", "")
        expect(page.get_by_test_id("pagina-atual")).to_have_text(re.compile(rf"^Página {folha}\b"))
        expect(page.get_by_test_id("trecho-evidencia")).not_to_be_empty()
        destaque = page.get_by_test_id("destaque-evidencia").first
        expect(destaque).to_be_visible()
        caixa = destaque.bounding_box()
        imagem = page.get_by_test_id("imagem-pagina").bounding_box()
        assert caixa and imagem
        assert caixa["x"] >= imagem["x"] - 1
        assert caixa["y"] >= imagem["y"] - 1
        assert caixa["x"] + caixa["width"] <= imagem["x"] + imagem["width"] + 1
    origem = page.get_by_test_id("imagem-pagina").get_attribute("src") or ""
    resposta = page.request.get(origem)
    assert resposta.headers["content-type"] == "image/png"
    assert resposta.headers["cache-control"].startswith("private")
    anonimo = browser.new_context(**ARGUMENTOS_DO_CONTEXTO)
    sem_sessao = anonimo.request.get(origem)
    assert "image/png" not in sem_sessao.headers.get("content-type", "")
    assert sem_sessao.url.endswith("/login")
    anonimo.close()
    _troca_de_pagina_e_zoom(page)


def _troca_de_pagina_e_zoom(page: Page) -> None:
    antes = page.get_by_test_id("pagina-atual").text_content() or ""
    encontrada = PAGINA.search(antes)
    assert encontrada, antes
    atual, total = encontrada.groups()
    page.get_by_test_id("moldura-pagina").focus()
    page.keyboard.press("ArrowLeft" if atual == total else "ArrowRight")
    expect(page.get_by_test_id("pagina-atual")).not_to_have_text(antes)
    page.keyboard.press("+")
    expect(page.get_by_test_id("zoom")).to_have_text("125%")


def test_correcao_preserva_o_fato_e_guarda_o_valor_anterior(pagina_do_assessor: Page) -> None:
    """RNF-09: a correção de uma data reexecuta as validações e mantém o histórico."""
    page = pagina_do_assessor
    page.goto(f"/processos/{variavel('LUPA_E2E_PROC_ID')}/validacoes")
    fato = (
        page.get_by_test_id("achado")
        .get_by_test_id("fato")
        .filter(has_text=re.compile(r"\d{2}/\d{2}/\d{4}"))
        .filter(has=page.locator("summary", has_text="Corrigir"))
        .first
    )
    expect(fato).to_be_visible()
    fato_id = fato.get_attribute("data-fato")
    fato.locator("summary", has_text="Corrigir").click()
    campo = fato.get_by_label("Valor corrigido")
    atual = campo.input_value()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", atual)
    ano = int(atual[:4]) - ANOS_RECUADOS
    campo.fill(f"{ano}{atual[4:]}")
    fato.get_by_role("button", name="Salvar correção").click()
    expect(
        page.get_by_text(re.compile(r"Fato corrigido\. Validações reexecutadas"))
    ).to_be_visible()
    expect(page.get_by_test_id("status-fato").filter(has_text="Corrigido").first).to_be_visible()
    anterior = page.get_by_test_id("historico-fatos").locator(f'[data-fato="{fato_id}"]').first
    expect(anterior).to_contain_text(atual[:4])
    vigente = page.get_by_test_id("achado").locator(f'[data-fato="{fato_id}"]').first
    expect(vigente).to_contain_text(str(ano))
    expect(page.get_by_test_id("historico-achados").locator("tbody tr").first).to_be_visible()
    _anotar(page)


def _anotar(page: Page) -> None:
    achado = page.get_by_test_id("achado").first
    nota = achado.locator("details.nota").last
    nota.locator("summary").click()
    nota.get_by_label("Anotação").fill("Conferir a certidão de intimação.")
    nota.get_by_role("button", name="Salvar anotação").click()
    expect(page.get_by_text("Anotação registrada.")).to_be_visible()
    expect(page.get_by_test_id("achado").first).to_contain_text("Conferir a certidão de intimação.")
