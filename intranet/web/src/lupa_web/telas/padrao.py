"""Página `/padrao`: catálogo de componentes com dados sintéticos (RF-VIS-05, A1).

Só existe com `LUPA_AMBIENTE=desenvolvimento`; em qualquer outro ambiente responde 404 antes de
consultar a sessão na API. No desenvolvimento exige sessão, como as demais telas.
"""

import os
from typing import Any

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

from lupa_web.telas.sessao import Sessao, contexto_da_moldura, tela_autenticada

AMBIENTE_DO_PADRAO = "desenvolvimento"

EXEMPLOS: dict[str, Any] = {
    "colunas": ["Processo", "Classe", "Recebido em", "Situação"],
    "linhas": [
        [
            {"texto": "0000001-00.2026.8.07.0001", "href": "/padrao"},
            "Apelação cível",
            "01/03/2026",
            "Concluído",
        ],
        [
            {"texto": "0000002-00.2026.8.07.0001", "href": "/padrao"},
            "Agravo de instrumento",
            "03/03/2026 — com observação longa para forçar a rolagem da tabela em telas estreitas",
            "Processando",
        ],
    ],
    "campos_da_acao": [
        {
            "rotulo": "Classe correta",
            "nome": "classe",
            "id_campo": "padrao-classe",
            "tipo": "select",
            "valor": "apelacao_civel",
            "opcoes": [
                {"valor": "apelacao_civel", "rotulo": "Apelação cível"},
                {"valor": "agravo_de_instrumento", "rotulo": "Agravo de instrumento"},
            ],
        },
        {
            "rotulo": "Motivo",
            "nome": "motivo",
            "id_campo": "padrao-motivo",
            "tipo": "textarea",
            "dica": "Texto sintético de exemplo.",
        },
    ],
    "opcoes_papel": [
        {"valor": "assessor", "rotulo": "Assessor"},
        {"valor": "desembargador", "rotulo": "Desembargador"},
    ],
    "selos": [
        {"tom": "sucesso", "texto": "Tempestiva", "detalhe": "interposta no 10º dia útil"},
        {"tom": "atencao", "texto": "Verificar", "detalhe": "guia de preparo ilegível"},
        {"tom": "falha", "texto": "Deserta", "detalhe": "preparo não comprovado"},
    ],
    "badges": ["Na fila", "Processando", "Concluído", "Em revisão", "Assessor"],
}


async def padrao(request: HttpRequest) -> HttpResponse:
    """Responde 404 fora do desenvolvimento; no desenvolvimento, o catálogo autenticado.

    Args:
        request: Pedido do navegador.

    Returns:
        Página do catálogo.

    Raises:
        Http404: `LUPA_AMBIENTE` diferente de `desenvolvimento`.
    """
    if os.environ.get("LUPA_AMBIENTE") != AMBIENTE_DO_PADRAO:
        raise Http404
    return await _catalogo(request)


@tela_autenticada
async def _catalogo(request: HttpRequest, sessao: Sessao) -> HttpResponse:
    contexto = contexto_da_moldura(request, sessao) | EXEMPLOS
    return render(request, "padrao.html", contexto)
