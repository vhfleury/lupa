"""Tipo de coluna `JsonTexto`: valor JSON serializado numa coluna `TEXT` (RF-SEG-01)."""

import json
from typing import Any

from sqlalchemy import Text
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class JsonTexto(TypeDecorator[Any]):
    """JSON gravado como texto em claro, com `ensure_ascii=False`."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        """Serializa na gravação.

        Args:
            value: Valor JSON.
            dialect: Dialeto (não usado).

        Returns:
            Texto JSON, ou None.
        """
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value: str | None, dialect: Dialect) -> Any:
        """Desserializa na leitura.

        Args:
            value: Texto JSON do banco.
            dialect: Dialeto (não usado).

        Returns:
            Valor JSON, ou None.
        """
        if value is None:
            return None
        return json.loads(value)
