"""Data da decisão recorrida e decisão de gratuidade."""

from collections.abc import Iterator

from lupa_pipeline.dominio.enums import TipoFato
from lupa_pipeline.ingestao.eventos import preparo
from lupa_pipeline.ingestao.eventos.base import Fonte
from lupa_pipeline.ingestao.eventos.modelo import Candidato


def extrair(fonte: Fonte) -> Iterator[Candidato]:
    """Localiza a decisão recorrida e o dispositivo sobre gratuidade."""
    yield from fonte.datas(TipoFato.DATA_DECISAO_RECORRIDA)
    yield from preparo.decisao(fonte)
