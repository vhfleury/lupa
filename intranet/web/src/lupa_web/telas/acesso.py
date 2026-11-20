"""Telas de acesso: login com TOTP, configuração do MFA, troca de senha e saída (A3, D11).

O desafio do TOTP vai em campo oculto do formulário do segundo passo; senha e código nunca são
devolvidos à página nem registrados em log.
"""

import contextlib
from typing import Any

import httpx
import segno
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods, require_POST

from lupa_web import cliente_api
from lupa_web.telas.sessao import Sessao, contexto_da_moldura, tela_autenticada

CAMINHO_PROCESSOS = "/processos"
ETAPA_CONFIGURAR = "configurar_mfa"
MENSAGEM_RECUSA = "Não foi possível entrar com os dados informados. Confira e tente novamente."
MENSAGEM_TENTATIVAS = "Muitas tentativas. Aguarde alguns minutos e tente novamente."
MENSAGEM_CONFIRMACAO = "A confirmação não confere com a nova senha."
MENSAGEM_SENHA_ATUAL = "Senha atual incorreta."
DETALHE_SENHA_ATUAL = "senha atual inválida"
ESCALA_QR = 5
ROTULO_QR = "QR code para cadastrar o autenticador do Lupa"


def desenhar_qr(uri: str) -> str:
    """SVG do QR code da URI `otpauth`, gerado no servidor (D11).

    Args:
        uri: URI de cadastro do autenticador.

    Returns:
        Elemento `<svg>` sem atributo `style`, para inserir no template.
    """
    return segno.make(uri, error="m").svg_inline(scale=ESCALA_QR, title=ROTULO_QR)


def mensagem_de_recusa(resposta: httpx.Response) -> str:
    """Recusa do login sem dizer qual campo errou (A3, passo 3).

    Args:
        resposta: Resposta de erro da API.

    Returns:
        Aviso de tentativas para 429; recusa genérica nos demais casos.
    """
    if resposta.status_code == httpx.codes.TOO_MANY_REQUESTS:
        return MENSAGEM_TENTATIVAS
    return MENSAGEM_RECUSA


def _pagina_senha(request: HttpRequest, erro: str = "", status: int = 200) -> HttpResponse:
    return render(request, "acesso/login.html", {"erro": erro, "pagina_login": True}, status=status)


def _pagina_codigo(
    request: HttpRequest, etapa: dict[str, Any], erro: str = "", status: int = 200
) -> HttpResponse:
    contexto = {"etapa": etapa, "erro": erro, "pagina_login": True}
    if etapa.get("etapa") == ETAPA_CONFIGURAR:
        contexto["qr_svg"] = desenhar_qr(str(etapa.get("uri_qr", "")))
    return render(request, "acesso/codigo.html", contexto, status=status)


async def _chamar_sem_sessao(
    request: HttpRequest, caminho: str, corpo: dict[str, str]
) -> httpx.Response:
    try:
        return await cliente_api.chamar(request, "POST", caminho, json=corpo)
    except cliente_api.SessaoExpiradaError as recusa:
        return recusa.resposta


@require_http_methods(["GET", "POST"])
async def login(request: HttpRequest) -> HttpResponse:
    """Primeiro passo: usuário e senha; leva ao código TOTP ou ao cadastro do MFA (A3.1).

    Args:
        request: Pedido do navegador.

    Returns:
        Formulário de senha, ou o do código com o desafio da API.
    """
    if request.method == "GET":
        return _pagina_senha(request)
    corpo = {
        "nome_usuario": request.POST.get("nome_usuario", "").strip(),
        "senha": request.POST.get("senha", ""),
    }
    resposta = await _chamar_sem_sessao(request, "/auth/login", corpo)
    if resposta.is_error:
        return _pagina_senha(request, mensagem_de_recusa(resposta), resposta.status_code)
    return _pagina_codigo(request, resposta.json())


