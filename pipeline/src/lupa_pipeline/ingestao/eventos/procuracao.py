"""Procurações, substabelecimentos e inscrições profissionais."""

import re
from collections.abc import Iterator
from typing import Any

from lupa_pipeline.dominio.enums import TipoFato
from lupa_pipeline.ingestao.eventos.base import Fonte
from lupa_pipeline.ingestao.eventos.modelo import Candidato

ADVOGADO = (
    r"(?P<nome>[^,\n;:]+?)[ \t]*[,–-][ \t]*OAB[ /-]+"
    r"(?P<uf>[A-Z]{2})[ /-]*(?:n[º°.]?\s*)?(?P<numero>\d+(?:\.\d+)*[A-Z]?)"
)
OUTORGADO = re.compile(r"(?:outorgad[oa]|substabelecid[oa])\s*:\s*" + ADVOGADO, re.I)
SUBSTABELECENTE = re.compile(r"(?:substabelecente|outorgante)\s*:\s*" + ADVOGADO, re.I)


def advogado(m: re.Match[str]) -> dict[str, str]:
    """Normaliza a inscrição com a UF e o número, preservando o nome literal."""
    return {"nome": m["nome"].strip(), "oab": (m["uf"] + m["numero"].replace(".", "")).upper()}


def extrair(fonte: Fonte) -> Iterator[Candidato]:
    """Vincula o outorgante à inscrição do advogado que recebeu os poderes."""
    texto = fonte.pagina.normalizado
    substabelecente = SUBSTABELECENTE.search(texto)
    for m in OUTORGADO.finditer(texto):
        outorgante = advogado(substabelecente) if substabelecente else fonte.sujeito
        if outorgante:
            mandato: dict[str, Any] = {
                "tipo": "substabelecimento" if substabelecente else "procuracao",
                "outorgante": outorgante,
                "advogado": advogado(m),
            }
            yield fonte.candidato(TipoFato.PROCURACAO, mandato, *m.span())
