"""Recolhimento de custas e gratuidade da justiça."""

import re
from collections.abc import Iterator

from lupa_pipeline.dominio.enums import TipoFato
from lupa_pipeline.ingestao.datas import dobrar
from lupa_pipeline.ingestao.eventos.base import Fonte
from lupa_pipeline.ingestao.eventos.modelo import Candidato

DECISAO = re.compile(
    r"(?:gratuidade(?: da justica)? (in)?deferida|"
    r"(in)?defiro (?:o pedido de |a )?gratuidade(?: da justica)?)"
)
PEDIDO = re.compile(
    r"(?:requer(?:eu)?|pede|pedido de) (?:a |o beneficio da )?gratuidade(?: da justica)?"
)


def pedido(fonte: Fonte) -> Iterator[Candidato]:
    """Reconhece os pedidos expressos da parte."""
    for m in PEDIDO.finditer(dobrar(fonte.pagina.normalizado)):
        yield fonte.candidato(TipoFato.GRATUIDADE_PEDIDO, True, *m.span())


def decisao(fonte: Fonte) -> Iterator[Candidato]:
    """Reconhece deferimento e indeferimento expressos."""
    for m in DECISAO.finditer(dobrar(fonte.pagina.normalizado)):
        yield fonte.candidato(
            TipoFato.GRATUIDADE_DECISAO, "indeferida" if any(m.groups()) else "deferida", *m.span()
        )


def comprovante(fonte: Fonte) -> Iterator[Candidato]:
    """Extrai a data do recolhimento no comprovante."""
    yield from fonte.datas(TipoFato.COMPROVANTE_PREPARO)
