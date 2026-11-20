"""Arquivo enviado à espera do complemento de número ou classe (D16, A4 passos 4 a 8).

A API não guarda o arquivo quando faltam dados da identificação. O front o guarda no volume
`envios-pendentes` sob um código aleatório de 32 bytes, com o SHA-256 do cookie de sessão de quem
enviou; só essa sessão o recupera, por até 2 horas. O corpo dos pedidos grandes, que o Django
grava em temporário sob ASGI, também fica no volume, na subpasta `temporarios`.
"""

import hashlib
import json
import os
import re
import secrets
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

PASTA_PADRAO = "/var/lupa/envios-pendentes"
VALIDADE = timedelta(hours=2)
BYTES_DO_CODIGO = 32
FORMATO_DO_CODIGO = re.compile(r"[0-9a-f]{64}")
SUFIXO_DADOS = ".json"
SUFIXO_ARQUIVO = ".arquivo"
PASTA_TEMPORARIOS = "temporarios"
PERMISSAO_TEMPORARIOS = 0o700


@dataclass(frozen=True)
class Pendente:
    """Arquivo guardado, o nome original e a identificação incompleta devolvida pela API."""

    caminho: Path
    nome: str
    identificacao: dict[str, Any]


def pasta() -> Path:
    """Pasta dos pendentes, de `LUPA_WEB_ENVIOS_PENDENTES`.

    Returns:
        Caminho do volume `envios-pendentes`.
    """
    return Path(os.environ.get("LUPA_WEB_ENVIOS_PENDENTES", PASTA_PADRAO))


def preparar_temporarios() -> Path:
    """Cria `temporarios` no volume e a torna o diretório padrão do `tempfile` no processo.

    Returns:
        Caminho da subpasta.
    """
    destino = pasta() / PASTA_TEMPORARIOS
    destino.mkdir(mode=PERMISSAO_TEMPORARIOS, exist_ok=True)
    destino.chmod(PERMISSAO_TEMPORARIOS)
    tempfile.tempdir = str(destino)
    return destino


def _hash_da_sessao(cookie: str) -> str:
    return hashlib.sha256(cookie.encode()).hexdigest()


def _caminhos(codigo: str) -> tuple[Path, Path]:
    base = pasta()
    return base / f"{codigo}{SUFIXO_ARQUIVO}", base / f"{codigo}{SUFIXO_DADOS}"


def guardar(
    origem: Path,
    nome: str,
    cookie: str,
    agora: datetime,
    identificacao: dict[str, Any] | None = None,
) -> str:
    """Move o arquivo recebido para o volume e devolve o código do pendente.

    Args:
        origem: Arquivo temporário do envio.
        nome: Nome original do arquivo.
        cookie: Cookie de sessão de quem enviou.
        agora: Momento do envio.
        identificacao: Números e classe lidos e campos que faltam, para refazer o formulário.

    Returns:
        Código hexadecimal de 32 bytes.
    """
    codigo = secrets.token_hex(BYTES_DO_CODIGO)
    arquivo, dados = _caminhos(codigo)
    shutil.move(origem, arquivo)
    registro = {
        "nome": nome,
        "sessao": _hash_da_sessao(cookie),
        "criado_em": agora.isoformat(),
        "identificacao": identificacao or {},
    }
    dados.write_text(json.dumps(registro), encoding="utf-8")
    return codigo


def _ler(codigo: str) -> dict[str, Any] | None:
    if not FORMATO_DO_CODIGO.fullmatch(codigo):
        return None
    _, dados = _caminhos(codigo)
    if not dados.is_file():
        return None
    registro: dict[str, Any] = json.loads(dados.read_text(encoding="utf-8"))
    return registro


def _vencido(registro: dict[str, Any], agora: datetime) -> bool:
    return agora - datetime.fromisoformat(registro["criado_em"]) > VALIDADE


def recuperar(codigo: str, cookie: str, agora: datetime) -> Pendente | None:
    """O pendente do código, se existe, não venceu e é da mesma sessão.

    Args:
        codigo: Código devolvido por `guardar`.
        cookie: Cookie de sessão do pedido atual.
        agora: Momento do complemento.

    Returns:
        O pendente, ou `None`.
    """
    registro = _ler(codigo)
    if registro is None or not cookie or _vencido(registro, agora):
        return None
    if not secrets.compare_digest(registro["sessao"], _hash_da_sessao(cookie)):
        return None
    arquivo, _ = _caminhos(codigo)
    return Pendente(arquivo, registro["nome"], registro["identificacao"])


def apagar(codigo: str) -> None:
    """Remove o pendente do código, se houver.

    Args:
        codigo: Código do pendente.
    """
    if not FORMATO_DO_CODIGO.fullmatch(codigo):
        return
    for caminho in _caminhos(codigo):
        caminho.unlink(missing_ok=True)


def apagar_vencidos(agora: datetime) -> int:
    """Remove os pendentes com mais de 2 horas.

    Args:
        agora: Momento do envio novo.

    Returns:
        Quantos pendentes foram removidos.
    """
    removidos = 0
    for dados in pasta().glob(f"*{SUFIXO_DADOS}"):
        codigo = dados.name.removesuffix(SUFIXO_DADOS)
        registro = _ler(codigo)
        if registro is not None and _vencido(registro, agora):
            apagar(codigo)
            removidos += 1
    return removidos
