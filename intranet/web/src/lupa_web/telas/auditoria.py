"""Auditoria: eventos com filtros, exportação, verificação da cadeia e relatório de uso.

Só o desembargador tem `ver_auditoria`; para os demais a API responde 403 e o middleware mostra
a página de acesso negado (RF-INT-02). Tudo é GET: filtros, verificação e relatório são
parâmetros da URL; a exportação é repassada da API.
"""

import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import render
from django.views.decorators.http import require_GET

from lupa_web import cliente_api, rotulos
from lupa_web.telas.sessao import Sessao, contexto_da_moldura, tela_autenticada

ID_PUBLICO = re.compile(r"[0-9a-fA-F]{64}")
LIMITE = "50"
CAMPOS_DE_TEXTO = ("usuario_id", "processo_id", "acao", "ip")
CAMPOS_DE_ID = (("usuario_id", "usuário"), ("processo_id", "processo"))
TIPOS_DE_RELATORIO = {"processo": "processo", "usuario": "usuario"}
SIMBOLOS = {"BRL": "R$", "USD": "US$"}
CASAS_MINIMAS = 2
CASAS_MAXIMAS = 4
TAMANHO_ID_CURTO = 8
MENSAGEM_DATA = "Informe data e hora válidas."
MENSAGEM_INTERVALO = "O início do intervalo deve ser anterior ao fim."
MENSAGEM_IDENTIFICADOR = "Informe o identificador."
CABECALHOS_DO_ARQUIVO = ("Content-Type", "Content-Disposition")

ACOES = (
    "login_ok",
    "login_falha",
    "login_bloqueado",
    "mfa_ok",
    "mfa_falha",
    "logout",
    "senha_trocada",
    "senha_resetada",
    "mfa_resetado",
    "usuario_criado",
    "usuario_desativado",
    "usuario_reativado",
    "responsavel_adicionado",
    "responsavel_removido",
    "processo_criado",
    "arquivo_enviado",
    "processo_aberto",
    "pagina_vista",
    "busca",
    "pergunta_chat",
    "anotacao",
    "fato_corrigido",
    "peca_reclassificada",
    "validacao_executada",
    "chamada_modelo",
    "citacao_descartada",
    "processo_descartado",
    "descarte_objetos_pendente",
    "auditoria_consultada",
    "auditoria_exportada",
    "processo_em_revisao",
    "revisao_liberada",
)


class FiltroInvalidoError(Exception):
    """Filtro da tela que não vai à API; a mensagem é o motivo para o usuário."""


def instante(valor: str) -> datetime:
    """Data e hora do campo `datetime-local` (horário de Brasília) como instante UTC.

    Args:
        valor: Texto `AAAA-MM-DDTHH:MM`.

    Returns:
        Instante em UTC.

    Raises:
        FiltroInvalidoError: Texto que não é data e hora.
    """
    try:
        local = datetime.fromisoformat(valor)
    except ValueError:
        raise FiltroInvalidoError(MENSAGEM_DATA) from None
    return local.replace(tzinfo=rotulos.FUSO).astimezone(UTC)


def _conferir_ids(campos: dict[str, str]) -> None:
    for campo, rotulo in CAMPOS_DE_ID:
        valor = campos.get(campo, "")
        if valor and not ID_PUBLICO.fullmatch(valor):
            raise FiltroInvalidoError(f"O identificador de {rotulo} não é válido.")


def _intervalo(consulta: QueryDict) -> dict[str, str]:
    inicio, fim = consulta.get("inicio", ""), consulta.get("fim", "")
    instantes = {campo: instante(v) for campo, v in (("inicio", inicio), ("fim", fim)) if v}
    if len(instantes) == len(("inicio", "fim")) and instantes["inicio"] >= instantes["fim"]:
        raise FiltroInvalidoError(MENSAGEM_INTERVALO)
    return {campo: momento.isoformat() for campo, momento in instantes.items()}


def parametros_da_api(consulta: QueryDict) -> dict[str, str]:
    """Filtros preenchidos da tela, no formato da API.

    Args:
        consulta: Parâmetros da URL da tela.

    Returns:
        Identificadores, ação, IP e intervalo em UTC, só os preenchidos.

    Raises:
        FiltroInvalidoError: Identificador, data ou intervalo inválido.
    """
    campos = {
        campo: consulta.get(campo, "").strip()
        for campo in CAMPOS_DE_TEXTO
        if consulta.get(campo, "").strip()
    }
    _conferir_ids(campos)
    return campos | _intervalo(consulta)


