"""Tela do processo: desvios da API e formatação dos arquivos (RF-INT-02)."""

import pytest
import respx
from django.test import Client

from lupa_web.telas import processo
from tests.telas.conftest import sessao_da_api
from tests.telas.test_paridade import ARQUIVO, BASE, _simular_arquivo, _simular_processo


def test_processo_inexistente_mostra_nao_encontrado(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02: 404 da API (inexistente ou descartado) vira a página "não encontrado"."""
    logado.get(BASE).respond(404, json={"detail": "processo não encontrado"})
    resposta = navegador.get(BASE)
    assert resposta.status_code == 404
    assert "Registro não encontrado" in resposta.content.decode()


def test_confirmacao_de_descarte_de_processo_inexistente(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02: a confirmação do descarte também responde 404 sem processo."""
    logado.get(BASE).respond(404, json={"detail": "processo não encontrado"})
    assert navegador.get(f"{BASE}/descartar").status_code == 404


def test_arquivo_inexistente_mostra_nao_encontrado(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02: arquivo que a API não encontra vira 404."""
    logado.get(f"{BASE}/arquivos/{ARQUIVO}/relatorio").respond(404, json={"detail": "x"})
    assert navegador.get(f"{BASE}/arquivos/{ARQUIVO}").status_code == 404


def test_arquivo_sem_diagnostico_avisa(logado: respx.MockRouter, navegador: Client) -> None:
    """RF-ING-03: diagnóstico ainda não gerado aparece como aviso, sem erro da tela."""
    _simular_arquivo(logado, "assessor")
    logado.get(f"{BASE}/arquivos/{ARQUIVO}/diagnostico").respond(404, json={"detail": "x"})
    resposta = navegador.get(f"{BASE}/arquivos/{ARQUIVO}")
    assert resposta.status_code == 200
    assert "Diagnóstico ainda não disponível." in resposta.content.decode()


def test_conflito_na_distribuicao_mostra_a_mensagem_da_api(
    api_simulada: respx.MockRouter, navegador: Client
) -> None:
    """RF-PRO-03 (A1.8): o 409 da API volta à tela do processo com a mensagem e o status."""
    api_simulada.get("/auth/sessao").respond(200, json=sessao_da_api("desembargador"))
    _simular_processo(api_simulada, "desembargador")
    api_simulada.post(f"{BASE}/responsaveis").respond(
        409, json={"detail": "Os responsáveis mudaram. Recarregue a lista antes de salvar."}
    )
    resposta = navegador.post(f"{BASE}/responsaveis", {"usuarios": ["x"], "anteriores": []})
    assert resposta.status_code == 409
    assert "Os responsáveis mudaram." in resposta.content.decode()


def test_aviso_da_distribuicao_aparece_depois_do_redirecionamento(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-PRO-03: depois de salvar, a tela confirma a distribuição."""
    _simular_processo(logado, "assessor")
    html = navegador.get(BASE, {"aviso": "responsaveis"}).content.decode()
    assert "Responsáveis atualizados." in html


@pytest.mark.parametrize(
    ("tamanho", "esperado"),
    [
        (None, "—"),
        (512, "512 B"),
        (1536, "1,5 KB"),
        (5 * 1024**2, "5,0 MB"),
        (3 * 1024**4, "3072,0 GB"),
    ],
)
def test_formatar_bytes(tamanho: int | None, esperado: str) -> None:
    """RF-INT-02: tamanhos dos arquivos aparecem em B, KB, MB ou GB."""
    assert processo.formatar_bytes(tamanho) == esperado


@pytest.mark.parametrize(
    ("arquivo", "esperado"),
    [
        ({"estado": "falho", "motivo_falha": "erro_parser"}, "Erro ao ler o PDF."),
        ({"estado": "parcial", "relatorio": {"faltantes": [3, 5]}}, "Páginas faltantes: 3, 5"),
        ({"estado": "parcial", "relatorio": None}, ""),
        ({"estado": "concluido"}, ""),
    ],
)
def test_detalhe_do_estado(arquivo: dict[str, object], esperado: str) -> None:
    """RF-ING-06: falha, páginas faltantes e quarentena têm explicação na linha do arquivo."""
    assert processo.detalhe_do_estado(arquivo) == esperado
