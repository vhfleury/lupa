"""Chat sobre os autos com HTMX: pergunta, resposta conferida, teto, revisão e liberação (A5).

A pergunta vai por `hx-post` e a resposta volta como fragmento anexado ao fim da conversa
(`hx-swap="beforeend"`), com o formulário trocado fora da área (`hx-swap-oob`). O texto da
pergunta nunca entra em log.
"""

from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from lupa_web import cliente_api, rotulos
from lupa_web.telas.sessao import (
    Sessao,
    contexto_da_moldura,
    obter,
    tela_autenticada,
    tem,
)

AVISO_IA = "Conteúdo gerado por IA: confira na página citada antes de usar."
LIMITE_PERGUNTA = 2000
MENSAGEM_INDISPONIVEL = "O Lupa não conseguiu falar com o serviço. Tente de novo em instantes."
AVISO_LIBERADO = "Processo liberado. O chat e os resumos voltam a funcionar."
DESFECHOS = {
    "sem_evidencia": "Sem evidência: resposta não conferida nos autos.",
    "recusa": "Pergunta fora do que o assistente pode responder.",
    "descartada": "Resposta descartada pela conferência automática.",
}
MOTIVO_REVISAO = {
    "instrucao_refletida": "a resposta repetia uma instrução contida nos autos",
    "outro_processo": "a resposta citava identificador de outro processo",
}
MOTIVO_REVISAO_PADRAO = "violou a conferência automática"
MOTIVO_ENCERRAMENTO = {
    "teto_conversa": "limite de uso da conversa atingido",
    "teto_processo": "limite de uso do processo atingido",
}
TRECHO_DO_AVISO_DE_DESCARTE = "não conferiram"


def plural(total: int, singular: str, varios: str) -> str:
    """Quantidade com a palavra no singular ou no plural.

    Args:
        total: Quantidade.
        singular: Texto para um.
        varios: Texto para zero ou mais de um.

    Returns:
        Texto como `1 citação descartada`.
    """
    return f"{total} {singular if total == 1 else varios}"


def link_da_citacao(processo_id: str, citacao: dict[str, Any]) -> str:
    """Endereço do visualizador na página citada, só com identificadores e número.

    Args:
        processo_id: Identificador público do processo.
        citacao: Citação conferida da API.

    Returns:
        Caminho do visualizador, ou texto vazio sem número de página.
    """
    numero = citacao.get("pagina_numero")
    if numero is None:
        return ""
    arquivo = citacao.get("arquivo_id")
    prefixo = f"arquivo={arquivo}&" if arquivo else ""
    return f"/processos/{processo_id}/visualizador?{prefixo}pagina={numero}"


def mensagem_da_tela(
    processo_id: str, mensagem: dict[str, Any], em_revisao: bool = False
) -> dict[str, Any]:
    """Mensagem pronta para o template, com o tipo de bloco em que aparece.

    Args:
        processo_id: Identificador público do processo.
        mensagem: Mensagem da API.
        em_revisao: Se a resposta veio de processo em revisão.

    Returns:
        A mensagem com `bloco` (`usuario`, `aviso` ou `ia`), desfecho, citações e avisos.
    """
    if mensagem["papel"] != "agente":
        return mensagem | {"bloco": "usuario"}
    if mensagem["status"] == "teto" or (mensagem["status"] == "recusa" and em_revisao):
        return mensagem | {"bloco": "aviso"}
    descartadas = mensagem.get("citacoes_descartadas", 0)
    return mensagem | {
        "bloco": "ia",
        "desfecho": DESFECHOS.get(mensagem["status"], ""),
        "citacoes_da_tela": [
            {"link": link_da_citacao(processo_id, c), "numero": c.get("pagina_numero")} | c
            for c in mensagem["citacoes"]
        ],
        "descartes": (
            plural(
                descartadas,
                "citação descartada nesta resposta",
                "citações descartadas nesta resposta",
            )
            if descartadas
            else ""
        ),
        "avisos_da_tela": [a for a in mensagem["avisos"] if TRECHO_DO_AVISO_DE_DESCARTE not in a],
    }


