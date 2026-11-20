"""Página `/padrao`: catálogo de componentes só no desenvolvimento (RF-VIS-03, 04, 05; A1)."""

import re

import pytest
import respx
from django.test import Client

COMPONENTES = (
    "botao",
    "aviso",
    "tabela",
    "campo",
    "acao",
    "paginacao",
    "vazio",
    "badge",
    "cartao",
    "progresso",
    "selo",
)


@pytest.fixture
def desenvolvimento(monkeypatch: pytest.MonkeyPatch) -> None:
    """`LUPA_AMBIENTE=desenvolvimento` no processo do front."""
    monkeypatch.setenv("LUPA_AMBIENTE", "desenvolvimento")


@pytest.mark.parametrize("ambiente", ["producao", "teste", ""])
def test_padrao_devolve_404_fora_do_desenvolvimento(
    ambiente: str,
    api_simulada: respx.MockRouter,
    navegador: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RF-VIS-05 (D8): fora do desenvolvimento `/padrao` é 404, sem chamar a API."""
    monkeypatch.setenv("LUPA_AMBIENTE", ambiente)
    resposta = navegador.get("/padrao")
    assert resposta.status_code == 404
    assert api_simulada.calls.call_count == 0


def test_padrao_sem_ambiente_devolve_404(
    api_simulada: respx.MockRouter, navegador: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RF-VIS-05 (D8): sem `LUPA_AMBIENTE` a página não existe."""
    monkeypatch.delenv("LUPA_AMBIENTE", raising=False)
    assert navegador.get("/padrao").status_code == 404
    assert api_simulada.calls.call_count == 0


@pytest.mark.usefixtures("desenvolvimento")
def test_padrao_sem_sessao_vai_ao_login(api_simulada: respx.MockRouter, navegador: Client) -> None:
    """RF-VIS-05 (D8): no desenvolvimento a página exige sessão, como as demais telas."""
    api_simulada.get("/auth/sessao").respond(401)
    resposta = navegador.get("/padrao")
    assert resposta.status_code == 303
    assert resposta["Location"] == "/login?motivo=expirada"


@pytest.mark.usefixtures("desenvolvimento")
def test_padrao_mostra_cada_componente_em_desenvolvimento(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-VIS-05: com sessão, a página mostra os 11 componentes do catálogo de RF-VIS-04."""
    resposta = navegador.get("/padrao")
    html = resposta.content.decode()
    assert resposta.status_code == 200
    assert "<h1>Padrão visual</h1>" in html
    presentes = set(re.findall(r'data-componente="([a-z]+)"', html))
    assert presentes == set(COMPONENTES)
    assert [chamada.request.url.path for chamada in logado.calls] == ["/auth/sessao"]


@pytest.mark.usefixtures("desenvolvimento")
def test_selo_traz_o_texto_do_resultado_em_cada_tom(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-VIS-03 (D7): cada tom do selo aparece com o texto do resultado, não só a cor."""
    html = navegador.get("/padrao").content.decode()
    for tom, texto in (("sucesso", "Tempestiva"), ("atencao", "Verificar"), ("falha", "Deserta")):
        assert re.search(rf'class="selo selo-{tom}"[^>]*>\s*{texto}', html), tom


@pytest.mark.usefixtures("desenvolvimento")
def test_badge_e_pilula_neutra_distinta_do_selo(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-VIS-04 (D7): o badge de estado de fluxo usa só a classe neutra, nunca a do selo."""
    html = navegador.get("/padrao").content.decode()
    badges = re.findall(r'<span class="([^"]*)" data-componente="badge"', html)
    assert badges
    assert {classes for classes in badges} == {"badge"}
