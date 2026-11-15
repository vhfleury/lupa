"""Hipóteses de preparo, dispensa e gratuidade de um recorrente."""

from datetime import date
from typing import Any

import pytest

from lupa_pipeline.validacoes.civel.preparo import executar
from tests.validacoes.conftest import criar_fato, modelo_de


@pytest.mark.parametrize(
    ("qualidade", "extras", "resultado"),
    [
        ("particular", {"comprovante_preparo": "2026-08-10"}, "conforme"),
        ("particular", {"comprovante_preparo": "2026-08-11"}, "atencao"),
        ("particular", {}, "atencao"),
        ("particular", {"gratuidade_pedido": True}, "verificar"),
        ("particular", {"gratuidade_pedido": True, "gratuidade_decisao": "deferida"}, "conforme"),
        ("particular", {"gratuidade_pedido": True, "gratuidade_decisao": "indeferida"}, "atencao"),
        ("fazenda_publica", {}, "conforme"),
        ("ministerio_publico", {}, "conforme"),
        ("defensoria_publica", {}, "conforme"),
    ],
)
def test_preparo_segue_as_dispensas_e_a_data_da_interposicao(
    qualidade: str, extras: dict[str, Any], resultado: str
) -> None:
    """RF-VAL-03: dispensa, pedido pendente e comprovante têm desfechos distintos."""
    dados = {
        "tipo_recurso": "apelacao_civel",
        "qualidade_recorrente": qualidade,
        "data_interposicao": "2026-08-10",
        **extras,
    }
    achado = executar(modelo_de(*(criar_fato(k, v) for k, v in dados.items())), date(2026, 8, 10))
    assert achado.resultado == resultado
    assert achado.fatos_usados and "1.007" in achado.valores["base_legal"]


def test_falta_interposicao_impede_comparar_data_do_preparo() -> None:
    """RF-VAL-01, RF-VAL-03: comprovante sem marco de comparação requer conferência."""
    achado = executar(
        modelo_de(
            criar_fato("tipo_recurso", "apelacao_civel"),
            criar_fato("qualidade_recorrente", "particular"),
            criar_fato("comprovante_preparo", "2026-08-10"),
        ),
        date(2026, 8, 10),
    )
    assert achado.resultado == "verificar"
    assert achado.valores["faltantes"] == ["data_interposicao"]
