"""Associação da decisão agravada ao inciso, sujeita a conferência humana."""

from datetime import date

import pytest

from lupa_pipeline.validacoes.civel.cabimento import executar
from tests.validacoes.conftest import criar_fato, modelo_de


@pytest.mark.parametrize(
    ("inciso", "esperado"),
    [
        ("I", "conforme"),
        ("XI", "conforme"),
        ("XII", "verificar"),
        ("nao_identificada", "verificar"),
        (None, "verificar"),
    ],
)
def test_cabimento_identifica_inciso_e_preserva_a_evidencia(
    inciso: str | None, esperado: str
) -> None:
    """RF-VAL-05: um inciso reconhecido cita o trecho; decisão sem hipótese requer conferência."""
    fatos = [criar_fato("hipotese_decisao_agravada", inciso)] if inciso else []
    achado = executar(modelo_de(*fatos), date(2026, 8, 10))
    assert achado.resultado == esperado
    if esperado == "conforme":
        assert achado.valores["inciso"] == inciso
        assert achado.valores["trecho"] == fatos[0].evidencias[0].trecho
