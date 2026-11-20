"""Tela do processo: arquivos com diagnóstico e alertas, responsáveis, classe e descarte.

Cada ação é um formulário POST que chama a rota da API e volta à tela do processo; a API
reconfere o papel em toda chamada (RF-INT-02).
"""

from typing import Any

import httpx
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from lupa_web import cliente_api, rotulos
from lupa_web.telas.dossie import capa
from lupa_web.telas.envio import limite_de_envio
from lupa_web.telas.sessao import (
    Sessao,
    contexto_da_moldura,
    nao_encontrado,
    obter,
    tela_autenticada,
    tem,
)

UNIDADES = ("B", "KB", "MB", "GB")
BYTES_POR_UNIDADE = 1024
MENSAGEM_RESPONSAVEIS = (
    "Responsáveis atualizados. O processo aparece na área de trabalho de cada assessor selecionado."
)
MENSAGEM_SEM_DIAGNOSTICO = "Diagnóstico ainda não disponível."


def formatar_bytes(tamanho: int | None) -> str:
    """Tamanho legível em B, KB, MB ou GB.

    Args:
        tamanho: Bytes ou `None`.

    Returns:
        Texto como `1,5 MB`, ou "—".
    """
    if tamanho is None:
        return rotulos.SEM_VALOR
    if tamanho < BYTES_POR_UNIDADE:
        return f"{tamanho} B"
    valor = tamanho / BYTES_POR_UNIDADE
    for unidade in UNIDADES[1:-1]:
        if valor < BYTES_POR_UNIDADE:
            return f"{valor:.1f} {unidade}".replace(".", ",")
        valor /= BYTES_POR_UNIDADE
    return f"{valor:.1f} {UNIDADES[-1]}".replace(".", ",")


def detalhe_do_estado(arquivo: dict[str, Any]) -> str:
    """Explicação do estado de um arquivo em quarentena, parcial ou com falha.

    Args:
        arquivo: Arquivo de `GET /processos/<id>/arquivos`.

    Returns:
        A frase do motivo, as páginas faltantes ou texto vazio.
    """
    estado = arquivo.get("estado")
    if estado == "quarentena":
        return rotulos.motivo_quarentena(arquivo.get("motivo_quarentena"))
    if estado == "falho":
        return rotulos.motivo_falha(arquivo.get("motivo_falha"))
    faltantes = (arquivo.get("relatorio") or {}).get("faltantes") or []
    if estado == "parcial" and faltantes:
        return "Páginas faltantes: " + ", ".join(str(p) for p in faltantes)
    return ""


def linha_do_arquivo(arquivo: dict[str, Any]) -> dict[str, Any]:
    """Dados de uma linha da tabela de arquivos.

    Args:
        arquivo: Arquivo da API.

    Returns:
        O arquivo com rótulos, tamanho, data, detalhe do estado e se a página abre no visualizador.
    """
    estado = arquivo.get("estado")
    return arquivo | {
        "estado_rotulo": rotulos.ESTADO_JOB.get(estado or "", estado or rotulos.SEM_VALOR),
        "tamanho_texto": formatar_bytes(arquivo.get("tamanho_bytes")),
        "enviado_em_texto": rotulos.formatar_data(arquivo.get("enviado_em")),
        "detalhe": detalhe_do_estado(arquivo),
        "legivel": bool(arquivo.get("total_paginas")) and estado in {"concluido", "em_revisao"},
    }


def contexto_do_estado(processo_id: str, arquivos: dict[str, Any]) -> dict[str, Any]:
    """Contexto do fragmento de estado dos arquivos (A4, passo 9).

    Args:
        processo_id: Identificador público do processo.
        arquivos: Corpo de `GET /processos/<id>/arquivos`.

    Returns:
        Situação, linhas dos arquivos e `pendente`, verdadeiro com arquivo fora do estado final.
    """
    linhas = [linha_do_arquivo(a) for a in arquivos["arquivos"]]
    return {
        "processo_id": processo_id,
        "situacao_rotulo": rotulos.SITUACAO.get(arquivos["situacao"], arquivos["situacao"]),
        "arquivos": linhas,
        "pendente": any(
            a.get("estado") and a["estado"] not in rotulos.ESTADOS_FINAIS for a in linhas
        ),
    }


