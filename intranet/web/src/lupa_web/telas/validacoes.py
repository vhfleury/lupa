"""Validações do processo: achados, fatos com confirmação e correção, anotações e histórico.

Cada valor do achado que é data ou identificador vira link para a evidência (RF-INT-05); a
confirmação, a correção e a anotação são formulários POST que chamam a API e voltam à tela.
"""

import json
import re
from typing import Any

from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from lupa_web import cliente_api, rotulos
from lupa_web.telas.dossie import link_da_evidencia
from lupa_web.telas.sessao import (
    Sessao,
    contexto_da_moldura,
    nao_encontrado,
    obter,
    tela_autenticada,
    tem,
)

DATA_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
ID_PUBLICO = re.compile(r"[0-9a-fA-F]{64}")
COLUNAS_HISTORICO = ("Validação", "Resultado", "Explicação", "Gravado em")
MENSAGEM_FONTE = "Informe a página, o intervalo e o trecho da correção."
AVISOS = {"confirmado": "Fato confirmado.", "anotacao": "Anotação registrada."}

Fato = dict[str, Any]


class Indices:
    """Fatos por id e evidências por página, para ligar os valores do achado às fontes."""

    def __init__(self, processo_id: str, fatos: list[Fato]) -> None:
        """Monta os índices.

        Args:
            processo_id: Identificador público do processo.
            fatos: Fatos vigentes de `GET /processos/<id>/fatos`.
        """
        self.processo_id = processo_id
        self.por_id = {fato["id"]: fato for fato in fatos}
        self.por_pagina = {ev["pagina_id"]: ev for fato in fatos for ev in fato["evidencias"]}

    def link_do_fato(self, fato: Fato | None) -> str:
        """Link da primeira evidência do fato.

        Args:
            fato: Fato ou `None`.

        Returns:
            Caminho do visualizador, ou texto vazio sem evidência.
        """
        if not fato or not fato["evidencias"]:
            return ""
        return link_da_evidencia(self.processo_id, fato["evidencias"][0]["id"])

    def fato_da_data(self, achado: dict[str, Any], chave: str, data: str) -> Fato | None:
        """Fato usado pelo achado que deu origem à data.

        Args:
            achado: Achado vigente.
            chave: Nome do valor no achado.
            data: Data ISO.

        Returns:
            O fato do marco com esse valor, ou `None`.
        """
        tipo = "comprovante_preparo" if chave == "data_comprovante" else chave
        for fato_id in achado["fatos_usados"]:
            fato = self.por_id.get(fato_id)
            if fato and fato["tipo"] == tipo and fato["valor"] == data:
                return fato
        return None


def _no_do_identificador(indices: Indices, valor: str) -> dict[str, Any]:
    fato = indices.por_id.get(valor)
    if fato and indices.link_do_fato(fato):
        return {
            "tipo": "link",
            "texto": rotulos.legivel(fato["tipo"]),
            "link": indices.link_do_fato(fato),
        }
    fonte = indices.por_pagina.get(valor)
    if fonte:
        link = link_da_evidencia(indices.processo_id, fonte["id"])
        return {"tipo": "link", "texto": f"Folha {fonte['pagina'] or '?'}", "link": link}
    return {"tipo": "abreviado", "texto": rotulos.abreviar_identificador(valor), "titulo": valor}


def no_do_valor(
    indices: Indices, achado: dict[str, Any], chave: str, valor: object
) -> dict[str, Any]:
    """Árvore de exibição de um valor do achado, com links para as fontes.

    Args:
        indices: Fatos e evidências do processo.
        achado: Achado vigente.
        chave: Nome do valor.
        valor: Valor do JSON da API.

    Returns:
        Nó com `tipo` `link`, `abreviado`, `lista`, `mapa` ou `texto`.
    """
    if isinstance(valor, str) and DATA_ISO.fullmatch(valor):
        link = indices.link_do_fato(indices.fato_da_data(achado, chave, valor))
        texto = rotulos.formatar_data(valor)
        return (
            {"tipo": "link", "texto": texto, "link": link}
            if link
            else {"tipo": "texto", "texto": texto}
        )
    if isinstance(valor, str) and ID_PUBLICO.fullmatch(valor):
        return _no_do_identificador(indices, valor)
    if isinstance(valor, list):
        return {"tipo": "lista", "itens": [no_do_valor(indices, achado, chave, v) for v in valor]}
    if isinstance(valor, dict):
        campos = [
            (rotulos.legivel(k), no_do_valor(indices, achado, k, v)) for k, v in valor.items()
        ]
        return {"tipo": "mapa", "campos": campos}
    return {"tipo": "texto", "texto": rotulos.texto_do_valor(valor)}


