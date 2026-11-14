"""Papel de banco da aplicação: `lupa_app`, só com SELECT e INSERT (RES-13)."""

from sqlalchemy import text
from sqlalchemy.orm import Session

PAPEL_APLICACAO = "lupa_app"


def assumir_papel_aplicacao(session: Session) -> None:
    """Troca, só na transação corrente, para o papel sem UPDATE, DELETE nem TRUNCATE.

    Args:
        session: Sessão SQLAlchemy com transação aberta.
    """
    session.execute(text(f"SET LOCAL ROLE {PAPEL_APLICACAO}"))
