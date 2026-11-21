"""Conversão dos fatos extraídos para a saída medida por ``pipeline/scripts/medir.py``."""

from collections.abc import Iterable, Mapping

from lupa_pipeline.dominio.enums import TipoFato
from lupa_pipeline.dominio.esquemas import Fato
from lupa_pipeline.sinteticos.saida_pipeline import EventoSaida, RefPagina


def eventos_saida(
    fatos: Iterable[Fato], paginas: Mapping[str, RefPagina], nomes: Mapping[str, str] | None = None
) -> tuple[EventoSaida, ...]:
    """Um evento por fato na página de origem da primeira evidência.

    Args:
        fatos: Fatos extraídos.
        paginas: Páginas por id (com arquivo e página de origem).
        nomes: Nome da parte por id para comparar o outorgante com o gabarito.

    Returns:
        Eventos no formato de ``lupa_pipeline.sinteticos.saida_pipeline``.
    """
    eventos = []
    for fato in fatos:
        ref = paginas[fato.evidencias[0].pagina_id]
        valor = fato.valor
        if nomes and fato.tipo is TipoFato.PROCURACAO and isinstance(valor, dict):
            outorgante = valor.get("outorgante")
            if isinstance(outorgante, str):
                valor = valor | {"outorgante": nomes.get(outorgante, outorgante)}
        eventos.append(
            EventoSaida(tipo=fato.tipo, valor=valor, ref=ref, trecho=fato.evidencias[0].trecho)
        )
    return tuple(eventos)
