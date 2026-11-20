"""Matriz de permissões por papel, como dados (seção 2 da especificação; RF-ACE-03).

Há dois papéis e um gabinete só: a permissão vale para todos os processos e usuários. A
verificação fica em `tem_permissao`; nenhum outro módulo decide por `if` de papel.
"""

from enum import StrEnum
from types import MappingProxyType
from typing import Final

from lupa_pipeline.dominio.enums import PapelUsuario


class Permissao(StrEnum):
    """Ações sujeitas a autorização."""

    VER_PROCESSO = "ver_processo"
    SUBIR_PROCESSO = "subir_processo"
    ANOTAR = "anotar"
    VER_AUDITORIA = "ver_auditoria"
    GERIR_ASSESSOR = "gerir_assessor"
    RESETAR_ASSESSOR = "resetar_assessor"


_ASSESSOR = frozenset({Permissao.VER_PROCESSO, Permissao.SUBIR_PROCESSO, Permissao.ANOTAR})
_DESEMBARGADOR = _ASSESSOR | {
    Permissao.VER_AUDITORIA,
    Permissao.GERIR_ASSESSOR,
    Permissao.RESETAR_ASSESSOR,
}

MATRIZ: Final = MappingProxyType(
    {PapelUsuario.ASSESSOR: _ASSESSOR, PapelUsuario.DESEMBARGADOR: _DESEMBARGADOR}
)


def tem_permissao(papel: PapelUsuario, permissao: Permissao) -> bool:
    """Diz se o papel tem a permissão.

    Args:
        papel: Papel do usuário.
        permissao: Ação desejada.

    Returns:
        Verdadeiro se a matriz concede a permissão.
    """
    return permissao in MATRIZ[papel]
