"""Reaproveitamento das páginas de originais idênticos entre processos disponíveis (RF-ING-08)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.tabelas import (
    atributos_do_satelite,
    sat_pagina_extracao,
    sat_pagina_saneamento,
)
from lupa_pipeline.dominio.visoes import VisaoArquivo, VisaoPagina, VisaoProcesso
from lupa_pipeline.ingestao.paginas import gravar_pagina
from lupa_pipeline.seguranca.contexto import abrir_dek, obter_cofre, registrar_dek


def copiar_do_cache(
    session: Session, destino: VisaoArquivo, versao: str, total: int, pendentes: set[int]
) -> set[int]:
    """Copia apenas páginas pendentes, decifrando na origem e cifrando com a DEK de destino."""
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
            VisaoProcesso.chave_dados_cifrada.is_not(None),
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
    chave = session.execute(
        select(VisaoProcesso.hk_processo, VisaoProcesso.chave_dados_cifrada)
        .join(VisaoArquivo, VisaoArquivo.hk_processo == VisaoProcesso.hk_processo)
        .where(VisaoArquivo.hk_arquivo == fonte)
    ).one()
    if chave.chave_dados_cifrada is None:
        return set()
    registrar_dek(
        chave.hk_processo, abrir_dek(obter_cofre(), chave.chave_dados_cifrada), atual=False
    )
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
