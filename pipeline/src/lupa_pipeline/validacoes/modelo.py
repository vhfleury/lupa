"""Modelo imutável dos fatos de um processo e resultados rastreáveis das validações cíveis."""

import json
from collections.abc import Iterable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from lupa_pipeline.dominio.enums import ResultadoAchado as ResultadoAchadoDominio
from lupa_pipeline.dominio.esquemas import Evidencia, Fato

__all__ = [
    "AchadoValidacao",
    "ConflitoDeFatosError",
    "Evidencia",
    "Fato",
    "ModeloProcesso",
    "ResultadoAchado",
    "valor_de",
]

ResultadoAchado = Literal["conforme", "atencao", "verificar"]


class AchadoValidacao(BaseModel):
    """Resultado de uma regra antes de persistir o achado no processo."""

    model_config = ConfigDict(frozen=True)
    validacao: str
    sujeito: str = ""
    versao_catalogo: str
    resultado: ResultadoAchadoDominio
    fatos_usados: tuple[str, ...]
    valores: dict[str, Any]
    explicacao: str


class ConflitoDeFatosError(ValueError):
    """O tipo que deveria ter um valor tem dois ou mais valores diferentes."""

    def __init__(self, tipo: str, fato_ids: list[str]) -> None:
        """Guarda as referências dos fatos divergentes."""
        super().__init__(f"valores divergentes para o fato {tipo}")
        self.tipo = tipo
        self.fato_ids = fato_ids


def valor_de(fato: Fato) -> Any:
    """Extrai o valor do fato, inclusive quando vem no campo valor do JSON."""
    if isinstance(fato.valor, dict) and "valor" in fato.valor:
        return fato.valor["valor"]
    return fato.valor


class ModeloProcesso:
    """Índice de fatos vigentes por tipo e sujeito."""

    def __init__(self, fatos: Iterable[Fato], *, sujeito: str = "") -> None:
        """Indexa os fatos com ordem estável para consulta e gravação dos resultados."""
        self.sujeito = sujeito
        self._fatos = tuple(sorted(fatos, key=lambda f: f.id))
        self._indice: dict[str, list[Fato]] = {}
        for fato in self._fatos:
            self._indice.setdefault(fato.tipo, []).append(fato)

    @property
    def todos(self) -> tuple[Fato, ...]:
        """Todos os fatos em ordem de identificador."""
        return self._fatos

    def fatos(self, tipo: str) -> list[Fato]:
        """Lista os fatos de um tipo."""
        return list(self._indice.get(tipo, ()))

    def fato(self, tipo: str) -> Fato | None:
        """Lê um valor único ou levanta conflito com referências aos fatos divergentes."""
        lista = self.fatos(tipo)
        if not lista:
            return None
        if len({json.dumps(valor_de(f), sort_keys=True, default=str) for f in lista}) > 1:
            raise ConflitoDeFatosError(tipo, [str(f.id) for f in lista])
        return lista[0]

    def recorrentes(self, classe: str) -> list["ModeloProcesso"]:
        """Recorta os fatos do recurso da classe por recorrente, incluindo os fatos comuns."""
        identificados = self.fatos("tipo_recurso")
        sujeitos = sorted({f.sujeito for f in identificados if valor_de(f) == classe})
        if identificados and not sujeitos:
            return []
        if not sujeitos:
            sujeitos = sorted({f.sujeito for f in self._fatos if f.sujeito}) or [""]
        return [
            ModeloProcesso(
                (f for f in self._fatos if f.sujeito in ("", sujeito)),
                sujeito=sujeito,
            )
            for sujeito in sujeitos
        ]
