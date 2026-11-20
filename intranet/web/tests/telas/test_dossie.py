"""Dossiê e validações: links das evidências, resumos, reclassificação e correção de fatos."""

import json

import respx
from django.test import Client

from tests.telas.test_paridade import (
    BASE,
    DOSSIE,
    EVIDENCIA,
    FATO,
    INDICE,
    OUTRA_EVIDENCIA,
    PECA,
    _simular_analise,
)


def test_evidencia_do_dossie_abre_a_pagina_do_arquivo(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-05: dado da capa, parte, evento e fonte do achado levam ao visualizador."""
    logado.get(f"{BASE}/dossie").respond(200, json=DOSSIE)
    logado.get(f"{BASE}/indice").respond(200, json=INDICE)

    html = navegador.get(f"{BASE}/dossie").content.decode()

    assert html.count(f'href="{BASE}/visualizador?evidencia={EVIDENCIA}"') == 3
    assert f'href="{BASE}/visualizador?evidencia={OUTRA_EVIDENCIA}"' in html


def test_resumos_das_pecas_sao_pedidos_a_api_e_rotulados_como_gerados(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-DOS-04: `?resumos=1` pede `resumos=true` à API e marca o texto como gerado."""
    peca = DOSSIE["pecas"][0] | {
        "resumo_peca": {"rotulo": "gerado", "texto": "Resumo sintético.", "citacoes": []}
    }
    rota = logado.get(f"{BASE}/dossie").respond(200, json=DOSSIE | {"pecas": [peca]})
    logado.get(f"{BASE}/indice").respond(200, json=INDICE)

    html = navegador.get(f"{BASE}/dossie", {"resumos": "1"}).content.decode()

    assert rota.calls.last.request.url.params["resumos"] == "true"
    assert "Resumo sintético." in html
    assert 'class="rotulo-gerado"' in html


def test_dossie_sem_indice_avisa(logado: respx.MockRouter, navegador: Client) -> None:
    """RF-DOS-01: sem índice de peças a tela avisa, sem erro."""
    logado.get(f"{BASE}/dossie").respond(200, json=DOSSIE)
    logado.get(f"{BASE}/indice").respond(200, json={"processo_id": "x", "pecas": []})
    assert "Índice ainda não disponível." in navegador.get(f"{BASE}/dossie").content.decode()


def test_dossie_de_processo_inexistente_mostra_nao_encontrado(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02: 404 da API no dossiê vira a página "não encontrado"."""
    logado.get(f"{BASE}/dossie").respond(404, json={"detail": "processo não encontrado"})
    assert navegador.get(f"{BASE}/dossie").status_code == 404


def test_reclassificacao_recusada_volta_ao_dossie_com_a_mensagem(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-PEC-02 (A1.8): a recusa da API aparece no dossiê com o mesmo status."""
    logado.get(f"{BASE}/dossie").respond(200, json=DOSSIE)
    logado.get(f"{BASE}/indice").respond(200, json=INDICE)
    logado.post(f"{BASE}/pecas/{PECA}/reclassificar").respond(
        422, json={"detail": "intervalo de páginas inválido"}
    )
    resposta = navegador.post(f"{BASE}/pecas/{PECA}/reclassificar", {"tipo": "sentenca"})
    assert resposta.status_code == 422
    assert "Intervalo de páginas inválido." in resposta.content.decode()


def test_aviso_da_reclassificacao_aparece_no_dossie(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-PEC-02: depois de reclassificar, o dossiê confirma a revisão."""
    logado.get(f"{BASE}/dossie").respond(200, json=DOSSIE)
    logado.get(f"{BASE}/indice").respond(200, json=INDICE)
    html = navegador.get(f"{BASE}/dossie", {"aviso": "reclassificada"}).content.decode()
    assert "Peça reclassificada." in html


def test_correcao_com_trecho_novo_exige_pagina_intervalo_e_trecho(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-FAT-03: trecho novo incompleto é recusado no front, sem chamar a API."""
    _simular_analise(logado)
    rota = logado.post(f"{BASE}/fatos/{FATO}/corrigir").respond(201, json={})
    resposta = navegador.post(
        f"{BASE}/fatos/{FATO}/corrigir",
        {"status": "corrigido", "valor": "x", "fonte": "", "pagina_id": "zz", "inicio": "3"},
    )
    assert resposta.status_code == 400
    assert "Informe a página, o intervalo e o trecho da correção." in resposta.content.decode()
    assert not rota.called


def test_correcao_com_trecho_novo_envia_a_fonte_informada(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-FAT-03: trecho novo completo vai à API com página, intervalo e trecho."""
    _simular_analise(logado)
    rota = logado.post(f"{BASE}/fatos/{FATO}/corrigir").respond(201, json={"achados_gravados": 2})
    pagina = "0f" * 32
    resposta = navegador.post(
        f"{BASE}/fatos/{FATO}/corrigir",
        {
            "status": "corrigido",
            "valor": "2026-02-12",
            "fonte": "",
            "pagina_id": pagina,
            "inicio": "0",
            "fim": "9",
            "trecho": "trecho sintético",
        },
    )
    assert resposta["Location"] == f"{BASE}/validacoes?aviso=corrigido&achados=2"
    assert json.loads(rota.calls.last.request.content) == {
        "status": "corrigido",
        "valor": "2026-02-12",
        "pagina_id": pagina,
        "inicio": 0,
        "fim": 9,
        "trecho": "trecho sintético",
    }


def test_aviso_da_correcao_informa_os_achados_novos(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-FAT-03: a tela confirma a correção e quantos achados foram regravados."""
    _simular_analise(logado)
    html = navegador.get(f"{BASE}/validacoes", {"aviso": "corrigido", "achados": "2"})
    assert "Validações reexecutadas: 2 achado(s) novo(s)" in html.content.decode()


def test_anotacao_vazia_nao_chama_a_api(logado: respx.MockRouter, navegador: Client) -> None:
    """RF-FAT-04: anotação em branco volta às validações sem gravar."""
    rota = logado.post(f"{BASE}/anotacoes").respond(201, json={})
    resposta = navegador.post(f"{BASE}/anotacoes", {"achado_id": "x", "texto": "  "})
    assert resposta["Location"] == f"{BASE}/validacoes"
    assert not rota.called
