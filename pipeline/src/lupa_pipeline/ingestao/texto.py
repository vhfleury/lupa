"""Dobramento de texto da ingestão: minúsculas sem acento, com o comprimento preservado."""

import unicodedata


def dobrar(texto: str) -> str:
    """Minúsculas sem acento, preservando o comprimento (um caractere por caractere).

    Args:
        texto: Texto (normalmente o normalizado).

    Returns:
        Texto dobrado do mesmo tamanho.
    """
    return "".join(_dobrar_caractere(c) for c in texto)


def _dobrar_caractere(caractere: str) -> str:
    base = unicodedata.normalize("NFD", caractere)[:1] or caractere
    minuscula = base.lower()
    return minuscula if len(minuscula) == 1 else base
