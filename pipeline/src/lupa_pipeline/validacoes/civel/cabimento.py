"""Contrato da regra cabimento_agravo no catálogo cível."""

from datetime import date

from lupa_pipeline.validacoes.modelo import AchadoValidacao, ModeloProcesso

NOME = "cabimento_agravo"
BASE_LEGAL = "art. 1.015 do CPC"


def executar(modelo: ModeloProcesso, referencia: date) -> AchadoValidacao:
    """Conferência de cabimento do recorrente."""
    raise NotImplementedError
