"""Dossiê do processo: ficha, linha do tempo, índice de peças com reclassificação e achados.

Cada evidência leva ao visualizador na página dela (RF-INT-05); a reclassificação é um
formulário POST que chama a API e volta ao dossiê (RF-PEC-02).
"""

from typing import Any

import httpx
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from lupa_web import cliente_api, rotulos
from lupa_web.telas.sessao import (
    Sessao,
    contexto_da_moldura,
    nao_encontrado,
    obter,
    tela_autenticada,
    tem,
)

AVISOS = {"reclassificada": "Peça reclassificada. Os fatos e as validações foram atualizados."}


def link_da_evidencia(processo_id: str, evidencia_id: str) -> str:
    """Endereço do visualizador aberto na evidência.

    Args:
        processo_id: Identificador público do processo.
        evidencia_id: Identificador público da evidência.

    Returns:
        Caminho do visualizador com `evidencia`.
    """
    return f"/processos/{processo_id}/visualizador?evidencia={evidencia_id}"


def link_da_pagina(processo_id: str, arquivo_id: str | None, pagina: int) -> str:
    """Endereço do visualizador aberto numa página de um arquivo.

    Args:
        processo_id: Identificador público do processo.
        arquivo_id: Identificador público do arquivo, se conhecido.
        pagina: Número da página no arquivo.

    Returns:
        Caminho do visualizador com `arquivo` (quando houver) e `pagina`.
    """
    arquivo = f"arquivo={arquivo_id}&" if arquivo_id else ""
    return f"/processos/{processo_id}/visualizador?{arquivo}pagina={pagina}"


def texto_do_dado(tipo: str, valor: str) -> str:
    """Valor de um dado da capa pronto para leitura.

    Args:
        tipo: Tipo do dado (`valor_causa`, `data_distribuicao`...).
        valor: Valor como a API devolve.

    Returns:
        Valor em reais, data no formato brasileiro ou o próprio valor.
    """
    if tipo == "valor_causa":
        return rotulos.formatar_moeda(valor)
    if tipo == "data_distribuicao":
        return rotulos.formatar_data(valor)
    return valor


def capa(processo_id: str, ficha: dict[str, Any]) -> dict[str, Any]:
    """Partes e dados da capa da ficha, com o link de cada evidência.

    Args:
        processo_id: Identificador público do processo.
        ficha: `ficha` do dossiê.

    Returns:
        `partes` e `dados` prontos para o template.
    """
    partes = [
        {
            "nome": parte["nome"],
            "polo": parte["polo"],
            "qualidade": rotulos.legivel(parte["qualidade"]),
            "link": link_da_evidencia(processo_id, parte["evidencia_id"]),
        }
        for parte in ficha["partes"]
    ]
    dados = [
        {
            "rotulo": rotulos.legivel(dado["tipo"]),
            "texto": texto_do_dado(dado["tipo"], dado["valor"]),
            "link": link_da_evidencia(processo_id, dado["evidencia_id"]),
        }
        for dado in ficha["dados_capa"]
    ]
    return {"partes": partes, "dados": dados}


def _paginas(peca: dict[str, Any]) -> str:
    inicial, final = peca["pagina_inicial"], peca["pagina_final"]
    return str(inicial) if inicial == final else f"{inicial}–{final}"


def linha_da_peca(processo_id: str, peca: dict[str, Any], resumo: str | None) -> dict[str, Any]:
    """Dados de uma linha do índice de peças.

    Args:
        processo_id: Identificador público do processo.
        peca: Peça de `GET /processos/<id>/indice`.
        resumo: Resumo gerado pelo modelo, se pedido.

    Returns:
        A peça com rótulos, intervalo, link da página inicial, confiança e sinais.
    """
    sinais = peca["resumo_flags"]
    return peca | {
        "tipo_rotulo": rotulos.legivel(peca["tipo"]),
        "origem_rotulo": rotulos.legivel(peca["origem"]),
        "metodo_rotulo": rotulos.legivel(peca["metodo"]),
        "paginas": _paginas(peca),
        "link": link_da_pagina(processo_id, peca["arquivo_id"], peca["pagina_inicial"]),
        "data_texto": rotulos.formatar_data(peca["data"]),
        "confianca_texto": rotulos.percentual(peca["confianca"]),
        "sinais": [rotulos.legivel(sinal) for sinal in sinais["peca"]],
        "total_saneamento": sinais["total_saneamento"],
        "resumo": resumo,
    }


def _linha_do_tempo(processo_id: str, eventos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        evento
        | {
            "data_texto": rotulos.formatar_data(evento["data"]),
            "tipo_rotulo": rotulos.legivel(evento["tipo"]),
            "status_rotulo": rotulos.legivel(evento["status"]),
            "link": link_da_evidencia(processo_id, evento["evidencia_id"]),
        }
        for evento in eventos
    ]


