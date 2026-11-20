"""Painel "Início" na raiz, com indicadores e atalhos vindos da API (RF-INT-02, D17)."""

from typing import Any

import respx
from django.test import Client

from tests.telas.conftest import sessao_da_api


def _processo(indice: int, situacao: str, criado_em: str) -> dict[str, Any]:
    return {
        "id": f"{indice:064x}",
        "numero_cnj": f"000000{indice}-00.2026.8.07.0001",
        "classe": "apelacao_civel",
        "status": "criado",
        "em_revisao": False,
        "criador_id": "cd" * 32,
        "criado_em": criado_em,
        "responsaveis": [],
        "ingestao": {"situacao": situacao, "por_estado": {}, "ultimo_envio": None},
    }


LISTA = [
    _processo(1, "concluido", "2026-03-01T10:00:00+00:00"),
    _processo(2, "processando", "2026-03-03T10:00:00+00:00"),
    _processo(3, "quarentena", "2026-03-02T10:00:00+00:00"),
]
USUARIOS = [
    {"id": "11" * 32, "nome_usuario": "assessora.sintetica", "papel": "assessor", "ativo": True},
    {"id": "22" * 32, "nome_usuario": "outra.sintetica", "papel": "assessor", "ativo": False},
    {"id": "ab" * 32, "nome_usuario": "des.sintetico", "papel": "desembargador", "ativo": True},
]


def test_painel_do_assessor_mostra_os_proprios_processos_e_indicadores(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02 (D17): o assessor vê `GET /processos?meus=true` resumido em indicadores."""
    rota = logado.get("/processos", params={"meus": "true"}).respond(200, json=LISTA)
    resposta = navegador.get("/")
    html = resposta.content.decode()
    assert resposta.status_code == 200
    assert rota.called
    assert "Minha área de trabalho" in html
    assert "Sob minha responsabilidade" in html
    assert [int(n) for n in _indicadores(html)] == [3, 1, 1, 1]
    assert html.index("0000002-00") < html.index("0000003-00") < html.index("0000001-00")
    assert 'class="situacao pendente"' in html
    assert "Para enviar documentos" in html
    assert 'href="/usuarios"' not in html.split('class="painel"')[1]


def test_painel_do_desembargador_mostra_gabinete_e_equipe(
    api_simulada: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02 (D17): o desembargador vê todos os processos, a equipe e os atalhos de gestão."""
    api_simulada.get("/auth/sessao").respond(200, json=sessao_da_api("desembargador"))
    rota = api_simulada.get("/processos").respond(200, json=LISTA)
    api_simulada.get("/usuarios").respond(200, json=USUARIOS)
    html = navegador.get("/").content.decode()
    assert "meus" not in str(rota.calls.last.request.url)
    assert "Visão geral do gabinete" in html
    assert "Equipe do gabinete" in html
    assert "outra.sintetica" in html and "Desativado" in html
    assert "des.sintetico" not in html.split('id="equipe-titulo"')[1]
    assert 'href="/auditoria"' in html


def test_painel_com_falha_da_api_mostra_indicadores_indisponiveis(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02 (D17): sem a lista, o painel avisa e mostra "—" nos indicadores."""
    logado.get("/processos").respond(500, json={"detail": "falha sintética"})
    html = navegador.get("/").content.decode()
    assert "Processos: Falha sintética." in html
    assert _indicadores(html) == ["—"] * 4
    assert "Não foi possível carregar os processos." in html


def test_menu_tem_inicio_marcado_so_na_raiz(logado: respx.MockRouter, navegador: Client) -> None:
    """RF-INT-02 (D17): o menu lateral começa por "Início", corrente só em `/`."""
    logado.get("/processos").respond(200, json=[])
    raiz = navegador.get("/").content.decode()
    lista = navegador.get("/processos").content.decode()
    assert '<a href="/" aria-current="page">Início</a>' in raiz
    assert '<a href="/">Início</a>' in lista


def _indicadores(html: str) -> list[str]:
    trechos = html.split('<article class="indicador')[1:]
    return [t.split("<strong>")[1].split("</strong>")[0] for t in trechos]
