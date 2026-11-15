"""Resultados da extração por processo (A5, A6)."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from lupa_pipeline.dominio.esquemas import Achado
from lupa_pipeline.dominio.repositorios import listar_achados, salvar_achado


def achados_vigentes(session: Session, processo_id: bytes) -> list[Achado]:
    """Lista o último resultado por validação e recorrente."""
    return listar_achados(session, processo_id)


def gravar_achados(session: Session, processo_id: bytes, achados: Sequence[Achado]) -> int:
    """Conta as versões novas do catálogo do processo."""
    if any(a.processo_id != processo_id.hex() for a in achados):
        raise ValueError("achado de outro processo")
    return sum(salvar_achado(session, achado) for achado in achados)
