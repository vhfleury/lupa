"""Chave por hash, `hash_diff` e HMAC por processo do Data Vault (A1; D4, D5).

O `hk` de um hub é o SHA-256 das partes da chave de negócio, normalizadas e unidas por `|`; o de
um link, o SHA-256 dos hex dos `hk` dos hubs ligados, na ordem das colunas. O `hash_diff` de um
satélite é o SHA-256 do JSON canônico dos atributos ou, quando o satélite tem coluna cifrada, o
HMAC-SHA-256 com a DEK do processo, para que o hash não revele o texto por dicionário.
"""

import hashlib
import hmac
import json
import re
import unicodedata
from collections.abc import Collection, Mapping, Sequence
from datetime import UTC, date, datetime
from uuid import UUID

SEPARADOR = "|"
TAMANHO_HK = 32
TAMANHO_DEK = 32
NAO_DIGITO = re.compile(r"\D")


class ChaveInvalidaError(ValueError):
    """Chave de negócio sem partes, com parte vazia não permitida ou com o separador `|`."""


def normalizar_cnj(numero: str) -> str:
    """Deixa só os dígitos do número CNJ.

    Args:
        numero: Número com ou sem máscara.

    Returns:
        Os dígitos, na ordem.
    """
    return NAO_DIGITO.sub("", numero)


def normalizar_hash(texto: str) -> str:
    """Normaliza um hash hexadecimal para comparação e chave.

    Args:
        texto: Hash em qualquer caixa.

    Returns:
        O hash aparado e em minúsculas.
    """
    return texto.strip().lower()


def _como_texto(parte: object) -> str:
    if isinstance(parte, bytes):
        return parte.hex()
    return unicodedata.normalize("NFC", str(parte).strip())


def _validar(textos: list[str], vazias_permitidas: Collection[int]) -> None:
    if not textos:
        raise ChaveInvalidaError("chave de negócio sem partes")
    for posicao, texto in enumerate(textos):
        if not texto and posicao not in vazias_permitidas:
            raise ChaveInvalidaError(f"parte {posicao} vazia")
        if SEPARADOR in texto:
            raise ChaveInvalidaError(f"parte {posicao} contém '|'")


def chave_hash(partes: Sequence[object], vazias_permitidas: Collection[int] = ()) -> bytes:
    """Calcula o `hk` de um hub a partir das partes da chave de negócio (A1, passos 1 a 3).

    Cada parte vira texto aparado em NFC; `bytes` vira hex minúsculo. Normalizações próprias de
    uma coluna (número CNJ, hash) ficam com quem chama (`normalizar_cnj`, `normalizar_hash`).

    Args:
        partes: Partes da chave de negócio, na ordem das colunas do hub.
        vazias_permitidas: Posições que podem ser vazias (o `sujeito` de fato e achado).

    Returns:
        SHA-256 (32 bytes).

    Raises:
        ChaveInvalidaError: Sem partes, parte vazia fora das permitidas ou parte com `|`.
    """
    textos = [_como_texto(parte) for parte in partes]
    _validar(textos, vazias_permitidas)
    return hashlib.sha256(SEPARADOR.join(textos).encode()).digest()


def chave_link(*hks: bytes) -> bytes:
    """Calcula o `hk` de um link a partir dos `hk` dos hubs (A1, passo 4).

    Args:
        *hks: `hk` de cada hub, na ordem das colunas do link.

    Returns:
        SHA-256 dos hex unidos por `|` (32 bytes).

    Raises:
        ChaveInvalidaError: Sem `hk` ou `hk` sem 32 bytes.
    """
    if not hks or any(len(hk) != TAMANHO_HK for hk in hks):
        raise ChaveInvalidaError("link exige hk de 32 bytes")
    return hashlib.sha256(SEPARADOR.join(hk.hex() for hk in hks).encode()).digest()


def _canonico(valor: object) -> object:
    if isinstance(valor, datetime):
        return valor.astimezone(UTC).isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, bytes):
        return valor.hex()
    if isinstance(valor, UUID):
        return str(valor)
    raise TypeError(f"sem forma canônica: {type(valor).__name__}")


def json_canonico(atributos: Mapping[str, object]) -> bytes:
    """Serializa atributos em JSON com chaves ordenadas e sem espaços.

    Args:
        atributos: Atributos do satélite.

    Returns:
        JSON em UTF-8.

    Raises:
        TypeError: Valor sem forma canônica.
    """
    texto = json.dumps(
        atributos, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=_canonico
    )
    return texto.encode()


def hmac_processo(dek: bytes, texto: str) -> bytes:
    """HMAC-SHA-256 de um texto com a DEK do processo (`hub_parte.chave_nome`, D5).

    Args:
        dek: DEK do processo (32 bytes).
        texto: Texto já normalizado por quem chama.

    Returns:
        HMAC (32 bytes).

    Raises:
        ValueError: DEK sem 32 bytes.
    """
    return _hmac(dek, texto.encode())


def _hmac(dek: bytes, dados: bytes) -> bytes:
    if len(dek) != TAMANHO_DEK:
        raise ValueError("DEK sem 32 bytes")
    return hmac.new(dek, dados, hashlib.sha256).digest()


def hash_diff(atributos: Mapping[str, object], dek: bytes | None = None) -> bytes:
    """Calcula o `hash_diff` dos atributos de um satélite (A1, passo 5).

    Args:
        atributos: Atributos de negócio (sem `hk`, `load_dts`, `record_source`).
        dek: DEK do processo, quando o satélite tem coluna cifrada.

    Returns:
        SHA-256 do JSON canônico, ou HMAC-SHA-256 com a DEK (32 bytes).

    Raises:
        TypeError: Valor sem forma canônica.
        ValueError: DEK sem 32 bytes.
    """
    conteudo = json_canonico(atributos)
    if dek is None:
        return hashlib.sha256(conteudo).digest()
    return _hmac(dek, conteudo)
