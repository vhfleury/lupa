"""Visualizador: página como imagem repassada da API e destaque da evidência (A6)."""

import re

import pytest
import respx
from django.test import Client

from lupa_web.telas import visualizador
from tests.telas.test_paridade import ARQUIVO, ARQUIVOS_LEGIVEIS, BASE, BBOX, EVIDENCIA

IMAGEM = f"{BASE}/arquivos/{ARQUIVO}/paginas/2/imagem"
PNG_SINTETICO = b"\x89PNG\r\n\x1a\nconteudo-sintetico"


def test_imagem_da_pagina_e_repassada_com_tipo_e_cache_da_api(
    api_simulada: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02 (A6): o PNG da API chega ao navegador com o tipo e o cache da API."""
    rota = api_simulada.get(IMAGEM).respond(
        200,
        content=PNG_SINTETICO,
        headers={"Content-Type": "image/png", "Cache-Control": "private, max-age=3600"},
    )

    resposta = navegador.get(IMAGEM)

    assert resposta.status_code == 200
    assert resposta.content == PNG_SINTETICO
    assert resposta["Content-Type"] == "image/png"
    assert resposta["Cache-Control"] == "private, max-age=3600"
    assert rota.calls.last.request.headers["Cookie"] == "lupa_sessao=sessao-sintetica"


@pytest.mark.parametrize("status", [404, 503])
def test_imagem_indisponivel_devolve_o_status_sem_o_corpo_da_api(
    api_simulada: respx.MockRouter, navegador: Client, status: int
) -> None:
    """RF-INT-02 (A6.2): status diferente de 200 volta igual, sem o corpo da API."""
    api_simulada.get(IMAGEM).respond(status, json={"detail": "página indisponível"})
    resposta = navegador.get(IMAGEM)
    assert resposta.status_code == status
    assert resposta.content == b""


def test_imagem_com_sessao_expirada_vai_ao_login(
    api_simulada: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-03 (A1.5): 401 da API na imagem redireciona ao login."""
    api_simulada.get(IMAGEM).respond(401, json={"detail": "não autenticado"})
    assert navegador.get(IMAGEM)["Location"] == "/login"


def test_sem_evidencia_abre_a_pagina_pedida_sem_destaque(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-DOS-05: `arquivo` e `pagina` abrem a página, sem retângulo nem trecho."""
    logado.get(f"{BASE}/arquivos").respond(200, json=ARQUIVOS_LEGIVEIS)
    html = navegador.get(
        f"{BASE}/visualizador", {"arquivo": ARQUIVO, "pagina": "3", "zoom": "150"}
    ).content.decode()
    assert f'src="{BASE}/arquivos/{ARQUIVO}/paginas/3/imagem"' in html
    assert "Página 3 de 3" in html
    assert "zoom-150" in html
    assert "<rect" not in html
    assert "Próxima →</span>" in html


def test_sem_parametros_abre_a_primeira_pagina_do_primeiro_arquivo_legivel(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-DOS-05: sem parâmetros, a página 1 do primeiro arquivo processado."""
    logado.get(f"{BASE}/arquivos").respond(200, json=ARQUIVOS_LEGIVEIS)
    html = navegador.get(f"{BASE}/visualizador").content.decode()
    assert f"/arquivos/{ARQUIVO}/paginas/1/imagem" in html
    assert "← Anterior</span>" in html


def test_sem_arquivo_processado_avisa(logado: respx.MockRouter, navegador: Client) -> None:
    """RF-DOS-05: sem arquivo legível, a tela avisa e não mostra imagem."""
    vazio = ARQUIVOS_LEGIVEIS | {"arquivos": []}
    logado.get(f"{BASE}/arquivos").respond(200, json=vazio)
    html = navegador.get(f"{BASE}/visualizador").content.decode()
    assert "Nenhum arquivo processado para visualizar." in html
    assert "<img" not in html


def test_evidencia_sem_coordenadas_mostra_o_trecho_sem_destaque(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-DOS-05: página sem coordenadas mostra o trecho e avisa que não há destaque."""
    logado.get(f"{BASE}/arquivos").respond(200, json=ARQUIVOS_LEGIVEIS)
    sem_caixas = BBOX | {"uniao": None, "retangulos": []}
    logado.get(f"{BASE}/evidencias/{EVIDENCIA}/bbox").respond(200, json=sem_caixas)
    html = navegador.get(f"{BASE}/visualizador", {"evidencia": EVIDENCIA}).content.decode()
    assert "o trecho não pôde ser destacado" in html
    assert "<rect" not in html


def test_evidencia_inexistente_mostra_a_mensagem_da_api(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-DOS-05 (A1.8): evidência que a API não encontra aparece como erro na tela."""
    logado.get(f"{BASE}/arquivos").respond(200, json=ARQUIVOS_LEGIVEIS)
    logado.get(f"{BASE}/evidencias/{EVIDENCIA}/bbox").respond(
        404, json={"detail": "evidência não encontrada"}
    )
    html = navegador.get(f"{BASE}/visualizador", {"evidencia": EVIDENCIA}).content.decode()
    assert "Evidência não encontrada." in html


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(None, 100), ("150", 150), ("999", 100), ("abc", 100), ("50", 50)],
)
def test_zoom_aceito_so_entre_os_passos(valor: str | None, esperado: int) -> None:
    """RF-DOS-05: o zoom fica nos passos de 25% entre 50% e 300%."""
    assert visualizador.zoom_pedido(valor) == esperado


@pytest.mark.parametrize(
    ("retangulo", "esperado"),
    [
        (
            {"x": 0.1, "y": 0.2, "largura": 0.5, "altura": 0.05},
            {"x": "0.1000", "y": "0.2000", "largura": "0.5000", "altura": "0.0500"},
        ),
        (
            {"x": -0.2, "y": 0.9, "largura": 1.5, "altura": 0.5},
            {"x": "0.0000", "y": "0.9000", "largura": "1.0000", "altura": "0.1000"},
        ),
    ],
)
def test_retangulo_do_destaque_nao_sai_da_pagina(
    retangulo: dict[str, float], esperado: dict[str, str]
) -> None:
    """RF-DOS-05: o retângulo é recortado à página, em fração com ponto decimal."""
    assert visualizador.retangulo_do_destaque(retangulo) == esperado


def test_atalhos_de_teclado_por_script_externo_sobre_os_links(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-DOS-05 (D8): `visualizador.js` externo liga setas e zoom aos links da barra."""
    logado.get(f"{BASE}/arquivos").respond(200, json=ARQUIVOS_LEGIVEIS)
    html = navegador.get(
        f"{BASE}/visualizador", {"arquivo": ARQUIVO, "pagina": "2", "zoom": "100"}
    ).content.decode()
    assert re.search(r'<script src="/static/js/visualizador\.[0-9a-f]+\.js" defer></script>', html)
    for atalho in ("anterior", "proxima", "menos-zoom", "mais-zoom"):
        assert f'data-atalho="{atalho}"' in html
    assert 'id="moldura"' in html
