"""Indicação literal do inciso do art. 1.015 citado na decisão agravada."""

import re
from collections.abc import Iterator

from lupa_pipeline.dominio.enums import TipoFato
from lupa_pipeline.ingestao.eventos import sentenca
from lupa_pipeline.ingestao.eventos.base import Fonte
from lupa_pipeline.ingestao.eventos.modelo import Candidato
from lupa_pipeline.ingestao.texto import dobrar

HIPOTESE = re.compile(
    r"art(?:igo|\.)?\s*1[.]?015(?:\s+do cpc)?[\s,–-]*(?:inciso\s+)?"
    r"(xiii|xii|xi|ix|viii|vii|vi|iv|iii|ii|x|v|i)\b"
)


def extrair(fonte: Fonte) -> Iterator[Candidato]:
    """Preserva a hipótese e os marcos que a decisão documenta."""
    yield from sentenca.extrair(fonte)
    for m in HIPOTESE.finditer(fonte.pagina.dobrado):
        yield fonte.candidato(TipoFato.HIPOTESE_DECISAO_AGRAVADA, m[1].upper(), *m.span())
