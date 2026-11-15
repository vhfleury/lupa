"""Marcos documentados no ajuizamento, contestação e acórdão."""

from collections.abc import Iterator

from lupa_pipeline.dominio.enums import TipoFato, TipoPeca
from lupa_pipeline.ingestao.eventos.base import Fonte
from lupa_pipeline.ingestao.eventos.modelo import Candidato

MARCOS = {
    TipoPeca.PETICAO_INICIAL: TipoFato.DATA_AJUIZAMENTO,
    TipoPeca.CONTESTACAO: TipoFato.DATA_CONTESTACAO,
    TipoPeca.ACORDAO: TipoFato.DATA_ACORDAO,
}


def extrair(fonte: Fonte, peca: TipoPeca) -> Iterator[Candidato]:
    """Extrai o marco próprio da peça."""
    yield from fonte.datas(MARCOS[peca])
