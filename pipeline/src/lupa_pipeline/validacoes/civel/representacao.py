"""Contrato da regra representacao_recurso no catálogo cível."""

from datetime import date

from lupa_pipeline.validacoes.modelo import AchadoValidacao, ModeloProcesso

NOME = "representacao_recurso"
BASE_LEGAL = "arts. 75, 103 e 104 do CPC"


def executar(modelo: ModeloProcesso, referencia: date) -> AchadoValidacao:
    """Conferência de representacao do recorrente."""
    raise NotImplementedError
