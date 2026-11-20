"""Lista de processos renderizada no servidor a partir da API (RF-INT-01, RF-INT-02)."""

from typing import Any

import respx
from django.test import Client

PROCESSO_A = "a1" * 32
PROCESSO_B = "b2" * 32


def _processo(
    processo_id: str, numero: str, situacao: str, responsaveis: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "id": processo_id,
        "numero_cnj": numero,
        "classe": "apelacao_civel",
        "status": "criado",
        "em_revisao": False,
        "criador_id": "cd" * 32,
        "criado_em": "2026-03-04T15:30:00+00:00",
        "responsaveis": responsaveis,
        "ingestao": {"situacao": situacao, "por_estado": {}, "ultimo_envio": None},
    }


LISTA = [
    _processo(
        PROCESSO_A,
        "0000001-23.2026.8.07.0001",
        "concluido",
        [{"id": "11" * 32, "nome_usuario": "assessora.sintetica", "ativo": True}],
    ),
    _processo(PROCESSO_B, "0000002-45.2026.8.07.0001", "processando", []),
]


def test_lista_de_processos_vem_renderizada_da_api(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-01: o HTML traz os processos simulados, com uma chamada a `/processos` na API."""
    rota = logado.get("/processos").respond(200, json=LISTA)
    resposta = navegador.get("/processos")
    html = resposta.content.decode()
    assert resposta.status_code == 200
    assert rota.call_count == 1
    assert "0000001-23.2026.8.07.0001" in html
    assert f'href="/processos/{PROCESSO_A}"' in html
    assert "Apelação cível" in html
    assert "assessora.sintetica" in html
    assert "Sem responsável atribuído" in html
    assert "Concluído" in html
    assert "04/03/2026 12:30" in html
    assert "2 de 2" in html


def test_filtro_por_situacao_e_busca_restringe_a_lista(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02: os filtros do formulário GET restringem a lista no servidor."""
    logado.get("/processos").respond(200, json=LISTA)
    html = navegador.get("/processos", {"situacao": "processando"}).content.decode()
    assert "0000002-45.2026.8.07.0001" in html
    assert "0000001-23.2026.8.07.0001" not in html
    assert "1 de 2" in html
    html = navegador.get("/processos", {"busca": "ASSESSORA"}).content.decode()
    assert "0000001-23.2026.8.07.0001" in html
    assert "0000002-45.2026.8.07.0001" not in html


def test_filtro_por_responsavel(logado: respx.MockRouter, navegador: Client) -> None:
    """RF-INT-02: o filtro de responsável aceita um assessor ou "sem responsável"."""
    logado.get("/processos").respond(200, json=LISTA)
    html = navegador.get("/processos", {"responsavel": "sem"}).content.decode()
    assert "0000002-45.2026.8.07.0001" in html
    assert "0000001-23.2026.8.07.0001" not in html
    html = navegador.get("/processos", {"responsavel": "11" * 32}).content.decode()
    assert "0000001-23.2026.8.07.0001" in html
    assert "0000002-45.2026.8.07.0001" not in html


def test_filtro_sem_resultado_oferece_limpar(logado: respx.MockRouter, navegador: Client) -> None:
    """RF-INT-02: filtro sem resultado diz que nada foi encontrado e oferece limpar."""
    logado.get("/processos").respond(200, json=LISTA)
    html = navegador.get("/processos", {"busca": "inexistente"}).content.decode()
    assert "Nenhum processo encontrado." in html
    assert 'href="/processos"' in html


def test_lista_vazia_avisa_que_nao_ha_processos(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02: sem processos, a tela diz que nenhum foi cadastrado."""
    logado.get("/processos").respond(200, json=[])
    assert "Nenhum processo cadastrado." in navegador.get("/processos").content.decode()


def test_lista_atualiza_sozinha_enquanto_ha_processamento(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02: com processo em processamento, a lista se atualiza a cada 4 s pelo HTMX."""
    logado.get("/processos").respond(200, json=LISTA)
    html = navegador.get("/processos", {"situacao": "processando"}).content.decode()
    assert 'hx-trigger="every 4s"' in html
    assert 'hx-get="/processos?situacao=processando"' in html
    fragmento = navegador.get("/processos", HTTP_HX_REQUEST="true").content.decode()
    assert "<html" not in fragmento
    assert "0000001-23.2026.8.07.0001" in fragmento


def test_lista_sem_processamento_nao_se_atualiza(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02: sem processamento em curso, nenhum `hx-trigger` periódico."""
    logado.get("/processos").respond(200, json=LISTA[:1])
    assert "hx-trigger" not in navegador.get("/processos").content.decode()


def test_cadastro_de_processo_aparece_para_quem_pode_subir(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-04 (A4.1): o assessor vê o cadastro por arquivo com `hx-post` multipart."""
    logado.get("/processos").respond(200, json=[])
    html = navegador.get("/processos").content.decode()
    assert 'hx-post="/processos/envio"' in html
    assert 'hx-encoding="multipart/form-data"' in html


def test_novo_processo_abre_e_fecha_o_cadastro_sem_javascript(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-04 (D17): "+ Novo processo" é o `<summary>` e o formulário fica no `<details>`."""
    logado.get("/processos").respond(200, json=LISTA)
    html = navegador.get("/processos").content.decode()
    inicio = html.index('<details id="cadastro-processo"')
    fim = html.index("</details>", inicio)
    cadastro = html[inicio:fim]
    assert '<summary class="novo-botao"><span class="abrir">+ Novo processo</span>' in cadastro
    assert "Fechar cadastro" in cadastro
    assert 'hx-post="/processos/envio"' in cadastro
    assert 'href="#cadastro-processo"' not in html