def formatar_dinheiro(valor: str, moeda: str) -> str:
    """Valor com o símbolo da moeda e de duas a quatro casas decimais.

    Args:
        valor: Valor decimal em texto.
        moeda: Código da moeda (`BRL`, `USD`...).

    Returns:
        Texto como `R$ 0,1234` ou `US$ 2,00`.
    """
    texto = f"{Decimal(valor):,.{CASAS_MAXIMAS}f}"
    inteiro, decimais = texto.split(".")
    decimais = decimais.rstrip("0").ljust(CASAS_MINIMAS, "0")
    numero = f"{inteiro.replace(',', '.')},{decimais}"
    return f"{SIMBOLOS.get(moeda, moeda)} {numero}"


def texto_da_verificacao(verificacao: dict[str, Any]) -> str:
    """Resultado da verificação da cadeia para o usuário.

    Args:
        verificacao: Corpo de `GET /auditoria/verificar`.

    Returns:
        Frase de cadeia íntegra ou quebrada.
    """
    if verificacao["integra"]:
        total = verificacao["total"]
        return f"Cadeia íntegra: {total} evento(s) conferido(s), nenhum hash divergente."
    onde = verificacao.get("primeira_sequencia_quebrada") or "desconhecida"
    motivo = f" ({verificacao['motivo']})" if verificacao.get("motivo") else ""
    return f"Cadeia QUEBRADA a partir da sequência {onde}{motivo}."


def _com(consulta: QueryDict, **extras: str) -> str:
    campos = {c: consulta.get(c, "") for c in (*CAMPOS_DE_TEXTO, "inicio", "fim")}
    return urlencode({c: v for c, v in (campos | extras).items() if v})


def _linha_do_evento(consulta: QueryDict, evento: dict[str, Any]) -> dict[str, Any]:
    def relatorio(tipo: str, identificador: str | None) -> dict[str, str] | None:
        if not identificador:
            return None
        link = "/auditoria?" + _com(consulta, relatorio_tipo=tipo, relatorio_id=identificador)
        return {"id": identificador, "curto": identificador[:TAMANHO_ID_CURTO], "link": link}

    return evento | {
        "quando": rotulos.formatar_data(evento["ocorrido_em"]),
        "usuario": relatorio("usuario", evento.get("usuario_id")),
        "processo": relatorio("processo", evento.get("processo_id")),
    }


def _relatorio_da_tela(relatorio: dict[str, Any]) -> dict[str, Any]:
    custo = relatorio["custo_estimado"]
    moeda = custo["moeda"]
    return relatorio | {
        "primeiro": rotulos.formatar_data(relatorio.get("primeiro_acesso")),
        "ultimo": rotulos.formatar_data(relatorio.get("ultimo_acesso")),
        "contagem": list(relatorio["contagem_por_acao"].items()),
        "custo_total": formatar_dinheiro(custo["total"], moeda),
        "por_modelo": [
            m | {"custo_texto": formatar_dinheiro(m["custo"], moeda) if m["custo"] else ""}
            for m in custo["por_modelo"]
        ],
    }


async def _eventos(request: HttpRequest, parametros: dict[str, str]) -> dict[str, Any]:
    cursor = request.GET.get("cursor", "")
    consulta = parametros | {"limite": LIMITE} | ({"cursor": cursor} if cursor else {})
    resposta = await cliente_api.chamar(request, "GET", "/auditoria", params=consulta)
    if resposta.is_error:
        return {"erro": cliente_api.detalhe_do_erro(resposta)}
    pagina = resposta.json()
    proximo = pagina.get("proximo_cursor")
    return {
        "consultado": True,
        "eventos": [_linha_do_evento(request.GET, e) for e in pagina["eventos"]],
        "proxima_pagina": "/auditoria?" + _com(request.GET, cursor=proximo) if proximo else "",
    }


async def _verificacao(request: HttpRequest) -> dict[str, Any]:
    if not request.GET.get("verificar"):
        return {}
    verificacao = (await cliente_api.chamar(request, "GET", "/auditoria/verificar")).json()
    return {"verificacao": verificacao, "texto_verificacao": texto_da_verificacao(verificacao)}


