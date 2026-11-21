"""Textos e candidatos com posição verificável na página de origem (A6)."""

from dataclasses import dataclass
from functools import cached_property
from typing import Any

from lupa_pipeline.dominio.chaves import chave_hash
from lupa_pipeline.dominio.enums import TipoFato, TipoPeca
from lupa_pipeline.dominio.esquemas import Evidencia
from lupa_pipeline.ingestao.datas import OcorrenciaData, datas_no_dobrado
from lupa_pipeline.ingestao.texto import dobrar


@dataclass(frozen=True)
class PaginaTexto:
    """Página de peça e versões original e normalizada de seu texto.

    O texto dobrado e as datas do normalizado são calculados no primeiro acesso e guardados.
    """

    id: str
    numero: int
    texto: str
    normalizado: str
    suspeitos: tuple[tuple[int, int], ...] = ()

    @cached_property
    def dobrado(self) -> str:
        """Normalizado em minúsculas sem acento, com o mesmo comprimento."""
        return dobrar(self.normalizado)

    @cached_property
    def datas(self) -> tuple[OcorrenciaData, ...]:
        """Datas do normalizado, com offsets no texto dobrado."""
        return tuple(datas_no_dobrado(self.dobrado, self.normalizado))


@dataclass(frozen=True)
class PecaTexto:
    """Tipo vigente com suas páginas na ordem do arquivo."""

    tipo: TipoPeca
    paginas: tuple[PaginaTexto, ...]


@dataclass(frozen=True)
class Candidato:
    """Fato candidato com o trecho literal e seu intervalo na página normalizada."""

    tipo: TipoFato
    valor: Any
    pagina: PaginaTexto
    inicio: int
    fim: int
    trecho: str
    sujeito: str = ""


def evidencia_de(pagina: PaginaTexto, inicio: int, fim: int, trecho: str) -> Evidencia | None:
    """Reconfere o texto normalizado e mapeia os offsets para a página original."""
    from lupa_pipeline.ingestao.saneamento_pagina import mapa_saneado

    if not 0 <= inicio < fim <= len(pagina.normalizado) or pagina.normalizado[inicio:fim] != trecho:
        return None
    if pagina.texto != pagina.normalizado:
        mapa = mapa_saneado(pagina.texto)
        if mapa.texto != pagina.normalizado:
            return None
        inicio, fim = mapa.inicios[inicio], mapa.fins[fim - 1]
    if any(a < fim and b > inicio for a, b in pagina.suspeitos):
        return None
    return Evidencia(
        id=chave_hash([pagina.id, inicio, fim]).hex(),
        pagina_id=pagina.id,
        inicio=inicio,
        fim=fim,
        trecho=pagina.texto[inicio:fim],
    )