def _exibe(chave: str, valor: object) -> bool:
    if chave == "fatos" or valor is None:
        return False
    return not isinstance(valor, dict | list) or bool(valor)


def _notas(anotacoes: list[dict[str, Any]], campo: str, alvo: str) -> list[dict[str, Any]]:
    return [
        {
            "autor": nota["autor"] or "usuário",
            "quando": rotulos.formatar_data(nota["criado_em"]),
            "texto": nota["texto"],
        }
        for nota in anotacoes
        if nota[campo] == alvo
    ]


def _fato_usado(
    indices: Indices, anotacoes: list[dict[str, Any]], achado_id: str, fato: Fato
) -> dict[str, Any]:
    return fato | {
        "chave": f"{achado_id}-{fato['id']}",
        "tipo_rotulo": rotulos.legivel(fato["tipo"]),
        "valor_texto": rotulos.texto_do_valor(fato["valor"]),
        "valor_edicao": fato["valor"]
        if isinstance(fato["valor"], str)
        else json.dumps(fato["valor"]),
        "status_rotulo": rotulos.STATUS_FATO.get(fato["status"], fato["status"]),
        "links": [
            {
                "link": link_da_evidencia(indices.processo_id, ev["id"]),
                "pagina": ev["pagina"] or "?",
            }
            for ev in fato["evidencias"]
        ],
        "opcoes_fonte": [
            (ev["id"], f"Página {ev['pagina'] or '?'} · {ev['trecho']}")
            for ev in fato["evidencias"]
        ],
        "notas": _notas(anotacoes, "fato_id", fato["id"]),
    }


def cartao_do_achado(
    indices: Indices, anotacoes: list[dict[str, Any]], achado: dict[str, Any]
) -> dict[str, Any]:
    """Dados do cartão de um achado vigente.

    Args:
        indices: Fatos e evidências do processo.
        anotacoes: Anotações do processo.
        achado: Achado vigente.

    Returns:
        O achado com rótulos, valores, fatos usados e notas.
    """
    usados = [
        {
            "id": fato_id,
            "fato": _fato_usado(indices, anotacoes, achado["id"], indices.por_id[fato_id]),
        }
        if fato_id in indices.por_id
        else {"id": fato_id, "fato": None}
        for fato_id in achado["fatos_usados"]
    ]
    return achado | {
        "validacao_rotulo": rotulos.legivel(achado["validacao"]),
        "resultado_rotulo": rotulos.RESULTADO.get(achado["resultado"], achado["resultado"]),
        "resultado_tom": rotulos.TOM_DO_RESULTADO.get(achado["resultado"], "atencao"),
        "valores_exibidos": [
            (rotulos.legivel(chave), no_do_valor(indices, achado, chave, valor))
            for chave, valor in achado["valores"].items()
            if _exibe(chave, valor)
        ],
        "usados": usados,
        "criado_em_texto": rotulos.formatar_data(achado["criado_em"]),
        "notas": _notas(anotacoes, "achado_id", achado["id"]),
    }


