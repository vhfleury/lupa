"""Contrato da regra tempestividade_recurso no catálogo cível."""

from datetime import date

from lupa_pipeline.validacoes.modelo import AchadoValidacao, ModeloProcesso

NOME = "tempestividade_recurso"
BASE_LEGAL = "arts. 180, 183, 186, 219, 220, 224, 1.003 § 5º e 1.023 do CPC"


def executar(modelo: ModeloProcesso, referencia: date) -> AchadoValidacao:
    """Conferência de tempestividade do recorrente."""
    raise NotImplementedError
