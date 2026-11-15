"""Tabela de validações aplicáveis a cada classe processual (RF-VAL-01)."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date

from lupa_pipeline.validacoes.civel import cabimento, preparo, representacao, tempestividade
from lupa_pipeline.validacoes.modelo import AchadoValidacao, ModeloProcesso
from lupa_pipeline.validacoes.versao import VERSAO_CATALOGO

__all__ = ["CATALOGO", "VERSAO_CATALOGO", "Validacao", "validacoes_de"]


@dataclass(frozen=True)
class Validacao:
    """Regra de conferência e base jurídica do achado."""

    nome: str
    base_legal: str
    executar: Callable[[ModeloProcesso, date], AchadoValidacao]


TEMPESTIVIDADE = Validacao(tempestividade.NOME, tempestividade.BASE_LEGAL, tempestividade.executar)
PREPARO = Validacao(preparo.NOME, preparo.BASE_LEGAL, preparo.executar)
REPRESENTACAO = Validacao(representacao.NOME, representacao.BASE_LEGAL, representacao.executar)
CABIMENTO = Validacao(cabimento.NOME, cabimento.BASE_LEGAL, cabimento.executar)
REGRAS_COM_PREPARO = (TEMPESTIVIDADE, PREPARO, REPRESENTACAO)
CATALOGO: Mapping[str, tuple[Validacao, ...]] = {
    "apelacao_civel": REGRAS_COM_PREPARO,
    "agravo_instrumento": (*REGRAS_COM_PREPARO, CABIMENTO),
    "embargos_declaracao": (TEMPESTIVIDADE, REPRESENTACAO),
    "agravo_interno": REGRAS_COM_PREPARO,
    "acao_originaria": (),
}


def validacoes_de(classe: str) -> tuple[Validacao, ...]:
    """Devolve as regras da classe em ordem ou recusa uma classe desconhecida."""
    try:
        return CATALOGO[classe]
    except KeyError as erro:
        raise ValueError(f"classe desconhecida: {classe}") from erro