def _descartes_da_conversa(total: int) -> str:
    return plural(total, "citação descartada nesta conversa", "citações descartadas nesta conversa")


def contexto_das_conversas(processo_id: str, conversas: list[dict[str, Any]]) -> dict[str, Any]:
    """Conversa atual (a última aberta), encerramento e conversas anteriores.

    Args:
        processo_id: Identificador público do processo.
        conversas: Conversas de `GET /processos/<id>/chat`, da mais antiga à mais recente.

    Returns:
        `atual`, `encerramento` e `anteriores` prontos para o template.
    """
    ultima = conversas[-1] if conversas else None
    atual = ultima if ultima and not ultima["encerrada"] else None
    encerramento = ultima["motivo_encerramento"] if ultima and ultima["encerrada"] else None
    anteriores = [
        {
            "quando": rotulos.formatar_data(c["criada_em"]),
            "total": plural(len(c["mensagens"]), "mensagem", "mensagens"),
            "motivo": MOTIVO_ENCERRAMENTO.get(
                c["motivo_encerramento"] or "", c["motivo_encerramento"]
            ),
            "mensagens": [mensagem_da_tela(processo_id, m) for m in c["mensagens"]],
        }
        for c in reversed(conversas)
        if c is not atual
    ]
    conversa_atual = None
    if atual:
        conversa_atual = {
            "descartes": _descartes_da_conversa(atual["citacoes_descartadas"]),
            "mensagens": [mensagem_da_tela(processo_id, m) for m in atual["mensagens"]],
        }
    return {
        "atual": conversa_atual,
        "encerramento": encerramento,
        "anteriores": anteriores,
    }


async def _revisao(request: HttpRequest, sessao: Sessao, processo_id: str) -> dict[str, Any]:
    revisao = (await obter(request, f"/processos/{processo_id}/revisao")).json()
    return {
        "em_revisao": bool(revisao.get("em_revisao")),
        "motivo_revisao": MOTIVO_REVISAO.get(revisao.get("motivo") or "", MOTIVO_REVISAO_PADRAO),
        "pode_liberar": tem(sessao, "ver_auditoria"),
    }


async def _pagina(
    request: HttpRequest,
    sessao: Sessao,
    processo_id: str,
    mensagens: dict[str, str],
    status: int = 200,
) -> HttpResponse:
    base = f"/processos/{processo_id}"
    conversas = (await obter(request, f"{base}/chat")).json()["conversas"]
    revisao = await _revisao(request, sessao, processo_id)
    contexto_conversas = contexto_das_conversas(processo_id, conversas)
    contexto = contexto_da_moldura(request, sessao) | {
        "processo_id": processo_id,
        "aviso_ia": AVISO_IA,
        "limite_pergunta": LIMITE_PERGUNTA,
        **revisao,
        "bloqueado": revisao["em_revisao"] or bool(contexto_conversas["encerramento"]),
        **contexto_conversas,
        **mensagens,
    }
    return render(request, "chat/chat.html", contexto, status=status)


def _fragmento(request: HttpRequest, processo_id: str, contexto: dict[str, Any]) -> HttpResponse:
    base = {
        "processo_id": processo_id,
        "aviso_ia": AVISO_IA,
        "limite_pergunta": LIMITE_PERGUNTA,
        "bloqueado": False,
        "pergunta": "",
        "resposta": None,
        "erro": "",
    }
    return render(request, "chat/_resposta.html", base | contexto)


