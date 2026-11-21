"""Valores e evidências literais da autuação cível (A4)."""

import re
from collections.abc import Iterator

from lupa_pipeline.dominio.enums import TipoFato
from lupa_pipeline.ingestao.datas import datas_no_dobrado
from lupa_pipeline.ingestao.eventos.base import Fonte
from lupa_pipeline.ingestao.eventos.modelo import Candidato
from lupa_pipeline.ingestao.eventos.padroes import campo_capa
from lupa_pipeline.ingestao.texto import dobrar

TIPOS_CAPA = (
    TipoFato.RELATOR,
    TipoFato.ORGAO_JULGADOR,
    TipoFato.ASSUNTO,
    TipoFato.VALOR_CAUSA,
    TipoFato.JUIZO_ORIGEM,
    TipoFato.DATA_DISTRIBUICAO,
)
REAIS = re.compile(r"(?:r\$\s*)?(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{2}))?")


def _valor(tipo: TipoFato, literal: str) -> str | None:
    if tipo == TipoFato.VALOR_CAUSA:
        if moeda := REAIS.fullmatch(dobrar(literal)):
            reais = moeda[1].replace(".", "").lstrip("0") or "0"
            return f"{reais}.{moeda[2] or '00'}"
        return None
    if tipo == TipoFato.DATA_DISTRIBUICAO:
        datas = datas_no_dobrado(dobrar(literal), literal)
        return datas[0].iso if len(datas) == 1 and datas[0].inicio == 0 else None
    return literal


def extrair(fonte: Fonte) -> Iterator[Candidato]:
    """Extrai cada campo no intervalo do valor da linha rotulada."""
    fonte = Fonte(fonte.pagina, "")
    texto = fonte.pagina.normalizado
    dobrado = dobrar(texto)
    for tipo in TIPOS_CAPA:
        for campo in campo_capa(tipo.value).finditer(dobrado):
            inicio, fim = campo.span("valor")
            if (valor := _valor(tipo, texto[inicio:fim])) is not None:
                yield fonte.candidato(tipo, valor, inicio, fim)
