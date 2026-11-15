"""Carregamento e validação das fontes versionadas do catálogo cível."""

from datetime import date
from functools import lru_cache
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator

from lupa_pipeline.validacoes.calendario import Calendario, Periodo


class ArquivoVersionado(BaseModel):
    """Dados versionados com origem identificada."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    versao: str = Field(min_length=1)
    fonte: str = Field(min_length=1)


class Feriado(BaseModel):
    """Dia sem expediente no tribunal."""

    data: date
    descricao: str
    fonte: str | None = None


class ArquivoFeriados(ArquivoVersionado):
    """Lista de dias sem expediente na abrangência indicada."""

    abrangencia: str
    feriados: list[Feriado]


class Suspensao(BaseModel):
    """Período inclusivo de suspensão, com base legal."""

    inicio: date
    fim: date
    descricao: str
    base_legal: str
    anual: bool = False

    @model_validator(mode="after")
    def _validar_intervalo(self) -> Self:
        if self.fim < self.inicio:
            raise ValueError("fim da suspensão anterior ao início")
        return self


class ArquivoSuspensoes(ArquivoVersionado):
    """Suspensões de prazos processuais."""

    suspensoes: list[Suspensao]


class RegraRecurso(BaseModel):
    """Regra de prazo de um recurso cível."""

    nome: str
    dias: PositiveInt
    base_legal: str


class TabelaPrazosRecursos(ArquivoVersionado):
    """Prazos, regra de contagem e hipóteses de prazo em dobro."""

    contagem_base_legal: str
    multiplicador_dobro: PositiveInt
    dobra: dict[str, str]
    recursos: dict[str, RegraRecurso]


class TabelaPreparo(ArquivoVersionado):
    """Qualidades do recorrente dispensadas, na especificação, de preparo e mandato."""

    dispensas: dict[str, str]


class TabelaCabimento(ArquivoVersionado):
    """Hipóteses da tabela de conferência de cabimento."""

    incisos: dict[str, str]


def caminho_padrao(relativo: str) -> Traversable:
    """Localiza um arquivo no diretório de dados jurídicos versionados."""
    return files("lupa_pipeline.validacoes").joinpath("dados", *relativo.split("/"))


def carregar[M: ArquivoVersionado](origem: Traversable | Path, modelo: type[M]) -> M:
    """Lê YAML e exige os campos e tipos do contrato."""
    return modelo.model_validate(yaml.safe_load(origem.read_text(encoding="utf-8")))


def montar_calendario(feriados: list[ArquivoFeriados], suspensoes: ArquivoSuspensoes) -> Calendario:
    """Indexa os dias sem expediente preservando a fonte de cada ocorrência."""
    dias = {f.data: f.descricao for arq in feriados for f in arq.feriados}
    fontes = {f.data: f.fonte or arq.fonte for arq in feriados for f in arq.feriados}
    periodos = tuple(
        Periodo(s.inicio, s.fim, s.descricao, s.base_legal, s.anual) for s in suspensoes.suspensoes
    )
    return Calendario(feriados=dias, suspensoes=periodos, fontes=fontes)


@lru_cache(maxsize=1)
def calendario_padrao() -> tuple[Calendario, dict[str, str]]:
    """Calendário do tribunal e versões dos dados usados."""
    nacionais = carregar(caminho_padrao("feriados/nacionais.yaml"), ArquivoFeriados)
    tribunal = carregar(caminho_padrao("feriados/tjgo.yaml"), ArquivoFeriados)
    suspensoes = carregar(caminho_padrao("suspensoes_prazo.yaml"), ArquivoSuspensoes)
    versoes = {
        "feriados/nacionais.yaml": nacionais.versao,
        "feriados/tjgo.yaml": tribunal.versao,
        "suspensoes_prazo.yaml": suspensoes.versao,
    }
    return montar_calendario([nacionais, tribunal], suspensoes), versoes


@lru_cache(maxsize=1)
def prazos_recursos_padrao() -> TabelaPrazosRecursos:
    """Tabela dos prazos do CPC."""
    return carregar(caminho_padrao("prazos_recursos.yaml"), TabelaPrazosRecursos)


@lru_cache(maxsize=1)
def preparo_padrao() -> TabelaPreparo:
    """Tabela das dispensas previstas para o gabinete."""
    return carregar(caminho_padrao("preparo.yaml"), TabelaPreparo)


@lru_cache(maxsize=1)
def cabimento_padrao() -> TabelaCabimento:
    """Tabela das hipóteses de agravo de instrumento."""
    return carregar(caminho_padrao("cabimento_art1015.yaml"), TabelaCabimento)