def _historico(achados: list[dict[str, Any]], fatos: list[Fato]) -> dict[str, Any]:
    antigos = [
        {
            "validacao": rotulos.legivel(a["validacao"]),
            "resultado": rotulos.RESULTADO.get(a["resultado"], a["resultado"]),
            "explicacao": a["explicacao"],
            "quando": rotulos.formatar_data(a["criado_em"]),
        }
        for a in achados
        if not a.get("vigente")
    ]
    substituidos = [
        {
            "id": f["id"],
            "texto": f"{rotulos.legivel(f['tipo'])}: {rotulos.texto_do_valor(f['valor'])}",
            "status": rotulos.STATUS_FATO.get(f["status"], f["status"]),
            "quando": rotulos.formatar_data(f["criado_em"]),
        }
        for f in fatos
        if not f["vigente"]
    ]
    return {
        "antigos": antigos,
        "substituidos": substituidos,
        "colunas_historico": COLUNAS_HISTORICO,
    }


def aviso_da_tela(consulta: QueryDict) -> str:
    """Confirmação mostrada depois de uma ação das validações.

    Args:
        consulta: Parâmetros da URL (`aviso` e, na correção, `achados`).

    Returns:
        A mensagem, ou texto vazio.
    """
    aviso = consulta.get("aviso", "")
    if aviso == "corrigido":
        gravados = consulta.get("achados", "")
        total = int(gravados) if gravados.isdigit() else 0
        return (
            f"Fato corrigido. Validações reexecutadas: {total} achado(s) novo(s); "
            "os anteriores ficam no histórico."
        )
    return AVISOS.get(aviso, "")


async def _pagina(
    request: HttpRequest,
    sessao: Sessao,
    processo_id: str,
    mensagens: dict[str, str],
    status: int = 200,
) -> HttpResponse:
    base = f"/processos/{processo_id}"
    vigentes = await obter(request, f"{base}/achados")
    if vigentes.is_error:
        return nao_encontrado(request, sessao)
    historico = (await obter(request, f"{base}/achados/historico")).json()["achados"]
    fatos = (await obter(request, f"{base}/fatos")).json()["fatos"]
    versoes = (await obter(request, f"{base}/fatos/historico")).json()["fatos"]
    anotacoes = (await obter(request, f"{base}/anotacoes")).json()["anotacoes"]
    indices = Indices(processo_id, fatos)
    contexto = contexto_da_moldura(request, sessao) | {
        "processo_id": processo_id,
        "achados": [cartao_do_achado(indices, anotacoes, a) for a in vigentes.json()["achados"]],
        "pode_anotar": tem(sessao, "anotar"),
        **_historico(historico, versoes),
        **mensagens,
    }
    return render(request, "processos/validacoes.html", contexto, status=status)


@require_GET
@tela_autenticada
async def validacoes(request: HttpRequest, sessao: Sessao, processo_id: str) -> HttpResponse:
    """Achados vigentes com valores, fatos usados, anotações e histórico (RF-INT-02).

    Args:
        request: Pedido do navegador; `?aviso=` confirma a última ação.
        sessao: Dados da sessão.
        processo_id: Identificador público do processo.

    Returns:
        Página das validações, ou 404 se a API não encontra o processo.
    """
    return await _pagina(request, sessao, processo_id, {"aviso": aviso_da_tela(request.GET)})


def fonte_da_correcao(fato: Fato, dados: QueryDict) -> dict[str, Any] | None:
    """Página, intervalo e trecho da correção: uma evidência do fato ou um trecho novo.

    Args:
        fato: Fato vigente corrigido.
        dados: Campos do formulário (`fonte` ou `pagina_id`, `inicio`, `fim` e `trecho`).

    Returns:
        Campos da fonte para a API, ou `None` se o trecho novo está incompleto ou inválido.
    """
    escolhida = dados.get("fonte", "")
    for evidencia in fato["evidencias"]:
        if evidencia["id"] == escolhida:
            return {campo: evidencia[campo] for campo in ("pagina_id", "inicio", "fim", "trecho")}
    pagina_id = dados.get("pagina_id", "").strip()
    trecho = dados.get("trecho", "")
    try:
        inicio, fim = int(dados.get("inicio", "")), int(dados.get("fim", ""))
    except ValueError:
        return None
    if not ID_PUBLICO.fullmatch(pagina_id) or inicio < 0 or fim <= inicio or not trecho.strip():
        return None
    return {"pagina_id": pagina_id, "inicio": inicio, "fim": fim, "trecho": trecho}