async def _relatorio(request: HttpRequest, intervalo: dict[str, str]) -> dict[str, Any]:
    tipo = TIPOS_DE_RELATORIO.get(request.GET.get("relatorio_tipo", ""))
    if tipo is None:
        return {}
    identificador = request.GET.get("relatorio_id", "").strip()
    if not ID_PUBLICO.fullmatch(identificador):
        return {"erro_relatorio": MENSAGEM_IDENTIFICADOR}
    parametros = intervalo | {tipo: identificador}
    resposta = await cliente_api.chamar(
        request, "GET", "/auditoria/relatorio-uso", params=parametros
    )
    if resposta.is_error:
        return {"erro_relatorio": cliente_api.detalhe_do_erro(resposta)}
    return {"relatorio": _relatorio_da_tela(resposta.json())}


def links_de_exportacao(parametros: dict[str, str]) -> dict[str, str]:
    """Links de download do filtro aplicado, com os parâmetros no formato da API.

    Args:
        parametros: Filtros aplicados, como saem de `parametros_da_api`.

    Returns:
        `exportar_csv`, `exportar_json` e `exportar_uso` (uso por processo e usuário em CSV).
    """
    uso = {"formato": "csv"} | {
        chave: parametros[campo]
        for chave, campo in (
            ("processo", "processo_id"),
            ("usuario", "usuario_id"),
            ("inicio", "inicio"),
            ("fim", "fim"),
        )
        if campo in parametros
    }
    return {
        "exportar_csv": "/auditoria/exportar?" + urlencode({"formato": "csv"} | parametros),
        "exportar_json": "/auditoria/exportar?" + urlencode({"formato": "json"} | parametros),
        "exportar_uso": "/auditoria/relatorio-uso?" + urlencode(uso),
    }


@require_GET
@tela_autenticada
async def lista(request: HttpRequest, sessao: Sessao) -> HttpResponse:
    """Eventos da auditoria com filtros, verificação e relatório de uso (RF-AUD-02 a 04).

    Args:
        request: Pedido com os filtros, `cursor`, `verificar` e `relatorio_tipo`/`relatorio_id`.
        sessao: Dados da sessão.

    Returns:
        Página da auditoria; a API responde 403 a quem não tem `ver_auditoria`.
    """
    contexto: dict[str, Any] = contexto_da_moldura(request, sessao) | {
        "filtros": {c: request.GET.get(c, "") for c in (*CAMPOS_DE_TEXTO, "inicio", "fim")},
        "acoes": ACOES,
        "relatorio_tipo": request.GET.get("relatorio_tipo", "processo"),
        "relatorio_id": request.GET.get("relatorio_id", ""),
    }
    try:
        parametros = parametros_da_api(request.GET)
    except FiltroInvalidoError as erro:
        contexto |= links_de_exportacao({}) | {"erro": str(erro)}
        return render(request, "auditoria/auditoria.html", contexto)
    contexto |= links_de_exportacao(parametros)
    contexto |= await _eventos(request, parametros)
    contexto |= await _verificacao(request)
    intervalo = {c: parametros[c] for c in ("inicio", "fim") if c in parametros}
    contexto |= await _relatorio(request, intervalo)
    return render(request, "auditoria/auditoria.html", contexto)


async def _repassar_arquivo(
    request: HttpRequest, caminho: str, parametros: dict[str, str]
) -> HttpResponse:
    resposta = await cliente_api.chamar(request, "GET", caminho, params=parametros)
    if resposta.is_error:
        return HttpResponse(
            cliente_api.detalhe_do_erro(resposta),
            status=resposta.status_code,
            content_type="text/plain; charset=utf-8",
        )
    saida = HttpResponse(resposta.content)
    for cabecalho in CABECALHOS_DO_ARQUIVO:
        if cabecalho in resposta.headers:
            saida[cabecalho] = resposta.headers[cabecalho]
    return saida


@require_GET
async def exportar(request: HttpRequest) -> HttpResponse:
    """Exportação dos eventos filtrados em CSV ou JSON, repassada da API (RF-AUD-05).

    Args:
        request: Pedido com os filtros no formato da API e `formato` (links da tela).

    Returns:
        O arquivo da API com o tipo e o nome dela, ou o status e a mensagem da recusa.
    """
    return await _repassar_arquivo(request, "/auditoria/exportar", request.GET.dict())


@require_GET
async def relatorio_uso(request: HttpRequest) -> HttpResponse:
    """Relatório de uso por processo e usuário em CSV, repassado da API (RF-AUD-04).

    Args:
        request: Pedido com `formato`, `processo`, `usuario`, `inicio` e `fim`.

    Returns:
        O arquivo da API com o tipo e o nome dela, ou o status e a mensagem da recusa.
    """
    return await _repassar_arquivo(request, "/auditoria/relatorio-uso", request.GET.dict())
