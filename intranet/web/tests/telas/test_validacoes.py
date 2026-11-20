"""Validações: valores do achado com links, fonte e valor da correção e desvios da API."""

from typing import Any

import pytest
import respx
from django.http import QueryDict
from django.test import Client

from lupa_web import rotulos
from lupa_web.telas import dossie, validacoes
from tests.telas.test_paridade import (
    ACHADO_VIGENTE,
    BASE,
    EVIDENCIA,
    EVIDENCIA_DO_FATO,
    FATO,
    FATO_VIGENTE,
    PAGINA,
    PROCESSO,
    _simular_analise,
)

INDICES = validacoes.Indices(PROCESSO, [FATO_VIGENTE])
LINK = f"/processos/{PROCESSO}/visualizador?evidencia={EVIDENCIA}"


@pytest.mark.parametrize(
    ("chave", "valor", "esperado"),
    [
        ("intimacao", "2026-02-10", {"tipo": "link", "texto": "10/02/2026", "link": LINK}),
        ("sentenca", "2026-02-10", {"tipo": "texto", "texto": "10/02/2026"}),
        ("x", FATO, {"tipo": "link", "texto": "Intimacao", "link": LINK}),
        ("x", PAGINA, {"tipo": "link", "texto": "Folha 2", "link": LINK}),
        ("x", "0" * 64, {"tipo": "abreviado", "texto": "00000000…", "titulo": "0" * 64}),
        ("x", True, {"tipo": "texto", "texto": "Sim"}),
        ("x", [15], {"tipo": "lista", "itens": [{"tipo": "texto", "texto": "15"}]}),
        (
            "x",
            {"prazo_dias": 15},
            {"tipo": "mapa", "campos": [("Prazo em dias úteis", {"tipo": "texto", "texto": "15"})]},
        ),
    ],
)
def test_valor_do_achado_liga_datas_e_identificadores_a_evidencia(
    chave: str, valor: object, esperado: dict[str, Any]
) -> None:
    """RF-INT-05: data do marco, fato e página citados abrem a evidência no visualizador."""
    assert validacoes.no_do_valor(INDICES, ACHADO_VIGENTE, chave, valor) == esperado


def test_data_do_comprovante_procura_o_fato_do_preparo() -> None:
    """RF-INT-05: `data_comprovante` liga ao fato `comprovante_preparo` com a mesma data."""
    preparo = FATO_VIGENTE | {"id": "fa" * 32, "tipo": "comprovante_preparo"}
    indices = validacoes.Indices(PROCESSO, [preparo])
    achado = ACHADO_VIGENTE | {"fatos_usados": [preparo["id"]]}
    assert indices.fato_da_data(achado, "data_comprovante", "2026-02-10") == preparo


def test_fato_sem_evidencia_nao_tem_link() -> None:
    """RF-INT-05: fato sem evidência aparece sem link."""
    assert INDICES.link_do_fato(FATO_VIGENTE | {"evidencias": []}) == ""


@pytest.mark.parametrize(
    ("original", "texto", "esperado"),
    [
        ("2026-02-10", " 2026-02-11 ", "2026-02-11"),
        (15, "20", 20),
        ({"a": 1}, '{"a": 2}', {"a": 2}),
        (15, " vinte ", "vinte"),
    ],
)
def test_valor_corrigido_segue_o_tipo_do_original(
    original: object, texto: str, esperado: object
) -> None:
    """RF-FAT-03: valor textual sai sem espaços; os demais são lidos como JSON."""
    assert validacoes.valor_corrigido(original, texto) == esperado


@pytest.mark.parametrize(
    "campos",
    [
        "fonte=&pagina_id=" + "a" * 64 + "&inicio=x&fim=2&trecho=t",
        "fonte=&pagina_id=" + "a" * 64 + "&inicio=-1&fim=2&trecho=t",
        "fonte=&pagina_id=" + "a" * 64 + "&inicio=2&fim=2&trecho=t",
        "fonte=&pagina_id=" + "a" * 64 + "&inicio=0&fim=2&trecho=+",
    ],
)
def test_trecho_novo_invalido_nao_vira_fonte(campos: str) -> None:
    """RF-FAT-03: intervalo inválido ou trecho vazio não vai à API."""
    assert validacoes.fonte_da_correcao(FATO_VIGENTE, QueryDict(campos)) is None


def test_evidencia_escolhida_vira_a_fonte_da_correcao() -> None:
    """RF-FAT-03: a evidência escolhida leva página, intervalo e trecho dela."""
    fonte = validacoes.fonte_da_correcao(FATO_VIGENTE, QueryDict(f"fonte={EVIDENCIA}"))
    assert fonte == {k: EVIDENCIA_DO_FATO[k] for k in ("pagina_id", "inicio", "fim", "trecho")}


