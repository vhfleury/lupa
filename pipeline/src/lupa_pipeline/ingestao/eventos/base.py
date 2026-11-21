"""Construtores de fatos com evidência literal na página normalizada."""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from lupa_pipeline.dominio.enums import TipoFato
from lupa_pipeline.ingestao.datas import datas_no_dobrado
from lupa_pipeline.ingestao.eventos.modelo import Candidato, PaginaTexto
from lupa_pipeline.ingestao.eventos.padroes import gatilho
from lupa_pipeline.ingestao.texto import dobrar


@dataclass(frozen=True)
class Fonte:
    """Página de trabalho e sujeito qualificado na peça."""

    pagina: PaginaTexto
    sujeito: str

    def candidato(self, tipo: TipoFato, valor: Any, inicio: int, fim: int) -> Candidato:
        """Recorta a evidência na posição reconhecida."""
        return Candidato(
            tipo, valor, self.pagina, inicio, fim, self.pagina.normalizado[inicio:fim], self.sujeito
        )

    def datas(self, *tipos: TipoFato) -> Iterator[Candidato]:
        """Vincula uma data válida ao marco explícito mais próximo."""
        texto = self.pagina.normalizado
        simples = dobrar(texto)
        for data in datas_no_dobrado(simples, texto):
            inicio = max(0, data.inicio - 110)
            prefixo = simples[inicio : data.inicio]
            for tipo in tipos:
                encontrado = gatilho(tipo).search(prefixo)
                if encontrado:
                    yield self.candidato(tipo, data.iso, inicio + encontrado.start(), data.fim)