async def _contexto_do_processo(
    request: HttpRequest, sessao: Sessao, processo_id: str
) -> dict[str, Any] | None:
    base = f"/processos/{processo_id}"
    resposta = await obter(request, base)
    if resposta.status_code == httpx.codes.NOT_FOUND:
        return None
    processo: dict[str, Any] = resposta.json()
    arquivos = (await obter(request, f"{base}/arquivos")).json()
    responsaveis = (await obter(request, f"{base}/responsaveis")).json()
    ativo = processo["status"] != "descartado"
    ficha = None
    if ativo:
        dossie = await obter(request, f"{base}/dossie")
        ficha = None if dossie.is_error else capa(processo_id, dossie.json()["ficha"])
    vigentes = {u["id"] for u in responsaveis["responsaveis"]}
    return contexto_da_moldura(request, sessao) | {
        "processo": processo,
        "classe_rotulo": rotulos.CLASSES.get(processo["classe"], processo["classe"]),
        "status_rotulo": rotulos.legivel(processo["status"]),
        "classe_anterior_rotulo": rotulos.CLASSES.get(processo.get("classe_anterior") or "", ""),
        "classe_corrigida_em_texto": rotulos.formatar_data(processo.get("classe_corrigida_em")),
        "classes": rotulos.CLASSES.items(),
        "capa": ficha,
        **contexto_do_estado(processo_id, arquivos),
        "responsaveis": responsaveis["responsaveis"],
        "disponiveis": [u | {"marcado": u["id"] in vigentes} for u in responsaveis["disponiveis"]],
        "pode_gerir": responsaveis["pode_gerir"] and tem(sessao, "gerir_assessor"),
        "pode_corrigir": ativo and tem(sessao, "anotar"),
        "pode_descartar": ativo and tem(sessao, "ver_auditoria"),
        "pode_enviar": ativo and tem(sessao, "subir_processo"),
        "acao_anexo": f"{base}/envio",
        "limite_envio": formatar_bytes(limite_de_envio()),
    }


async def _pagina(
    request: HttpRequest,
    sessao: Sessao,
    processo_id: str,
    mensagens: dict[str, str] | None = None,
    status: int = 200,
) -> HttpResponse:
    contexto = await _contexto_do_processo(request, sessao, processo_id)
    if contexto is None:
        return nao_encontrado(request, sessao)
    contexto |= mensagens or {}
    return render(request, "processos/processo.html", contexto, status=status)


@require_GET
@tela_autenticada
async def processo(request: HttpRequest, sessao: Sessao, processo_id: str) -> HttpResponse:
    """Tela do processo, com as ações que o papel permite.

    Args:
        request: Pedido do navegador; `?aviso=responsaveis` mostra a confirmação da distribuição.
        sessao: Dados da sessão.
        processo_id: Identificador público do processo.

    Returns:
        Página do processo, ou 404 se a API não o encontra.
    """
    aviso = MENSAGEM_RESPONSAVEIS if request.GET.get("aviso") == "responsaveis" else ""
    return await _pagina(request, sessao, processo_id, {"aviso": aviso})


async def _acao(
    request: HttpRequest,
    sessao: Sessao,
    processo_id: str,
    caminho: str,
    corpo: dict[str, Any],
    destino: str,
) -> HttpResponse:
    resposta = await cliente_api.chamar(request, "POST", caminho, json=corpo)
    if resposta.is_error:
        erro = cliente_api.detalhe_do_erro(resposta)
        return await _pagina(request, sessao, processo_id, {"erro": erro}, resposta.status_code)
    return cliente_api.redirecionar(request, destino)


@require_POST
@tela_autenticada
async def corrigir_classe(request: HttpRequest, sessao: Sessao, processo_id: str) -> HttpResponse:
    """Corrige a classe do processo (RF-PRO-06) e volta à tela.

    Args:
        request: Pedido com `classe`.
        sessao: Dados da sessão.
        processo_id: Identificador público do processo.

    Returns:
        Redirecionamento à tela do processo, ou a tela com o erro da API.
    """
    base = f"/processos/{processo_id}"
    corpo = {"classe": request.POST.get("classe", "")}
    return await _acao(request, sessao, processo_id, f"{base}/classe", corpo, base)


