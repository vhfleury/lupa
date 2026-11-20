"""Painel "Início" na raiz, como a página `/` do SvelteKit (RF-INT-02, D17).

O assessor vê `GET /processos?meus=true`; o desembargador, todos os processos e a equipe de
`GET /usuarios`. Falha de uma das chamadas vira aviso e indicadores com "—".
"""

from typing import Any

import httpx
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from lupa_web import cliente_api, rotulos
from lupa_web.telas.sessao import ROTULO_PAPEL, Sessao, contexto_da_moldura, tela_autenticada, tem

SITUACOES_PENDENTES = ("pendencias", "falho", "quarentena")
TOTAL_RECENTES = 5
TOTAL_PENDENTES = 3


async def _listar(
    request: HttpRequest, nome: str, caminho: str, params: dict[str, str] | None = None
) -> tuple[list[dict[str, Any]] | None, str]:
    resposta: httpx.Response = await cliente_api.chamar(request, "GET", caminho, params=params)
    if resposta.is_error:
        return None, f"{nome}: {cliente_api.detalhe_do_erro(resposta)}"
    dados: list[dict[str, Any]] = resposta.json()
    return dados, ""


def item_do_painel(processo: dict[str, Any]) -> dict[str, Any]:
    """Processo com os rótulos usados nas listas do painel.

    Args:
        processo: Processo da lista da API.

    Returns:
        O processo com `classe_rotulo`, `criado_em_texto`, `situacao_rotulo` e `pendente`.
    """
    situacao = processo["ingestao"]["situacao"]
    return processo | {
        "classe_rotulo": rotulos.legivel(processo["classe"]),
        "criado_em_texto": rotulos.formatar_data(processo.get("criado_em")),
        "situacao_rotulo": rotulos.SITUACAO.get(situacao, situacao),
        "pendente": situacao in SITUACOES_PENDENTES,
    }


def resumo(processos: list[dict[str, Any]]) -> dict[str, Any]:
    """Indicadores, recentes e pendentes de uma lista de processos.

    Args:
        processos: Lista devolvida pela API.

    Returns:
        Contagens, os cinco mais recentes e os pendentes (até três exibidos).
    """
    itens = [item_do_painel(p) for p in processos]
    situacoes = [p["ingestao"]["situacao"] for p in processos]
    pendentes = [p for p in itens if p["pendente"]]
    return {
        "total": len(itens),
        "processando": situacoes.count("processando"),
        "concluidos": situacoes.count("concluido"),
        "pendentes": len(pendentes),
        "pendentes_exibidos": pendentes[:TOTAL_PENDENTES],
        "mais_pendentes": len(pendentes) > TOTAL_PENDENTES,
        "recentes": sorted(itens, key=lambda p: str(p["criado_em"]), reverse=True)[:TOTAL_RECENTES],
    }


@tela_autenticada
async def inicio(request: HttpRequest, sessao: Sessao) -> HttpResponse:
    """Painel com indicadores, processos recentes, atalhos e, ao desembargador, a equipe.

    Args:
        request: Pedido do navegador.
        sessao: Dados da sessão.

    Returns:
        Página do painel.
    """
    assessor = sessao.get("papel") == "assessor"
    erros: list[str] = []
    processos: list[dict[str, Any]] | None = None
    if tem(sessao, "ver_processo"):
        params = {"meus": "true"} if assessor else None
        processos, erro = await _listar(request, "Processos", "/processos", params)
        erros += [erro] if erro else []
    equipe: list[dict[str, Any]] | None = None
    if tem(sessao, "gerir_assessor"):
        usuarios, erro = await _listar(request, "Usuários", "/usuarios")
        erros += [erro] if erro else []
        equipe = None if usuarios is None else [u for u in usuarios if u["papel"] == "assessor"]
    contexto = contexto_da_moldura(request, sessao) | {
        "assessor": assessor,
        "papel_rotulo": ROTULO_PAPEL.get(str(sessao.get("papel")), ""),
        "erros": erros,
        "resumo": None if processos is None else resumo(processos),
        "equipe": equipe,
        "gere_usuarios": tem(sessao, "gerir_assessor"),
        "ve_auditoria": tem(sessao, "ver_auditoria"),
    }
    return render(request, "inicio.html", contexto)
