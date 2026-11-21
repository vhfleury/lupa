"""Converte o achado calculado pelas validações no achado do domínio."""

from lupa_pipeline.dominio.esquemas import Achado
from lupa_pipeline.validacoes.modelo import AchadoValidacao


def para_dominio(achado_validacao: AchadoValidacao, processo_id: str, achado_id: str) -> Achado:
    """Vincula o achado ao processo preservando as referências às evidências do recorrente."""
    return Achado(id=achado_id, processo_id=processo_id, **achado_validacao.model_dump())