async def _perguntar(
    request: HttpRequest, sessao: Sessao, processo_id: str, pergunta: str
) -> HttpResponse:
    caminho = f"/processos/{processo_id}/chat"
    try:
        resposta = await cliente_api.chamar(
            request, "POST", caminho, longo=True, json={"pergunta": pergunta}
        )
    except cliente_api.ApiIndisponivelError:
        return _fragmento(
            request, processo_id, {"pergunta": pergunta, "erro": MENSAGEM_INDISPONIVEL}
        )
    if resposta.is_error:
        erro = cliente_api.detalhe_do_erro(resposta)
        return _fragmento(request, processo_id, {"pergunta": pergunta, "erro": erro})
    dados = resposta.json()
    em_revisao = bool(dados.get("processo_em_revisao"))
    revisao = await _revisao(request, sessao, processo_id) if em_revisao else {}
    return _fragmento(
        request,
        processo_id,
        revisao
        | {
            "oob_revisao": em_revisao,
            "pergunta": pergunta,
            "resposta": mensagem_da_tela(processo_id, dados, em_revisao),
            "bloqueado": em_revisao or bool(dados.get("conversa_encerrada")),
            "descartes_conversa": _descartes_da_conversa(
                dados.get("citacoes_descartadas_na_conversa", 0)
            ),
        },
    )


@require_http_methods(["GET", "POST"])
@tela_autenticada
async def chat(request: HttpRequest, sessao: Sessao, processo_id: str) -> HttpResponse:
    """Tela do chat (GET) e pergunta ao assistente (POST, fragmento HTMX) (RF-INT-05).

    Args:
        request: GET mostra as conversas (`?aviso=liberado` confirma a liberação); POST leva
            `pergunta`.
        sessao: Dados da sessão.
        processo_id: Identificador público do processo.

    Returns:
        Página do chat; no POST HTMX, o fragmento com a pergunta e a resposta; no POST comum
        (sem JavaScript), a pergunta é feita e o navegador volta à tela do chat.
    """
    if request.method == "GET":
        aviso = AVISO_LIBERADO if request.GET.get("aviso") == "liberado" else ""
        return await _pagina(request, sessao, processo_id, {"aviso": aviso})
    pergunta = request.POST.get("pergunta", "").strip()
    if not pergunta:
        return _fragmento(request, processo_id, {})
    if request.headers.get("HX-Request") == "true":
        return await _perguntar(request, sessao, processo_id, pergunta)
    caminho = f"/processos/{processo_id}/chat"
    await cliente_api.chamar(request, "POST", caminho, longo=True, json={"pergunta": pergunta})
    return cliente_api.redirecionar(request, caminho)


def _confirmacao(request: HttpRequest, sessao: Sessao, processo_id: str) -> HttpResponse:
    base = f"/processos/{processo_id}"
    contexto = contexto_da_moldura(request, sessao) | {
        "processo_id": processo_id,
        "titulo": "Liberar a revisão?",
        "mensagem": (
            "Confirme que conferiu o incidente. O chat e os resumos gerados voltam a funcionar "
            "neste processo, e a liberação fica registrada na auditoria."
        ),
        "rotulo_confirmar": "Liberar",
        "acao": f"{base}/chat/liberar",
        "voltar": f"{base}/chat",
    }
    return render(request, "chat/liberar.html", contexto)


@require_http_methods(["GET", "POST"])
@tela_autenticada
async def liberar(request: HttpRequest, sessao: Sessao, processo_id: str) -> HttpResponse:
    """Confirmação (GET) e liberação (POST) do processo em revisão; a API exige desembargador.

    Args:
        request: Pedido do navegador.
        sessao: Dados da sessão.
        processo_id: Identificador público do processo.

    Returns:
        Página de confirmação, redirecionamento ao chat com o aviso ou o chat com o erro da API.
    """
    if request.method == "GET":
        return _confirmacao(request, sessao, processo_id)
    base = f"/processos/{processo_id}"
    resposta = await cliente_api.chamar(request, "POST", f"{base}/liberar-revisao", json={})
    if resposta.is_error:
        erro = cliente_api.detalhe_do_erro(resposta)
        return await _pagina(request, sessao, processo_id, {"erro": erro}, resposta.status_code)
    return cliente_api.redirecionar(request, f"{base}/chat?aviso=liberado")
