"""Reaproveitamento das páginas de originais idênticos entre processos disponíveis (RF-ING-08)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.enums import StatusProcesso
from lupa_pipeline.dominio.tabelas import (
    atributos_do_satelite,
    sat_pagina_extracao,
    sat_pagina_saneamento,
)
from lupa_pipeline.dominio.visoes import VisaoArquivo, VisaoPagina, VisaoProcesso
from lupa_pipeline.ingestao.paginas import gravar_pagina


def copiar_do_cache(
    session: Session, destino: VisaoArquivo, versao: str, total: int, pendentes: set[int]
) -> set[int]:
    """Copia apenas as páginas pendentes de um arquivo idêntico de processo não descartado."""
    if not pendentes:
        return set()
    consulta = (
        select(VisaoPagina.hk_arquivo)
        .join(VisaoArquivo, VisaoArquivo.hk_arquivo == VisaoPagina.hk_arquivo)
        .join(VisaoProcesso, VisaoProcesso.hk_processo == VisaoArquivo.hk_processo)
        .where(
            VisaoArquivo.sha256 == destino.sha256,
            VisaoArquivo.hk_arquivo != destino.hk_arquivo,
            VisaoArquivo.estado == "concluido",
            VisaoProcesso.status.is_distinct_from(StatusProcesso.DESCARTADO.value),
            VisaoPagina.versao_extrator == versao,
        )
        .group_by(VisaoPagina.hk_arquivo)
        .having(func.count() == total)
        .order_by(VisaoPagina.hk_arquivo)
        .limit(1)
    )
    fonte = session.scalar(consulta)
    if fonte is None:
        return set()
    campos = [
        *atributos_do_satelite(sat_pagina_extracao),
        *atributos_do_satelite(sat_pagina_saneamento),
    ]
    linhas = session.scalars(
        select(VisaoPagina)
        .where(
            VisaoPagina.hk_arquivo == fonte,
            VisaoPagina.numero.in_(pendentes),
            VisaoPagina.versao_extrator == versao,
        )
        .order_by(VisaoPagina.numero)
    )
    copiadas = set()
    for pagina in linhas:
        linha = {campo: getattr(pagina, campo) for campo in campos}
        gravar_pagina(session, destino, linha | {"numero": pagina.numero})
        copiadas.add(pagina.numero)
    return copiadas
