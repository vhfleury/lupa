"""Padrões versionados dos marcos cíveis presentes nas peças."""

import re
from functools import cache
from typing import Any

from lupa_pipeline.dominio.enums import TipoFato
from lupa_pipeline.ingestao.datas import dobrar
from lupa_pipeline.ingestao.deteccao import ler_yaml


@cache
def padroes() -> dict[str, Any]:
    """Carrega os gatilhos do pacote instalado."""
    return ler_yaml("eventos.yaml")


@cache
def gatilho(tipo: TipoFato) -> re.Pattern[str]:
    """Casa a menção imediatamente anterior à data, na mesma frase."""
    expressao = padroes()["datas"][tipo.value]
    return re.compile(r"(?:" + expressao + r")\b[^.\n;:\d]{0,55}(?::[ \t]*)?$")


def rotulos_capa(campo: str) -> str:
    """Alternativas literais do campo, com o rótulo mais específico primeiro."""
    rotulos = sorted(padroes()["capa"][campo], key=len, reverse=True)
    return "|".join(re.escape(dobrar(rotulo)) for rotulo in rotulos)


@cache
def campo_capa(campo: str) -> re.Pattern[str]:
    """Captura o valor da linha rotulada no texto dobrado, mantendo os offsets originais."""
    alternativas = rotulos_capa(campo)
    return re.compile(
        rf"^[ \t]*(?:{alternativas})(?:[ \t]*:[ \t]*|[ \t]+)(?P<valor>\S[^\r\n]*?)" r"[ \t]*\r?$",
        re.MULTILINE,
    )