def _achados(processo_id: str, achados: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        achado
        | {
            "validacao_rotulo": rotulos.legivel(achado["validacao"]),
            "resultado_rotulo": rotulos.RESULTADO.get(achado["resultado"], achado["resultado"]),
            "links": [link_da_evidencia(processo_id, f["evidencia_id"]) for f in achado["fontes"]],
        }
        for achado in achados
    ]


def _alertas(processo_id: str, alertas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "pagina": alerta["pagina"],
            "link": link_da_pagina(processo_id, alerta["arquivo_id"], alerta["pagina"]),
            "sinais": ", ".join(rotulos.legivel(sinal) for sinal in alerta["flags"]),
        }
        for alerta in alertas
    ]


def contexto_do_dossie(
    processo_id: str, dossie: dict[str, Any], indice: dict[str, Any]
) -> dict[str, Any]:
    """Contexto do template do dossiê.

    Args:
        processo_id: Identificador público do processo.
        dossie: Corpo de `GET /processos/<id>/dossie`.
        indice: Corpo de `GET /processos/<id>/indice`.

    Returns:
        Ficha, linha do tempo, peças, alertas e achados prontos para o template.
    """
    ficha = dossie["ficha"]
    resumos = {
        peca["peca_id"]: (peca.get("resumo_peca") or {}).get("texto") for peca in dossie["pecas"]
    }
    situacao = ficha["ingestao"]["situacao"]
    return {
        "processo_id": processo_id,
        "ficha": ficha,
        "numero_cnj": rotulos.mascarar_cnj(ficha["numero_cnj"]),
        "capa": capa(processo_id, ficha),
        "classe_rotulo": rotulos.legivel(ficha["classe"]),
        "status_rotulo": rotulos.legivel(ficha["status"]),
        "responsaveis": ", ".join(r["nome_usuario"] for r in ficha["responsaveis"]),
        "situacao_rotulo": rotulos.SITUACAO.get(situacao, situacao),
        "linha_do_tempo": _linha_do_tempo(processo_id, dossie["linha_do_tempo"]),
        "pecas": [
            linha_da_peca(processo_id, peca, resumos.get(peca["id"])) for peca in indice["pecas"]
        ],
        "alertas": _alertas(processo_id, dossie["alertas"]),
        "achados": _achados(processo_id, dossie["achados"]),
        "tipos_peca": [(tipo, rotulos.legivel(tipo)) for tipo in rotulos.TIPOS_PECA],
    }


async def _pagina(
    request: HttpRequest,
    sessao: Sessao,
    processo_id: str,
    mensagens: dict[str, str],
    status: int = 200,
) -> HttpResponse:
    base = f"/processos/{processo_id}"
    parametros = {"resumos": "true"} if request.GET.get("resumos") else None
    resposta = await cliente_api.chamar(request, "GET", f"{base}/dossie", params=parametros)
    if resposta.status_code == httpx.codes.NOT_FOUND:
        return nao_encontrado(request, sessao)
    indice = (await obter(request, f"{base}/indice")).json()
    contexto = (
        contexto_da_moldura(request, sessao)
        | contexto_do_dossie(processo_id, resposta.json(), indice)
        | {"pode_reclassificar": tem(sessao, "anotar")}
        | mensagens
    )
    return render(request, "processos/dossie.html", contexto, status=status)


@require_GET
@tela_autenticada
async def dossie(request: HttpRequest, sessao: Sessao, processo_id: str) -> HttpResponse:
    """Dossiê do processo; `?resumos=1` pede os resumos das peças ao modelo (RF-DOS-04).

    Args:
        request: Pedido do navegador; `?aviso=reclassificada` confirma a reclassificação.
        sessao: Dados da sessão.
        processo_id: Identificador público do processo.

    Returns:
        Página do dossiê, ou 404 se a API não encontra o processo.
    """
    aviso = AVISOS.get(request.GET.get("aviso", ""), "")
    return await _pagina(request, sessao, processo_id, {"aviso": aviso})


@require_POST
@tela_autenticada
async def reclassificar(
    request: HttpRequest, sessao: Sessao, processo_id: str, peca_id: str
) -> HttpResponse:
    """Reclassifica o tipo de uma peça (RF-PEC-02) e volta ao dossiê.

    Args:
        request: Pedido com `tipo`.
        sessao: Dados da sessão.
        processo_id: Identificador público do processo.
        peca_id: Identificador público da peça.

    Returns:
        Redirecionamento ao dossiê, ou o dossiê com o erro da API e o mesmo status.
    """
    base = f"/processos/{processo_id}"
    corpo = {"tipo": request.POST.get("tipo", "")}
    caminho = f"{base}/pecas/{peca_id}/reclassificar"
    resposta = await cliente_api.chamar(request, "POST", caminho, json=corpo)
    if resposta.is_error:
        erro = cliente_api.detalhe_do_erro(resposta)
        return await _pagina(request, sessao, processo_id, {"erro": erro}, resposta.status_code)
    return cliente_api.redirecionar(request, f"{base}/dossie?aviso=reclassificada")
