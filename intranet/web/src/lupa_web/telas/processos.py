"""Lista de processos renderizada a partir de `GET /processos` (RF-INT-01, RF-INT-02).

Os filtros (busca, situação e responsável) vêm do formulário GET e são aplicados no servidor.
"""

from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from lupa_web import cliente_api, rotulos
from lupa_web.telas.sessao import Sessao, contexto_da_moldura, tela_autenticada, tem

SEM_RESPONSAVEL = "sem"


def _texto_de_busca(processo: dict[str, Any]) -> str:
    nomes = " ".join(u["nome_usuario"] for u in processo.get("responsaveis", []))
    classe = rotulos.CLASSES.get(processo["classe"], processo["classe"])
    return f"{processo['numero_cnj']} {classe} {nomes}".casefold()


def _atende(processo: dict[str, Any], busca: str, situacao: str, responsavel: str) -> bool:
    responsaveis = {u["id"] for u in processo.get("responsaveis", [])}
    if busca and busca.casefold() not in _texto_de_busca(processo):
        return False
    if situacao and processo["ingestao"]["situacao"] != situacao:
        return False
    if responsavel == SEM_RESPONSAVEL:
        return not responsaveis
    return not responsavel or responsavel in responsaveis


def filtrar(processos: list[dict[str, Any]], filtros: dict[str, str]) -> list[dict[str, Any]]:
    """Processos que atendem a todos os filtros informados.

    Args:
        processos: Lista devolvida pela API.
        filtros: `busca`, `situacao` e `responsavel` (vazio é "todos").

    Returns:
        Os processos filtrados, na ordem da API.
    """
    return [
        p
        for p in processos
        if _atende(p, filtros["busca"], filtros["situacao"], filtros["responsavel"])
    ]


def assessores_da_lista(processos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Responsáveis que aparecem na lista, sem repetição, em ordem de nome.

    Args:
        processos: Lista devolvida pela API.

    Returns:
        Usuários `{id, nome_usuario, ativo}`.
    """
    por_id = {u["id"]: u for p in processos for u in p.get("responsaveis", [])}
    return sorted(por_id.values(), key=lambda u: str(u["nome_usuario"]))


def linha(processo: dict[str, Any]) -> dict[str, Any]:
    """Dados de uma linha da tabela, com rótulos e data formatados.

    Args:
        processo: Processo da lista da API.

    Returns:
        O processo com `classe_rotulo`, `situacao`, `situacao_rotulo` e `criado_em_texto`.
    """
    situacao = processo["ingestao"]["situacao"]
    return processo | {
        "classe_rotulo": rotulos.CLASSES.get(processo["classe"], processo["classe"]),
        "situacao": situacao,
        "situacao_rotulo": rotulos.SITUACAO.get(situacao, situacao),
        "criado_em_texto": rotulos.formatar_data(processo.get("criado_em")),
    }


@tela_autenticada
async def lista(request: HttpRequest, sessao: Sessao) -> HttpResponse:
    """Tela da lista de processos com filtros.

    Args:
        request: Pedido do navegador, com os filtros na consulta.
        sessao: Dados da sessão.

    Returns:
        Página da lista.
    """
    resposta = await cliente_api.chamar(request, "GET", "/processos")
    processos: list[dict[str, Any]] = resposta.json()
    filtros = {campo: request.GET.get(campo, "").strip() for campo in ("busca", "situacao")}
    filtros["responsavel"] = request.GET.get("responsavel", "")
    filtrados = filtrar(processos, filtros)
    contexto = contexto_da_moldura(request, sessao) | {
        "processos": [linha(p) for p in filtrados],
        "total": len(processos),
        "filtros": filtros,
        "situacoes": rotulos.SITUACAO.items(),
        "assessores": assessores_da_lista(processos),
        "pode_criar": tem(sessao, "subir_processo"),
        "processando": any(p["ingestao"]["situacao"] == "processando" for p in processos),
    }
    return render(request, "processos/lista.html", contexto)
