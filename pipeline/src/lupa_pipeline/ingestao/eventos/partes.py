"""Reconhecimento de partes a partir das qualificações expressas (RF-FAT-04)."""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from lupa_pipeline.dominio.enums import Polo, QualidadeParte, TipoPeca
from lupa_pipeline.ingestao.eventos.modelo import PaginaTexto, PecaTexto
from lupa_pipeline.ingestao.texto import dobrar
from lupa_pipeline.validacoes.dados import dispensas_padrao

QUALIFICACAO = re.compile(
    r"(?im)^[ \t]*(autor(?:a)?|r[ée]u|r[ée]|apelante|apelad[oa]|agravante|agravad[oa]|"
    r"embargante|embargad[oa]|impetrante|impetrad[oa]|requerente|requerid[oa]|"
    r"recorrente|recorrid[oa]|terceir[oa](?: interessad[oa])?)\s*[:–-][ \t]*"
    r"(?P<nome>[^\n,;:]{2,160}?)(?=[ \t]*(?:[,;]|\.(?:\s|$)|$))"
)
ATIVO = frozenset(
    {
        "autor",
        "autora",
        "apelante",
        "agravante",
        "embargante",
        "impetrante",
        "requerente",
        "recorrente",
    }
)
TIPOS = frozenset(
    {
        TipoPeca.PETICAO_INICIAL,
        TipoPeca.SENTENCA,
        TipoPeca.ACORDAO,
        TipoPeca.APELACAO,
        TipoPeca.AGRAVO_INSTRUMENTO,
        TipoPeca.AGRAVO_INTERNO,
        TipoPeca.EMBARGOS_DECLARACAO,
    }
)


@dataclass(frozen=True)
class ParteExtraida:
    """Nome da parte e prova de sua posição processual."""

    nome: str
    polo: Polo
    qualidade: QualidadeParte
    pagina: PaginaTexto
    inicio: int
    fim: int


def chave_nome(nome: str) -> str:
    """Normaliza o nome para comparação e cálculo do HMAC por processo."""
    return " ".join(dobrar(nome).split())


def qualidade(nome: str) -> QualidadeParte:
    """Classifica apenas entidades identificadas pelo nome ou por qualificação inequívoca."""
    simples = chave_nome(nome).replace("_", " ")
    for codigo, dispensa in dispensas_padrao().dispensas.items():
        if chave_nome(dispensa.rotulo) in simples:
            return QualidadeParte(codigo)
    if re.match(r"^(?:municipio de |estado (?:de|do|da) |uniao(?: federal)?$)", simples):
        return QualidadeParte.FAZENDA_PUBLICA
    return QualidadeParte.PARTICULAR


def _trocar_outorgante(valor: Any, trocar: Callable[[str], str]) -> Any:
    """Aplica ``trocar`` ao outorgante de uma procuração; outro valor volta sem troca."""
    if not isinstance(valor, dict) or valor.get("tipo") != "procuracao":
        return valor
    outorgante = valor.get("outorgante")
    if not isinstance(outorgante, str):
        return valor
    return {**valor, "outorgante": trocar(outorgante)}


def nome_do_outorgante(valor: Any, nomes: Mapping[str, str]) -> Any:
    """Troca o código da parte outorgante pelo nome; código sem parte em ``nomes`` fica.

    Args:
        valor: Valor de um fato.
        nomes: Nome da parte por código.

    Returns:
        O valor com o nome do outorgante se for procuração; senão, o próprio valor
        (inclusive substabelecimento, cujo outorgante já traz nome e OAB).
    """
    return _trocar_outorgante(valor, lambda codigo: nomes.get(codigo, codigo))


def codigo_do_outorgante(valor: Any, sujeito: Callable[[str], str]) -> Any:
    """Troca o nome da parte outorgante pelo código calculado por ``sujeito``.

    Args:
        valor: Valor de um evento, com o nome literal do outorgante na procuração.
        sujeito: Função que calcula o código da parte a partir do nome.

    Returns:
        O valor com o código do outorgante se for procuração; senão, o próprio valor
        (inclusive substabelecimento, cujo outorgante já traz nome e OAB).
    """
    return _trocar_outorgante(valor, sujeito)


def extrair_partes(peca: PecaTexto) -> list[ParteExtraida]:
    """Lê qualificações literais nas peças previstas no A6."""
    if peca.tipo not in TIPOS:
        return []
    partes = []
    for pagina in peca.paginas:
        for m in QUALIFICACAO.finditer(pagina.normalizado):
            papel = dobrar(m[1])
            polo = Polo.ATIVO if papel in ATIVO else Polo.PASSIVO
            if papel.startswith("terceir"):
                polo = Polo.TERCEIRO
            nome = m["nome"].strip()
            a, b = m.span("nome")
            partes.append(ParteExtraida(nome, polo, qualidade(nome), pagina, a, b))
    return partes
