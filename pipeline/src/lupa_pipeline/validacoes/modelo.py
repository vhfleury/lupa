"""Modelo imutável dos fatos de um processo e resultados rastreáveis das validações cíveis."""

import json
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict

from lupa_pipeline.dominio.enums import ResultadoAchado as ResultadoAchadoDominio
from lupa_pipeline.dominio.esquemas import Evidencia, Fato

__all__ = [
    "AchadoValidacao",
    "ConflitoDeFatosError",
    "Evidencia",
    "Fato",
    "ModeloProcesso",
]


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


class ModeloProcesso:
    """Índice de fatos vigentes por tipo e sujeito, com `fato` e `recorrentes` memorizados."""

    def __init__(self, fatos: Iterable[Fato], *, sujeito: str = "") -> None:
        """Indexa os fatos, com o valor lido por `Fato.de_registro`, em ordem estável."""
        self.sujeito = sujeito
        self._fatos = tuple(
            sorted((Fato.de_registro(f.model_dump()) for f in fatos), key=lambda f: f.id)
        )
        self._indice: dict[str, list[Fato]] = {}
        for fato in self._fatos:
            self._indice.setdefault(fato.tipo, []).append(fato)
        self._unicos: dict[str, Fato | None] = {}
        self._conflitos: dict[str, list[str]] = {}
        self._recortes: dict[str, list[ModeloProcesso]] = {}

    @property
    def todos(self) -> tuple[Fato, ...]:
        """Todos os fatos em ordem de identificador."""
        return self._fatos

    def fatos(self, tipo: str) -> list[Fato]:
        """Lista os fatos de um tipo."""
        return list(self._indice.get(tipo, ()))

    def fato(self, tipo: str) -> Fato | None:
        """Lê um valor único ou levanta conflito com referências aos fatos divergentes."""
        if tipo in self._conflitos:
            raise ConflitoDeFatosError(tipo, list(self._conflitos[tipo]))
        if tipo not in self._unicos:
            lista = self.fatos(tipo)
            if len({json.dumps(f.valor, sort_keys=True, default=str) for f in lista}) > 1:
                self._conflitos[tipo] = [str(f.id) for f in lista]
                raise ConflitoDeFatosError(tipo, list(self._conflitos[tipo]))
            self._unicos[tipo] = lista[0] if lista else None
        return self._unicos[tipo]

    def recorrentes(self, classe: str) -> list["ModeloProcesso"]:
        """Recorta os fatos do recurso da classe por recorrente, incluindo os fatos comuns."""
        if classe not in self._recortes:
            self._recortes[classe] = self._recortar(classe)
        return list(self._recortes[classe])

    def _recortar(self, classe: str) -> list["ModeloProcesso"]:
        identificados = self.fatos("tipo_recurso")
        sujeitos = sorted({f.sujeito for f in identificados if f.valor == classe})
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
