"""Chat por processo com HTMX: resposta rotulada, citações, sem evidência, teto e revisão (A5)."""

import json
import logging
from typing import Any

import httpx
import pytest
import respx
from django.test import Client

from lupa_web.telas import chat
from tests.telas.conftest import sessao_da_api
from tests.telas.test_paridade import (
    ARQUIVO,
    BASE,
    CHAT,
    CONVERSA,
    MENSAGEM_AGENTE,
    PAGINA,
    REVISAO,
    _simular_chat,
)

PERGUNTA = "Em que página está a certidão sintética de intimação?"
HTMX = {"HX-Request": "true"}


def _resposta(**campos: Any) -> dict[str, Any]:
    return (
        MENSAGEM_AGENTE
        | {
            "conversa_id": CONVERSA["conversa_id"],
            "conversa_encerrada": False,
            "citacoes_descartadas_na_conversa": 0,
            "processo_em_revisao": False,
        }
        | campos
    )


def _perguntar(api: respx.MockRouter, navegador: Client, resposta: dict[str, Any]) -> str:
    api.post(f"{BASE}/chat").respond(200, json=resposta)
    enviado = navegador.post(f"{BASE}/chat", {"pergunta": PERGUNTA}, headers=HTMX)
    assert enviado.status_code == 200
    return enviado.content.decode()


