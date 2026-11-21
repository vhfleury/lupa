"""Funções de texto da ingestão: dobramento, distância de edição e normalizações."""

import re
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


def levenshtein(a: str, b: str) -> int:
    """Distância de edição (inserção, remoção, substituição), em Python puro.

    Prefixo e sufixo comuns são descartados antes da programação dinâmica.

    Args:
        a: Primeiro texto.
        b: Segundo texto.

    Returns:
        Número mínimo de edições.
    """
    inicio = 0
    while inicio < min(len(a), len(b)) and a[inicio] == b[inicio]:
        inicio += 1
    a, b = a[inicio:], b[inicio:]
    while a and b and a[-1] == b[-1]:
        a, b = a[:-1], b[:-1]
    if len(a) < len(b):
        a, b = b, a
    anterior = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        atual = [i]
        for j, cb in enumerate(b, start=1):
            atual.append(min(anterior[j] + 1, atual[j - 1] + 1, anterior[j - 1] + (ca != cb)))
        anterior = atual
    return anterior[-1]


def colapsar_espacos(texto: str) -> str:
    """Texto na forma NFC com espaços e quebras de linha colapsados em um espaço.

    Args:
        texto: Texto livre.

    Returns:
        Texto sem espaços nas pontas e com um espaço entre palavras.
    """
    return " ".join(unicodedata.normalize("NFC", texto).split())


def maiusculas_sem_acento(texto: str) -> str:
    """Maiúsculas, sem acento e sem pontuação, com espaços simples.

    Args:
        texto: Texto livre.

    Returns:
        Texto só com letras ASCII maiúsculas, dígitos, barra e espaços simples.
    """
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    limpo = re.sub(r"[^A-Za-z0-9/ ]+", " ", sem_acento)
    return " ".join(limpo.upper().split())