@require_POST
@tela_autenticada
async def distribuir(request: HttpRequest, sessao: Sessao, processo_id: str) -> HttpResponse:
    """Define os assessores responsáveis (RF-PRO-03) e volta à tela com a confirmação.

    Args:
        request: Pedido com `usuarios` marcados e `anteriores` conhecidos.
        sessao: Dados da sessão.
        processo_id: Identificador público do processo.

    Returns:
        Redirecionamento à tela do processo, ou a tela com o erro da API.
    """
    base = f"/processos/{processo_id}"
    corpo = {
        "usuarios": request.POST.getlist("usuarios"),
        "anteriores": request.POST.getlist("anteriores"),
    }
    destino = f"{base}?aviso=responsaveis"
    return await _acao(request, sessao, processo_id, f"{base}/responsaveis", corpo, destino)


@require_http_methods(["GET", "POST"])
@tela_autenticada
async def descartar(request: HttpRequest, sessao: Sessao, processo_id: str) -> HttpResponse:
    """Confirmação e descarte do processo pelo desembargador (A13 da API).

    Args:
        request: GET mostra a confirmação; POST descarta.
        sessao: Dados da sessão.
        processo_id: Identificador público do processo.

    Returns:
        Página de confirmação, redirecionamento à lista ou a tela com o erro da API.
    """
    base = f"/processos/{processo_id}"
    if request.method == "POST":
        return await _acao(request, sessao, processo_id, f"{base}/descartar", {}, "/processos")
    resposta = await obter(request, base)
    if resposta.status_code == httpx.codes.NOT_FOUND:
        return nao_encontrado(request, sessao)
    contexto = contexto_da_moldura(request, sessao) | {
        "processo": resposta.json(),
        "titulo": "Descartar processo",
        "mensagem": (
            "O processo, os arquivos e os resultados da análise serão descartados. "
            "Esta ação não pode ser desfeita."
        ),
        "rotulo_confirmar": "Descartar processo",
        "perigo": True,
        "acao": f"{base}/descartar",
        "voltar": base,
    }
    return render(request, "processos/descartar.html", contexto)


@require_GET
@tela_autenticada
async def arquivo(
    request: HttpRequest, sessao: Sessao, processo_id: str, arquivo_id: str
) -> HttpResponse:
    """Relatório, diagnóstico e alertas de um arquivo do processo (RF-ING-03, 05 e 06).

    Args:
        request: Pedido do navegador.
        sessao: Dados da sessão.
        processo_id: Identificador público do processo.
        arquivo_id: Identificador público do arquivo.

    Returns:
        Página do arquivo, ou 404 se a API não o encontra.
    """
    base = f"/processos/{processo_id}/arquivos/{arquivo_id}"
    relatorio = await obter(request, f"{base}/relatorio")
    if relatorio.status_code == httpx.codes.NOT_FOUND:
        return nao_encontrado(request, sessao)
    diagnostico = await obter(request, f"{base}/diagnostico")
    alertas = (await obter(request, f"{base}/alertas")).json()
    dados_relatorio = relatorio.json()
    estado = dados_relatorio.get("estado") or ""
    sem_id = frozenset({"arquivo_id"})
    contexto = contexto_da_moldura(request, sessao) | {
        "processo_id": processo_id,
        "estado_rotulo": rotulos.ESTADO_JOB.get(estado, estado or rotulos.SEM_VALOR),
        "versao_extrator": dados_relatorio.get("versao_extrator") or rotulos.SEM_VALOR,
        "relatorio": rotulos.pares(dados_relatorio.get("relatorio")),
        "diagnostico": None if diagnostico.is_error else rotulos.pares(diagnostico.json(), sem_id),
        "sem_diagnostico": MENSAGEM_SEM_DIAGNOSTICO,
        "resumo_alertas": rotulos.pares(alertas.get("resumo")),
        "paginas_alertas": [
            {"numero": p["numero"], "flags": ", ".join(rotulos.legivel(f) for f in p["flags"])}
            for p in alertas.get("paginas", [])
        ],
        "metadados_suspeitos": [rotulos.pares(m) for m in alertas.get("metadados_suspeitos", [])],
    }
    return render(request, "processos/arquivo.html", contexto)


@require_GET
@tela_autenticada
async def estado(request: HttpRequest, sessao: Sessao, processo_id: str) -> HttpResponse:
    """Fragmento HTMX com o estado dos arquivos; repete a cada 5 s até o estado final (A4.9).

    Args:
        request: Pedido HTMX.
        sessao: Dados da sessão.
        processo_id: Identificador público do processo.

    Returns:
        Fragmento da tabela de arquivos.
    """
    arquivos = (await obter(request, f"/processos/{processo_id}/arquivos")).json()
    return render(request, "processos/_estado.html", contexto_do_estado(processo_id, arquivos))
