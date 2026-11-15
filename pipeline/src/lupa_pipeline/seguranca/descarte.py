"""Descarte dos satélites e limpeza dos objetos do processo (A13; RF-SEG-01)."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.enums import StatusProcesso
from lupa_pipeline.dominio.gravacao import gravar_satelite
from lupa_pipeline.dominio.tabelas import sat_processo_estado
from lupa_pipeline.ingestao.storage import ObjectStorage, prefixo_processo

PREFIXO_RENDERIZACAO = "renderizacao/"


def descartar(session: Session, hk_processo: bytes) -> None:
    """Apaga os satélites de conteúdo do processo travado e grava o estado descartado.

    Roda na transação de quem chama, a mesma do evento de auditoria.
    """
    session.execute(text("SELECT lupa_descartar_processo(:hk)"), {"hk": hk_processo})
    gravar_satelite(
        session,
        sat_processo_estado,
        hk_processo,
        {"status": StatusProcesso.DESCARTADO.value},
        "pipeline.descarte",
    )


def apagar_objetos(storage: ObjectStorage, hk_processo: bytes) -> int:
    """Apaga os originais e PNGs em cache de todas as versões depois do commit do descarte."""
    base = prefixo_processo(hk_processo)
    objetos = storage.listar(base)
    objetos.extend(chave for chave in storage.listar(PREFIXO_RENDERIZACAO) if f"/{base}" in chave)
    for chave in objetos:
        storage.apagar(chave)
    return len(objetos)
