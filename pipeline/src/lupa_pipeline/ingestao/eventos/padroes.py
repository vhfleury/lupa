"""Padrões versionados dos marcos cíveis presentes nas peças."""

import re
from functools import cache
from importlib.resources import files
from typing import Any

import yaml

from lupa_pipeline.dominio.enums import TipoFato


@cache
def padroes() -> dict[str, Any]:
    """Carrega os gatilhos do pacote instalado."""
    arquivo = files("lupa_pipeline.ingestao").joinpath("dados", "eventos.yaml")
    dados: dict[str, Any] = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
    return dados


@cache
def gatilho(tipo: TipoFato) -> re.Pattern[str]:
    """Casa a menção imediatamente anterior à data, na mesma frase."""
    expressao = padroes()["datas"][tipo.value]
    return re.compile(r"(?:" + expressao + r")\b[^.\n;:\d]{0,55}(?::[ \t]*)?$")