def valor_corrigido(original: object, texto: str) -> object:
    """Valor digitado na correção, no tipo do valor original.

    Args:
        original: Valor atual do fato.
        texto: Texto digitado.

    Returns:
        O texto sem espaços nas pontas para valor textual; o JSON lido, ou o texto, nos demais.
    """
    if isinstance(original, str):
        return texto.strip()
    try:
        lido: object = json.loads(texto)
    except ValueError:
        return texto.strip()
    return lido


async def _corpo_da_correcao(
    request: HttpRequest, processo_id: str, fato_id: str
) -> dict[str, Any] | None:
    fatos = (await obter(request, f"/processos/{processo_id}/fatos")).json()["fatos"]
    fato = next((f for f in fatos if f["id"] == fato_id), None)
    fonte = fonte_da_correcao(fato, request.POST) if fato else None
    if fato is None or fonte is None:
        return None
    valor = valor_corrigido(fato["valor"], request.POST.get("valor", ""))
    return {"status": "corrigido", "valor": valor} | fonte


async def _postar(
    request: HttpRequest, sessao: Sessao, processo_id: str, caminho: str, corpo: dict[str, Any]
) -> HttpResponse | dict[str, Any]:
    resposta = await cliente_api.chamar(request, "POST", caminho, json=corpo)
    if resposta.is_error:
        erro = cliente_api.detalhe_do_erro(resposta)
        return await _pagina(request, sessao, processo_id, {"erro": erro}, resposta.status_code)
    dados: dict[str, Any] = resposta.json()
    return dados


@require_POST
@tela_autenticada
async def corrigir(
    request: HttpRequest, sessao: Sessao, processo_id: str, fato_id: str
) -> HttpResponse:
    """Confirma ou corrige um fato (RF-FAT-03); a API reexecuta as validações.

    Args:
        request: Pedido com `status` e, na correção, `valor` e a fonte.
        sessao: Dados da sessão.
        processo_id: Identificador público do processo.
        fato_id: Identificador público do fato.

    Returns:
        Redirecionamento às validações com o aviso, ou a tela com o erro.
    """
    base = f"/processos/{processo_id}"
    corpo: dict[str, Any] | None = {"status": "confirmado"}
    if request.POST.get("status") == "corrigido":
        corpo = await _corpo_da_correcao(request, processo_id, fato_id)
    if corpo is None:
        return await _pagina(request, sessao, processo_id, {"erro": MENSAGEM_FONTE}, 400)
    caminho = f"{base}/fatos/{fato_id}/corrigir"
    dados = await _postar(request, sessao, processo_id, caminho, corpo)
    if isinstance(dados, HttpResponse):
        return dados
    destino = f"{base}/validacoes?aviso=confirmado"
    if corpo["status"] == "corrigido":
        destino = f"{base}/validacoes?aviso=corrigido&achados={dados.get('achados_gravados', 0)}"
    return cliente_api.redirecionar(request, destino)


@require_POST
@tela_autenticada
async def anotar(request: HttpRequest, sessao: Sessao, processo_id: str) -> HttpResponse:
    """Grava uma anotação sobre um fato ou um achado (RF-FAT-04).

    Args:
        request: Pedido com `fato_id` ou `achado_id` e `texto`.
        sessao: Dados da sessão.
        processo_id: Identificador público do processo.

    Returns:
        Redirecionamento às validações; texto em branco volta sem gravar.
    """
    base = f"/processos/{processo_id}"
    texto = request.POST.get("texto", "").strip()
    if not texto:
        return cliente_api.redirecionar(request, f"{base}/validacoes")
    alvo = {
        campo: request.POST[campo] for campo in ("achado_id", "fato_id") if request.POST.get(campo)
    }
    corpo = alvo | {"texto": texto}
    resultado = await _postar(request, sessao, processo_id, f"{base}/anotacoes", corpo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return cliente_api.redirecionar(request, f"{base}/validacoes?aviso=anotacao")
