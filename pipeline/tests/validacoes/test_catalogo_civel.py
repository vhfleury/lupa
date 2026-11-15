"""Seleção de validações por classe do recurso (RF-VAL-01)."""

import pytest

from lupa_pipeline.validacoes.catalogo import validacoes_de


@pytest.mark.parametrize(
    ("classe", "nomes"),
    [
        ("apelacao_civel", ["tempestividade_recurso", "preparo_recurso", "representacao_recurso"]),
        ("agravo_interno", ["tempestividade_recurso", "preparo_recurso", "representacao_recurso"]),
        ("embargos_declaracao", ["tempestividade_recurso", "representacao_recurso"]),
        (
            "agravo_instrumento",
            [
                "tempestividade_recurso",
                "preparo_recurso",
                "representacao_recurso",
                "cabimento_agravo",
            ],
        ),
        ("acao_originaria", []),
    ],
)
def test_catalogo_aplica_apenas_as_regras_da_classe(classe: str, nomes: list[str]) -> None:
    """RF-VAL-01: a tabela 3.1 decide as regras para cada uma das cinco classes."""
    assert [regra.nome for regra in validacoes_de(classe)] == nomes
