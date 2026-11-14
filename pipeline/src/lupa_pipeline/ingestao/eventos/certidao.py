"""Marcos de intimação e citação em certidões."""

from collections.abc import Iterator

from lupa_pipeline.dominio.enums import TipoFato
from lupa_pipeline.ingestao.eventos.base import Fonte
from lupa_pipeline.ingestao.eventos.modelo import Candidato


def extrair(fonte: Fonte) -> Iterator[Candidato]:
    """Extrai os marcos distintos documentados na certidão."""
    yield from fonte.datas(TipoFato.DATA_INTIMACAO, TipoFato.DATA_CITACAO)
