"""Contrato da regra preparo_recurso no catálogo cível."""

from datetime import date

from lupa_pipeline.validacoes.modelo import AchadoValidacao, ModeloProcesso

NOME = "preparo_recurso"
BASE_LEGAL = "arts. 98, 99 § 7º e 1.007 do CPC"


def executar(modelo: ModeloProcesso, referencia: date) -> AchadoValidacao:
    """Conferência de preparo do recorrente."""
    raise NotImplementedError
