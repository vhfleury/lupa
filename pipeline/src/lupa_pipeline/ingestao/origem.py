"""Origem dos trechos de uma página segundo a classificação vigente (RF-ING-05)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.enums import OrigemPeca
from lupa_pipeline.dominio.visoes import VisaoPagina, VisaoPeca


def origem_da_pagina(session: Session, pagina_id: bytes) -> OrigemPeca:
    """Origem da peça que contém a página.

    Só contam as peças vigentes (a reclassificação manual encerra a versão anterior); com mais
    de uma cobrindo a página, vale a de maior confiança; sem peça, `desconhecida`.

    Args:
        session: Sessão com transação aberta.
        pagina_id: Página.

    Returns:
        Origem da peça, ou `desconhecida`.
    """
    pagina = session.get(VisaoPagina, pagina_id)
    if pagina is None:
        return OrigemPeca.DESCONHECIDA
    consulta = (
        select(VisaoPeca.origem)
        .where(
            VisaoPeca.arquivo_id == pagina.arquivo_id,
            VisaoPeca.vigente.is_(True),
            VisaoPeca.pagina_inicial <= pagina.numero,
            VisaoPeca.pagina_final >= pagina.numero,
        )
        .order_by(VisaoPeca.confianca.desc(), VisaoPeca.id)
        .limit(1)
    )
    origem = session.scalar(consulta)
    return OrigemPeca(origem) if origem else OrigemPeca.DESCONHECIDA


def rotular(trechos: list[dict[str, Any]], origem: OrigemPeca) -> list[dict[str, Any]]:
    """Aplica a origem a trechos (o rótulo ausente vira `desconhecida`).

    Args:
        trechos: Trechos suspeitos.
        origem: Origem da peça (use `desconhecida` quando não houver).

    Returns:
        Cópias dos trechos com `origem`.
    """
    return [t | {"origem": (origem or OrigemPeca.DESCONHECIDA).value} for t in trechos]


def trechos_rotulados(session: Session, pagina_id: bytes) -> list[dict[str, Any]]:
    """Trechos suspeitos da página com a origem da peça.

    Args:
        session: Sessão com transação aberta.
        pagina_id: Página.

    Returns:
        Trechos com `origem`; lista vazia se a página não existe.
    """
    pagina = session.get(VisaoPagina, pagina_id)
    if pagina is None:
        return []
    return rotular(list(pagina.trechos_suspeitos or []), origem_da_pagina(session, pagina_id))
