"""Converte entre fatos e achados do domínio e o modelo puro das validações."""

from collections.abc import Iterable

from lupa_pipeline.dominio.esquemas import Achado, Fato
from lupa_pipeline.validacoes.modelo import AchadoValidacao, ModeloProcesso


def para_modelo(fatos: Iterable[Fato]) -> ModeloProcesso:
    """Indexa os fatos vigentes para o motor."""
    return ModeloProcesso(fatos)


def para_dominio(achado_validacao: AchadoValidacao, processo_id: str, achado_id: str) -> Achado:
    """Vincula o achado ao processo preservando as referências às evidências do recorrente."""
    return Achado(id=achado_id, processo_id=processo_id, **achado_validacao.model_dump())
