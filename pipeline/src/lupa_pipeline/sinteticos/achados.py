"""Compara os resultados persistidos aos achados esperados por regra, parte e folha de conteúdo."""

import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Protocol

from pydantic import BaseModel

from lupa_pipeline.sinteticos.gabarito import Gabarito, ResultadoEsperado
from lupa_pipeline.sinteticos.gerador import fatos_do_gabarito
from lupa_pipeline.sinteticos.medicao import mapa_folhas
from lupa_pipeline.sinteticos.saida_pipeline import RefPagina


def referencias_do_gabarito(gabarito: Gabarito) -> dict[str, str]:
    """Resolve os ids sintéticos de parte e página aos nomes e folhas do gabarito."""
    fatos = fatos_do_gabarito(gabarito.processo.numero_cnj, gabarito.eventos)
    referencias = {}
    for fato, evento in zip(fatos, gabarito.eventos, strict=True):
        if fato.sujeito:
            referencias[fato.sujeito] = evento.sujeito
        for evidencia in fato.evidencias:
            referencias[evidencia.pagina_id] = f"folha {evento.pagina}"
    return referencias


def referencias_de_paginas(gabarito: Gabarito, paginas: Mapping[str, RefPagina]) -> dict[str, str]:
    """Resolve a página física da extração à folha de conteúdo comum aos empacotamentos."""
    folhas = mapa_folhas(gabarito)
    return {
        pid: f"folha {folha}"
        for pid, p in paginas.items()
        if (folha := folhas.get((p.arquivo, p.pagina))) is not None
    }


class AchadoComparavel(Protocol):
    """Campos comuns ao gabarito e ao resultado do motor cível."""

    @property
    def validacao(self) -> str:
        """Nome da validação."""

    @property
    def sujeito(self) -> str:
        """Parte à qual se aplica o resultado."""

    @property
    def resultado(self) -> object:
        """Conclusão da regra."""

    @property
    def valores(self) -> dict[str, Any]:
        """Valores e fatos usados pela regra."""

    @property
    def explicacao(self) -> str:
        """Texto justificado pelo motor."""


class ComparacaoAchado(BaseModel):
    """Resultado de uma regra sobre uma parte, incluindo ausências e resultados inesperados."""

    validacao: str
    sujeito: str
    esperado: str | None
    obtido: str | None
    resultado_igual: bool
    valores_iguais: bool
    explicacao_igual: bool
    diferencas: list[str]


def _referenciar(valor: Any, referencias: Mapping[str, str]) -> Any:
    if isinstance(valor, dict):
        return {k: _referenciar(v, referencias) for k, v in valor.items()}
    if isinstance(valor, list | tuple):
        return [_referenciar(v, referencias) for v in valor]
    return referencias.get(valor, valor) if isinstance(valor, str) else valor


def _valores(
    achado: AchadoComparavel | None, referencias: Mapping[str, str]
) -> dict[str, Any] | None:
    if achado is None:
        return None
    por_fato = dict(referencias)
    fontes = []
    for fato in achado.valores.get("fatos", []):
        fonte = _referenciar(
            {k: v for k, v in fato.items() if k not in {"fato_id", "evidencia_ids"}}, referencias
        )
        fontes.append(fonte)
        if "fato_id" in fato:
            por_fato[fato["fato_id"]] = json.dumps(fonte, sort_keys=True, ensure_ascii=False)
    dados = _referenciar(achado.valores, por_fato)
    if "fatos" in dados:
        dados["fatos"] = sorted(fontes, key=lambda f: json.dumps(f, sort_keys=True))
    return dict(dados)


def _diferencas(esperado: Any, obtido: Any, caminho: str = "") -> list[str]:
    if isinstance(esperado, dict) and isinstance(obtido, dict):
        chaves = sorted(set(esperado) | set(obtido))
        return [
            d for k in chaves for d in _diferencas(esperado.get(k), obtido.get(k), f"{caminho}.{k}")
        ]
    return [caminho or "."] if esperado != obtido else []


def comparar(
    esperados: Sequence[ResultadoEsperado],
    obtidos: Iterable[AchadoComparavel],
    referencias_gabarito: Mapping[str, str] | None = None,
    referencias_banco: Mapping[str, str] | None = None,
) -> list[ComparacaoAchado]:
    """Compara cada regra por recorrente, com nomes e folhas comuns aos dois conjuntos.

    As chaves de evidência variam com os offsets da extração. Os campos tipo, valor e folhas
    de cada fato e a sequência dos fatos da cadeia de representação são confrontados.
    """
    gabarito = referencias_gabarito or {}
    banco = referencias_banco or {}
    esperados_por_parte = {(a.validacao, a.sujeito): a for a in esperados}
    obtidos_por_parte = {(a.validacao, banco.get(a.sujeito, a.sujeito)): a for a in obtidos}
    saida = []
    for nome, sujeito in sorted(esperados_por_parte.keys() | obtidos_por_parte.keys()):
        esperado = esperados_por_parte.get((nome, sujeito))
        obtido = obtidos_por_parte.get((nome, sujeito))
        diferencas = _diferencas(_valores(esperado, gabarito), _valores(obtido, banco))
        saida.append(
            ComparacaoAchado(
                validacao=nome,
                sujeito=sujeito,
                esperado=str(esperado.resultado) if esperado is not None else None,
                obtido=str(obtido.resultado) if obtido is not None else None,
                resultado_igual=esperado is not None
                and obtido is not None
                and esperado.resultado == obtido.resultado,
                valores_iguais=not diferencas,
                diferencas=diferencas[:10],
                explicacao_igual=esperado is not None
                and obtido is not None
                and esperado.explicacao == obtido.explicacao,
            )
        )
    return saida