def test_resposta_conferida_aparece_em_bloco_rotulado_com_link_da_pagina(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-05 (A5.5): pergunta e resposta rotulada como IA, com link da página citada."""
    html = _perguntar(logado, navegador, _resposta())

    assert PERGUNTA in html
    assert chat.AVISO_IA in html
    assert 'data-status="respondida"' in html
    assert f'href="{BASE}/visualizador?arquivo={ARQUIVO}&amp;pagina=2"' in html
    assert "Página 2: “certidão sintética de intimação”" in html
    assert 'id="formulario-pergunta" hx-swap-oob="true"' in html


def test_resposta_sem_citacao_conferida_mostra_sem_evidencia(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-05 (A5.4): sem citação conferida, a resposta aparece como "sem evidência"."""
    resposta = _resposta(status="sem_evidencia", citacoes=[], texto="Não localizei nos autos.")
    html = _perguntar(logado, navegador, resposta)

    assert "Sem evidência: resposta não conferida nos autos." in html
    assert 'data-status="sem_evidencia"' in html
    assert "/visualizador?" not in html


def test_aviso_de_teto_aparece_sem_bloco_de_ia(logado: respx.MockRouter, navegador: Client) -> None:
    """RF-INT-05 (A5.3): o teto aparece como aviso, sem o bloco gerado por IA, e trava o campo."""
    resposta = _resposta(
        status="teto",
        citacoes=[],
        texto="Limite de uso da conversa atingido.",
        rotulo=None,
        conversa_encerrada=True,
    )
    html = _perguntar(logado, navegador, resposta)

    assert "Limite de uso da conversa atingido." in html
    assert chat.AVISO_IA not in html
    assert 'data-status="teto"' in html
    assert "disabled" in html


def test_processo_em_revisao_responde_aviso_sem_bloco_de_ia(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-05 (A5.3): a recusa por revisão aparece como aviso, sem bloco de IA."""
    resposta = _resposta(
        status="recusa",
        citacoes=[],
        texto="Este processo está em revisão.",
        processo_em_revisao=True,
    )
    html = _perguntar(logado, navegador, resposta)

    assert "Este processo está em revisão." in html
    assert chat.AVISO_IA not in html


def test_pergunta_vai_a_api_com_prazo_longo_e_nao_entra_no_log(
    logado: respx.MockRouter, navegador: Client, caplog: pytest.LogCaptureFixture
) -> None:
    """RF-INT-05 (D13): a pergunta usa o prazo do chat e o texto dela não aparece no log."""
    caplog.set_level(logging.DEBUG)
    rota = logado.post(f"{BASE}/chat").respond(200, json=_resposta())

    navegador.post(f"{BASE}/chat", {"pergunta": f"  {PERGUNTA}  "}, headers=HTMX)

    pedido = rota.calls.last.request
    assert pedido.extensions["timeout"]["read"] == 180
    assert json.loads(pedido.content) == {"pergunta": PERGUNTA}
    assert PERGUNTA not in caplog.text


def test_recusa_da_api_aparece_no_fragmento(logado: respx.MockRouter, navegador: Client) -> None:
    """RF-INT-05 (A1.8): erro da API vira aviso no fim da conversa, com status 200 do HTMX."""
    logado.post(f"{BASE}/chat").respond(422, json={"detail": "a pergunta deve ter de 1 a 2000"})
    resposta = navegador.post(f"{BASE}/chat", {"pergunta": PERGUNTA}, headers=HTMX)
    assert resposta.status_code == 200
    assert "A pergunta deve ter de 1 a 2000." in resposta.content.decode()


def test_api_sem_resposta_no_prazo_aparece_no_fragmento(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-05 (A1.3): prazo esgotado vira aviso de serviço indisponível no fragmento."""
    logado.post(f"{BASE}/chat").mock(side_effect=httpx.ReadTimeout("prazo"))
    resposta = navegador.post(f"{BASE}/chat", {"pergunta": PERGUNTA}, headers=HTMX)
    assert resposta.status_code == 200
    assert "não conseguiu falar com o serviço" in resposta.content.decode()


def test_pergunta_em_branco_nao_chama_a_api(logado: respx.MockRouter, navegador: Client) -> None:
    """RF-INT-05: pergunta em branco não é enviada."""
    rota = logado.post(f"{BASE}/chat").respond(200, json=_resposta())
    resposta = navegador.post(f"{BASE}/chat", {"pergunta": "   "}, headers=HTMX)
    assert resposta.status_code == 200
    assert not rota.called


def test_historico_separa_a_conversa_atual_das_anteriores(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-05: a última conversa aberta é a atual; as encerradas ficam no histórico."""
    _simular_chat(logado)
    html = navegador.get(f"{BASE}/chat").content.decode()
    atual, anteriores = html.split('id="titulo-historico"')
    assert "certidão sintética de intimação" in atual
    assert "1 citação descartada nesta conversa" in atual
    assert "encerrada: limite de uso da conversa atingido" in anteriores
    assert "Pergunta anterior sintética" in anteriores


def test_conversa_encerrada_pelo_teto_trava_a_pergunta(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-05: com a última conversa encerrada pelo teto do processo, o campo fica travado."""
    _simular_chat(logado)
    encerrada = CONVERSA | {"encerrada": True, "motivo_encerramento": "teto_processo"}
    logado.get(f"{BASE}/chat").respond(200, json=CHAT | {"conversas": [encerrada]})
    html = navegador.get(f"{BASE}/chat").content.decode()
    assert "Limite de uso do processo atingido." in html
    assert "<textarea" in html and "disabled" in html


def test_processo_em_revisao_mostra_aviso_e_liberacao_ao_desembargador(
    api_simulada: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-05: em revisão, o chat avisa o motivo e o desembargador vê a liberação."""
    api_simulada.get("/auth/sessao").respond(200, json=sessao_da_api("desembargador"))
    _simular_chat(api_simulada)
    em_revisao = REVISAO | {"em_revisao": True, "motivo": "outro_processo"}
    api_simulada.get(f"{BASE}/revisao").respond(200, json=em_revisao)
    html = navegador.get(f"{BASE}/chat").content.decode()
    assert "a resposta citava identificador de outro processo" in html
    assert f'href="{BASE}/chat/liberar"' in html
    assert "disabled" in html


def test_assessor_nao_ve_a_liberacao(logado: respx.MockRouter, navegador: Client) -> None:
    """RF-INT-05: o assessor vê o aviso da revisão, sem a liberação."""
    _simular_chat(logado)
    logado.get(f"{BASE}/revisao").respond(200, json=REVISAO | {"em_revisao": True})
    html = navegador.get(f"{BASE}/chat").content.decode()
    assert "Processo em revisão." in html
    assert "/chat/liberar" not in html


def test_liberacao_recusada_volta_ao_chat_com_a_mensagem(
    api_simulada: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-05 (A1.8): recusa da liberação aparece no chat com o mesmo status."""
    api_simulada.get("/auth/sessao").respond(200, json=sessao_da_api("desembargador"))
    _simular_chat(api_simulada)
    api_simulada.post(f"{BASE}/liberar-revisao").respond(
        409, json={"detail": "processo não está em revisão"}
    )
    resposta = navegador.post(f"{BASE}/chat/liberar")
    assert resposta.status_code == 409
    assert "Processo não está em revisão." in resposta.content.decode()


def test_aviso_da_liberacao_aparece_no_chat(logado: respx.MockRouter, navegador: Client) -> None:
    """RF-INT-05: depois de liberar, o chat confirma a volta do assistente."""
    _simular_chat(logado)
    html = navegador.get(f"{BASE}/chat", {"aviso": "liberado"}).content.decode()
    assert "Processo liberado." in html


def test_citacao_sem_pagina_aparece_sem_link() -> None:
    """RF-INT-05: citação sem número de página mostra o trecho sem link."""
    citacao = {"pagina_id": PAGINA, "trecho": "x", "pagina_numero": None, "arquivo_id": None}
    assert chat.link_da_citacao("p", citacao) == ""


def test_citacao_sem_arquivo_usa_so_a_pagina() -> None:
    """RF-INT-05: sem arquivo conhecido, o link leva só a página."""
    citacao = {"pagina_id": PAGINA, "trecho": "x", "pagina_numero": 3, "arquivo_id": None}
    assert chat.link_da_citacao("p", citacao) == "/processos/p/visualizador?pagina=3"
