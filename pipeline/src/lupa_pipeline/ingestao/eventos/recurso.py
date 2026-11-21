"""Espécie, interposição, qualidade e subscrição recursal."""

import re
from collections.abc import Iterator

from lupa_pipeline.dominio.enums import ClasseProcessual, TipoFato, TipoPeca
from lupa_pipeline.ingestao.eventos import preparo
from lupa_pipeline.ingestao.eventos.base import Fonte
from lupa_pipeline.ingestao.eventos.modelo import Candidato
from lupa_pipeline.ingestao.eventos.partes import qualidade
from lupa_pipeline.ingestao.eventos.procuracao import ADVOGADO, advogado
from lupa_pipeline.ingestao.texto import dobrar

RECURSOS = {
    TipoPeca.APELACAO: ClasseProcessual.APELACAO_CIVEL,
    TipoPeca.EMBARGOS_DECLARACAO: ClasseProcessual.EMBARGOS_DECLARACAO,
    TipoPeca.AGRAVO_INSTRUMENTO: ClasseProcessual.AGRAVO_INSTRUMENTO,
    TipoPeca.AGRAVO_INTERNO: ClasseProcessual.AGRAVO_INTERNO,
}
TITULOS = re.compile(
    r"(?im)^[ \t]*(?:recurso de )?(?:apelacao(?: civel)?|"
    r"agravo (?:de instrumento|interno)|embargos de declaracao)[ \t]*$"
)
ASSINATURA = re.compile(
    r"(?:advogad[oa](?: subscritor[a]?)?|subscritor[a]?)\s*:\s*" + ADVOGADO, re.I
)
QUALIDADE = re.compile(r"qualidade do recorrente:\s*([^\n.;]+)")
ROTULO_SUJEITO = re.compile(
    r"(?im)^[ \t]*(?:recorrente|apelante|agravante|embargante|outorgante|"
    r"intimad[oa]|benefici[áa]ri[oa])\s*[:–-][ \t]*([^\n,;.]+)"
)


def extrair(fonte: Fonte, tipo: TipoPeca, qualidade_explicita: bool) -> Iterator[Candidato]:
    """Extrai os elementos formais declarados no recurso."""
    texto = fonte.pagina.normalizado
    simples = fonte.pagina.dobrado
    for m in TITULOS.finditer(simples):
        yield fonte.candidato(TipoFato.TIPO_RECURSO, RECURSOS[tipo].value, *m.span())
    for m in ASSINATURA.finditer(texto):
        yield fonte.candidato(TipoFato.ADVOGADO_SUBSCRITOR, advogado(m), *m.span())
    for m in QUALIDADE.finditer(simples):
        yield fonte.candidato(TipoFato.QUALIDADE_RECORRENTE, qualidade(m[1]).value, *m.span())
    if not qualidade_explicita:
        for m in ROTULO_SUJEITO.finditer(texto):
            yield fonte.candidato(TipoFato.QUALIDADE_RECORRENTE, qualidade(m[1]).value, *m.span())
    yield from fonte.datas(TipoFato.DATA_INTERPOSICAO)
    yield from preparo.pedido(fonte)