@pytest.mark.parametrize(
    ("tipo", "valor", "esperado"),
    [
        ("valor_causa", "1500.50", "R$ 1.500,50"),
        ("valor_causa", "mil reais", "mil reais"),
        ("data_distribuicao", "2026-01-05", "05/01/2026"),
        ("comarca", "Sintética", "Sintética"),
    ],
)
def test_dado_da_capa_formatado(tipo: str, valor: str, esperado: str) -> None:
    """RF-DOS-01: valor da causa em reais e data de distribuição no formato brasileiro."""
    assert dossie.texto_do_dado(tipo, valor) == esperado


def test_percentual_arredonda() -> None:
    """RF-DOS-01: a confiança aparece como percentual inteiro."""
    assert rotulos.percentual(0.925) == "92%"


def test_validacoes_de_processo_inexistente_mostra_nao_encontrado(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02: 404 da API nas validações vira a página "não encontrado"."""
    logado.get(f"{BASE}/achados").respond(404, json={"detail": "processo não encontrado"})
    assert navegador.get(f"{BASE}/validacoes").status_code == 404


def test_validacoes_sem_achados_avisa(logado: respx.MockRouter, navegador: Client) -> None:
    """RF-INT-02: sem achados nem histórico, a tela explica quando eles aparecem."""
    _simular_analise(logado)
    for rota in ("achados", "achados/historico"):
        logado.get(f"{BASE}/{rota}").respond(200, json={"achados": []})
    logado.get(f"{BASE}/fatos/historico").respond(200, json={"fatos": []})
    html = navegador.get(f"{BASE}/validacoes").content.decode()
    assert "Nenhum achado ainda." in html
    assert "Sem versões anteriores." in html


def test_correcao_de_fato_inexistente_e_recusada_sem_chamar_a_api(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-FAT-03: fato que não está entre os vigentes não é corrigido."""
    _simular_analise(logado)
    rota = logado.post(f"{BASE}/fatos/{'00' * 32}/corrigir").respond(201, json={})
    resposta = navegador.post(
        f"{BASE}/fatos/{'00' * 32}/corrigir", {"status": "corrigido", "fonte": EVIDENCIA}
    )
    assert resposta.status_code == 400
    assert not rota.called


def test_recusa_da_api_na_confirmacao_volta_com_a_mensagem(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-FAT-03 (A1.8): a recusa da API aparece nas validações com o mesmo status."""
    _simular_analise(logado)
    logado.post(f"{BASE}/fatos/{FATO}/corrigir").respond(
        409, json={"detail": "processo em revisão"}
    )
    resposta = navegador.post(f"{BASE}/fatos/{FATO}/corrigir", {"status": "confirmado"})
    assert resposta.status_code == 409
    assert "Processo em revisão." in resposta.content.decode()


def test_recusa_da_api_na_anotacao_volta_com_a_mensagem(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-FAT-04 (A1.8): a recusa da API na anotação aparece nas validações."""
    _simular_analise(logado)
    logado.post(f"{BASE}/anotacoes").respond(404, json={"detail": "achado não encontrado"})
    resposta = navegador.post(f"{BASE}/anotacoes", {"achado_id": "x", "texto": "nota"})
    assert resposta.status_code == 404
    assert "Achado não encontrado." in resposta.content.decode()


def test_visualizador_de_processo_inexistente_mostra_nao_encontrado(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02: 404 da API nos arquivos vira a página "não encontrado"."""
    logado.get(f"{BASE}/arquivos").respond(404, json={"detail": "processo não encontrado"})
    assert navegador.get(f"{BASE}/visualizador").status_code == 404


def _selo(tom: str, texto: str) -> str:
    return (
        f'<span class="selo selo-{tom}" data-componente="selo" data-testid="resultado">'
        f"{texto}</span>"
    )


def test_resultado_tempestivo_aparece_no_selo_de_sucesso(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-VIS-03 (D7): o resultado conforme vai no selo de sucesso, com o texto do resultado."""
    _simular_analise(logado)
    html = navegador.get(f"{BASE}/validacoes").content.decode()
    assert _selo("sucesso", "Conforme") in html


def test_atencao_e_falha_usam_selo_do_seu_tom(logado: respx.MockRouter, navegador: Client) -> None:
    """RF-VIS-03 (D7): "verificar" vai no selo de atenção e "atenção" no de falha."""
    _simular_analise(logado)
    achados = [
        ACHADO_VIGENTE | {"id": "e1" * 32, "resultado": "verificar"},
        ACHADO_VIGENTE | {"id": "e2" * 32, "resultado": "atencao", "validacao": "preparo"},
    ]
    logado.get(f"{BASE}/achados").respond(200, json={"processo_id": PROCESSO, "achados": achados})
    html = navegador.get(f"{BASE}/validacoes").content.decode()
    assert _selo("atencao", "Verificar") in html
    assert _selo("falha", "Atenção") in html
    assert 'class="resultado' not in html
