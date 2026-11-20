"""Auditoria: filtros, paginação, verificação, relatório de uso e exportação (RF-INT-02)."""

import pytest
import respx
from django.test import Client

from lupa_web.telas import auditoria
from tests.telas.conftest import sessao_da_api
from tests.telas.test_paridade import EVENTOS, PROCESSO, RELATORIO, VERIFICACAO


@pytest.fixture
def desembargador(api_simulada: respx.MockRouter) -> respx.MockRouter:
    """API que reconhece a sessão do desembargador."""
    api_simulada.get("/auth/sessao").respond(200, json=sessao_da_api("desembargador"))
    return api_simulada


def test_filtros_vao_a_api_com_o_intervalo_em_utc(
    desembargador: respx.MockRouter, navegador: Client
) -> None:
    """RF-AUD-02: filtros preenchidos vão à API; o horário de Brasília vira instante UTC."""
    rota = desembargador.get("/auditoria").respond(200, json=EVENTOS)
    navegador.get(
        "/auditoria",
        {
            "usuario_id": "",
            "processo_id": PROCESSO,
            "acao": "processo_aberto",
            "inicio": "2026-03-04T09:00",
            "fim": "2026-03-04T18:00",
            "ip": " 10.0.0.7 ",
            "cursor": "c1",
        },
    )
    parametros = dict(rota.calls.last.request.url.params)
    assert parametros == {
        "processo_id": PROCESSO,
        "acao": "processo_aberto",
        "inicio": "2026-03-04T12:00:00+00:00",
        "fim": "2026-03-04T21:00:00+00:00",
        "ip": "10.0.0.7",
        "limite": "50",
        "cursor": "c1",
    }


@pytest.mark.parametrize(
    ("campos", "mensagem"),
    [
        ({"usuario_id": "xyz"}, "O identificador de usuário não é válido."),
        ({"processo_id": "xyz"}, "O identificador de processo não é válido."),
        (
            {"inicio": "2026-03-05T10:00", "fim": "2026-03-04T10:00"},
            "O início do intervalo deve ser anterior ao fim.",
        ),
        ({"inicio": "ontem"}, "Informe data e hora válidas."),
    ],
)
def test_filtro_invalido_e_recusado_sem_chamar_a_api(
    desembargador: respx.MockRouter, navegador: Client, campos: dict[str, str], mensagem: str
) -> None:
    """RF-AUD-02: identificador ou intervalo inválido mostra o motivo sem consultar."""
    rota = desembargador.get("/auditoria").respond(200, json=EVENTOS)
    html = navegador.get("/auditoria", campos).content.decode()
    assert mensagem in html
    assert not rota.called


def test_evento_sem_usuario_nem_processo_mostra_traco(
    desembargador: respx.MockRouter, navegador: Client
) -> None:
    """RF-AUD-02: evento sem usuário nem processo não oferece relatório."""
    evento = EVENTOS["eventos"][0] | {"usuario_id": None, "processo_id": None}
    desembargador.get("/auditoria").respond(200, json={"eventos": [evento], "proximo_cursor": None})
    html = navegador.get("/auditoria").content.decode()
    assert "relatorio_tipo=" not in html
    assert "Próxima página" not in html


def test_cadeia_quebrada_mostra_a_sequencia(
    desembargador: respx.MockRouter, navegador: Client
) -> None:
    """RF-AUD-03: a verificação aponta a primeira sequência quebrada e o motivo."""
    desembargador.get("/auditoria").respond(200, json=EVENTOS)
    quebrada = VERIFICACAO | {"integra": False, "primeira_sequencia_quebrada": 7, "motivo": "hash"}
    desembargador.get("/auditoria/verificar").respond(200, json=quebrada)
    html = navegador.get("/auditoria", {"verificar": "1"}).content.decode()
    assert "Cadeia QUEBRADA a partir da sequência 7 (hash)." in html


def test_relatorio_sem_identificador_avisa(
    desembargador: respx.MockRouter, navegador: Client
) -> None:
    """RF-AUD-04: relatório sem identificador pede o identificador, sem chamar a API."""
    desembargador.get("/auditoria").respond(200, json=EVENTOS)
    rota = desembargador.get("/auditoria/relatorio-uso").respond(200, json=RELATORIO)
    html = navegador.get("/auditoria", {"relatorio_tipo": "usuario", "relatorio_id": ""})
    assert "Informe o identificador." in html.content.decode()
    assert not rota.called


def test_relatorio_recusado_mostra_a_mensagem_da_api(
    desembargador: respx.MockRouter, navegador: Client
) -> None:
    """RF-AUD-04 (A1.8): recusa da API no relatório aparece na seção do relatório."""
    desembargador.get("/auditoria").respond(200, json=EVENTOS)
    desembargador.get("/auditoria/relatorio-uso").respond(
        422, json={"detail": "informe um processo ou um usuário"}
    )
    html = navegador.get("/auditoria", {"relatorio_tipo": "processo", "relatorio_id": PROCESSO})
    assert "Informe um processo ou um usuário." in html.content.decode()


def test_consulta_recusada_mostra_a_mensagem_da_api(
    desembargador: respx.MockRouter, navegador: Client
) -> None:
    """RF-AUD-02 (A1.8): cursor inválido recusado pela API aparece como erro da consulta."""
    desembargador.get("/auditoria").respond(422, json={"detail": "cursor inválido"})
    html = navegador.get("/auditoria", {"cursor": "x"}).content.decode()
    assert "Cursor inválido." in html


def test_relatorio_com_custos_por_modelo(
    desembargador: respx.MockRouter, navegador: Client
) -> None:
    """RF-AUD-04: o custo de cada modelo da tabela aparece em reais."""
    desembargador.get("/auditoria").respond(200, json=EVENTOS)
    custo = RELATORIO["custo_estimado"] | {
        "por_modelo": [
            {"modelo": "m", "tokens_entrada": 1, "tokens_saida": 2, "custo": "1234.5"},
        ]
    }
    desembargador.get("/auditoria/relatorio-uso").respond(
        200, json=RELATORIO | {"custo_estimado": custo, "contagem_por_acao": {}}
    )
    html = navegador.get("/auditoria", {"relatorio_tipo": "usuario", "relatorio_id": PROCESSO})
    texto = html.content.decode()
    assert "R$ 1.234,50" in texto
    assert "Sem eventos." in texto


def test_exportacao_recusada_devolve_o_status(
    desembargador: respx.MockRouter, navegador: Client
) -> None:
    """RF-AUD-05: recusa da API na exportação volta com o status e a mensagem."""
    desembargador.get("/auditoria/exportar").respond(422, json={"detail": "filtro inválido"})
    resposta = navegador.get("/auditoria/exportar", {"formato": "xml"})
    assert resposta.status_code == 422
    assert resposta.content.decode() == "Filtro inválido."


@pytest.mark.parametrize(
    ("valor", "moeda", "esperado"),
    [
        ("0.1234", "BRL", "R$ 0,1234"),
        ("1234.5", "BRL", "R$ 1.234,50"),
        ("2", "USD", "US$ 2,00"),
        ("2", "EUR", "EUR 2,00"),
    ],
)
def test_dinheiro_com_duas_a_quatro_casas(valor: str, moeda: str, esperado: str) -> None:
    """RF-AUD-04: custo com duas a quatro casas decimais e o símbolo da moeda."""
    assert auditoria.formatar_dinheiro(valor, moeda) == esperado
