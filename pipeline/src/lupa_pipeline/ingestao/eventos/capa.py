"""Valores e evidências literais da autuação cível (A4)."""

import re
from collections.abc import Callable, Iterator

from lupa_pipeline.dominio.enums import TipoFato
from lupa_pipeline.ingestao.datas import datas_no_dobrado
from lupa_pipeline.ingestao.eventos.base import Fonte
from lupa_pipeline.ingestao.eventos.modelo import Candidato
from lupa_pipeline.ingestao.eventos.padroes import campo_capa

TIPOS_CAPA = (
    TipoFato.RELATOR,
    TipoFato.ORGAO_JULGADOR,
    TipoFato.ASSUNTO,
    TipoFato.VALOR_CAUSA,
    TipoFato.JUIZO_ORIGEM,
    TipoFato.DATA_DISTRIBUICAO,
)
REAIS = re.compile(r"(?:r\$\s*)?(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{2}))?")


def _valor_da_causa(literal: str, dobrado: str) -> str | None:
    if moeda := REAIS.fullmatch(dobrado):
        reais = moeda[1].replace(".", "").lstrip("0") or "0"
        return f"{reais}.{moeda[2] or '00'}"
    return None


def _data_de_distribuicao(literal: str, dobrado: str) -> str | None:
    datas = datas_no_dobrado(dobrado, literal)
    return datas[0].iso if len(datas) == 1 and datas[0].inicio == 0 else None


def _literal(literal: str, dobrado: str) -> str | None:
    return literal


CONVERSORES_CAPA: dict[TipoFato, Callable[[str, str], str | None]] = {
    TipoFato.VALOR_CAUSA: _valor_da_causa,
    TipoFato.DATA_DISTRIBUICAO: _data_de_distribuicao,
}


def extrair(fonte: Fonte) -> Iterator[Candidato]:
    """Extrai cada campo no intervalo do valor da linha rotulada."""
    fonte = Fonte(fonte.pagina, "")
    texto = fonte.pagina.normalizado
    dobrado = fonte.pagina.dobrado
    for tipo in TIPOS_CAPA:
        converter = CONVERSORES_CAPA.get(tipo, _literal)
        for campo in campo_capa(tipo.value).finditer(dobrado):
            inicio, fim = campo.span("valor")
            if (valor := converter(texto[inicio:fim], dobrado[inicio:fim])) is not None:
                yield fonte.candidato(tipo, valor, inicio, fim)
