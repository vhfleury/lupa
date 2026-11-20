"""Cadastro e anexo por arquivo, com complemento de número e classe (RF-INT-04, A4, D14, D16).

O arquivo chega ao Django em arquivo temporário e segue em streaming para a API. Quando a API
pede número ou classe, o arquivo fica no volume de pendentes até o complemento.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from django.core.files.uploadedfile import TemporaryUploadedFile, UploadedFile
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from lupa_web import cliente_api, envios_pendentes, rotulos
from lupa_web.telas.sessao import Sessao, tela_autenticada

LIMITE_PADRAO = str(512 * 1024 * 1024)
TAMANHO_DO_BLOCO = 1024 * 1024
EXTENSOES = (".pdf", ".zip")
MOTIVO_INCOMPLETA = "identificacao_incompleta"
SEM_ARQUIVO = "Escolha um arquivo PDF ou ZIP."
TIPO_INVALIDO = "Envie um arquivo PDF ou ZIP."
VAZIO = "O arquivo está vazio."
ACIMA_DO_LIMITE = "O arquivo passa do limite de envio."
EXPIRADO = "Envio expirado, selecione o arquivo de novo."
FRAGMENTO = "processos/_envio_resultado.html"


def limite_de_envio() -> int:
    """Tamanho máximo do envio em bytes, o mesmo da API (D14).

    Returns:
        `LUPA_WEB_TAMANHO_MAXIMO_ENVIO`, padrão 512 MiB.
    """
    return int(os.environ.get("LUPA_WEB_TAMANHO_MAXIMO_ENVIO", LIMITE_PADRAO))


def problema_do_arquivo(arquivo: UploadedFile | None) -> str:
    """Motivo para recusar o arquivo antes de chamar a API (A4, passo 2).

    Args:
        arquivo: Arquivo recebido ou `None`.

    Returns:
        A frase do motivo, ou texto vazio se o arquivo pode seguir.
    """
    if arquivo is None:
        return SEM_ARQUIVO
    if not str(arquivo.name).lower().endswith(EXTENSOES):
        return TIPO_INVALIDO
    if not arquivo.size:
        return VAZIO
    if arquivo.size > limite_de_envio():
        return ACIMA_DO_LIMITE
    return ""


async def _blocos(caminho: Path) -> AsyncIterator[bytes]:
    with caminho.open("rb") as arquivo:
        while bloco := await asyncio.to_thread(arquivo.read, TAMANHO_DO_BLOCO):
            yield bloco


async def _repassar(
    request: HttpRequest, rota: str, caminho: Path, parametros: dict[str, str]
) -> httpx.Response:
    return await cliente_api.chamar(
        request,
        "POST",
        rota,
        longo=True,
        params=parametros,
        content=_blocos(caminho),
        headers={"Content-Type": "application/octet-stream"},
    )


def _fragmento(request: HttpRequest, contexto: dict[str, Any]) -> HttpResponse:
    return render(request, FRAGMENTO, contexto)


def _complemento(
    request: HttpRequest, codigo: str, corpo: dict[str, Any], erro: str = ""
) -> HttpResponse:
    lido = corpo.get("lido") or {}
    contexto = {
        "codigo": codigo,
        "faltando": corpo.get("faltando", []),
        "numero_lido": lido.get("numero_cnj") or "",
        "classe_lida": rotulos.CLASSES.get(lido.get("classe") or "", ""),
        "numeros_encontrados": corpo.get("numeros_encontrados", []),
        "classes": rotulos.CLASSES.items(),
        "erro": erro,
    }
    return _fragmento(request, contexto)


def _corpo(resposta: httpx.Response) -> dict[str, Any]:
    try:
        corpo = resposta.json()
    except ValueError:
        return {}
    return corpo if isinstance(corpo, dict) else {}


def _agora() -> datetime:
    return datetime.now(UTC)


def _concluir(
    request: HttpRequest,
    resposta: httpx.Response,
    caminho: Path,
    nome: str,
    pendente: envios_pendentes.Pendente | None = None,
    codigo: str = "",
) -> HttpResponse:
    corpo = _corpo(resposta)
    if not resposta.is_error:
        envios_pendentes.apagar(codigo)
        return cliente_api.redirecionar(request, f"/processos/{corpo['processo_id']}")
    if corpo.get("motivo") == MOTIVO_INCOMPLETA:
        if not codigo:
            sessao = request.COOKIES.get(cliente_api.NOME_COOKIE, "")
            codigo = envios_pendentes.guardar(caminho, nome, sessao, _agora(), corpo)
        return _complemento(request, codigo, corpo)
    erro = cliente_api.detalhe_do_erro(resposta)
    if pendente is not None and "motivo" not in corpo:
        return _complemento(request, codigo, pendente.identificacao, erro)
    envios_pendentes.apagar(codigo)
    return _fragmento(request, {"erro": erro})


async def _enviar_arquivo(request: HttpRequest, rota: str) -> HttpResponse:
    arquivo = request.FILES.get("arquivo")
    problema = problema_do_arquivo(arquivo)
    if problema or not isinstance(arquivo, TemporaryUploadedFile):
        return _fragmento(request, {"erro": problema or SEM_ARQUIVO})
    envios_pendentes.apagar_vencidos(_agora())
    caminho = Path(arquivo.temporary_file_path())
    nome = str(arquivo.name)
    resposta = await _repassar(request, rota, caminho, {"nome": nome})
    return _concluir(request, resposta, caminho, nome)


@require_POST
@tela_autenticada
async def novo(request: HttpRequest, sessao: Sessao) -> HttpResponse:
    """Cadastro de processo por arquivo: a API identifica número e classe (A4, passos 1 a 4).

    Args:
        request: Pedido HTMX multipart com `arquivo`.
        sessao: Dados da sessão.

    Returns:
        `HX-Redirect` para o processo, o formulário do complemento ou o motivo da recusa.
    """
    return await _enviar_arquivo(request, "/processos/arquivos")


@require_POST
@tela_autenticada
async def anexo(request: HttpRequest, sessao: Sessao, processo_id: str) -> HttpResponse:
    """Anexa um arquivo ao processo (A4, passo 3).

    Args:
        request: Pedido HTMX multipart com `arquivo`.
        sessao: Dados da sessão.
        processo_id: Identificador público do processo.

    Returns:
        `HX-Redirect` para o processo ou o motivo da recusa.
    """
    return await _enviar_arquivo(request, f"/processos/{processo_id}/arquivos")


@require_POST
@tela_autenticada
async def complemento(request: HttpRequest, sessao: Sessao) -> HttpResponse:
    """Reenvia o arquivo pendente com o número e a classe informados (A4, passos 5 a 8).

    Args:
        request: Pedido HTMX com `codigo`, `numero_cnj` e `classe`.
        sessao: Dados da sessão.

    Returns:
        `HX-Redirect` para o processo, o formulário com o erro, a recusa ou "envio expirado".
    """
    codigo = request.POST.get("codigo", "")
    cookie = request.COOKIES.get(cliente_api.NOME_COOKIE, "")
    pendente = envios_pendentes.recuperar(codigo, cookie, _agora())
    if pendente is None:
        return _fragmento(request, {"erro": EXPIRADO})
    parametros = {"nome": pendente.nome}
    for campo in ("numero_cnj", "classe"):
        valor = request.POST.get(campo, "").strip()
        if valor:
            parametros[campo] = valor
    resposta = await _repassar(request, "/processos/arquivos", pendente.caminho, parametros)
    return _concluir(request, resposta, pendente.caminho, pendente.nome, pendente, codigo)