@require_POST
async def login_codigo(request: HttpRequest) -> HttpResponse:
    """Segundo passo: confere o código ou confirma o autenticador e cria a sessão (A3.2, A3.4).

    Args:
        request: Pedido do navegador com o desafio em campo oculto.

    Returns:
        Redirecionamento para `/processos` ou `/trocar-senha`; o formulário com a recusa.
    """
    etapa = {
        chave: request.POST.get(chave, "") for chave in ("etapa", "desafio", "segredo", "uri_qr")
    }
    rota = "/auth/mfa/confirmar" if etapa["etapa"] == ETAPA_CONFIGURAR else "/auth/mfa"
    corpo = {"desafio": etapa["desafio"], "codigo": request.POST.get("codigo", "").strip()}
    resposta = await _chamar_sem_sessao(request, rota, corpo)
    if resposta.is_error:
        return _pagina_codigo(request, etapa, mensagem_de_recusa(resposta), resposta.status_code)
    destino = "/trocar-senha" if resposta.json().get("troca_senha_obrigatoria") else None
    return cliente_api.redirecionar(request, destino or CAMINHO_PROCESSOS)


def _pagina_troca(
    request: HttpRequest, sessao: Sessao, erro: str = "", status: int = 200
) -> HttpResponse:
    contexto = contexto_da_moldura(request, sessao) | {"erro": erro}
    return render(request, "acesso/trocar_senha.html", contexto, status=status)


async def _pedir_troca(request: HttpRequest, corpo: dict[str, str]) -> httpx.Response | None:
    try:
        return await cliente_api.chamar(request, "POST", "/auth/trocar-senha", json=corpo)
    except cliente_api.SessaoExpiradaError as recusa:
        if DETALHE_SENHA_ATUAL in recusa.resposta.text:
            return None
        raise


@require_http_methods(["GET", "POST"])
@tela_autenticada
async def trocar_senha(request: HttpRequest, sessao: Sessao) -> HttpResponse:
    """Troca da própria senha, obrigatória antes de qualquer tela com senha temporária.

    Args:
        request: Pedido do navegador.
        sessao: Dados da sessão.

    Returns:
        Formulário (com a mensagem do erro) ou redirecionamento para `/processos`.
    """
    if request.method == "GET":
        return _pagina_troca(request, sessao)
    nova = request.POST.get("nova_senha", "")
    if nova != request.POST.get("confirmacao", ""):
        return _pagina_troca(request, sessao, MENSAGEM_CONFIRMACAO, 422)
    corpo = {"senha_atual": request.POST.get("senha_atual", ""), "nova_senha": nova}
    resposta = await _pedir_troca(request, corpo)
    if resposta is None:
        return _pagina_troca(request, sessao, MENSAGEM_SENHA_ATUAL, 401)
    if resposta.is_error:
        mensagem = cliente_api.detalhe_do_erro(resposta)
        return _pagina_troca(request, sessao, mensagem, resposta.status_code)
    return cliente_api.redirecionar(request, CAMINHO_PROCESSOS)


@require_POST
async def sair(request: HttpRequest) -> HttpResponse:
    """Revoga a sessão na API e volta ao login, mesmo que a sessão já tenha expirado.

    Args:
        request: Pedido do navegador.

    Returns:
        Redirecionamento para `/login`, com o cookie apagado pela API.
    """
    with contextlib.suppress(cliente_api.SessaoExpiradaError):
        await cliente_api.chamar(request, "POST", "/auth/logout")
    return cliente_api.redirecionar_para_login(request)


@tela_autenticada
async def inicio(request: HttpRequest, sessao: Sessao) -> HttpResponse:
    """Raiz: com sessão válida, leva à lista de processos (A3.2).

    Args:
        request: Pedido do navegador.
        sessao: Dados da sessão.

    Returns:
        Redirecionamento para `/processos`.
    """
    return cliente_api.redirecionar(request, CAMINHO_PROCESSOS)
