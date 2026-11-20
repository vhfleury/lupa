"""Gestão de assessores pelo desembargador: criar, desativar, reativar e resetar senha e MFA.

A senha temporária aparece uma única vez, na resposta da criação ou do reset, com
`Cache-Control: no-store`, e nunca vai para a URL. Para quem não tem `gerir_assessor` a API
responde 403 e o middleware mostra a página de acesso negado (RF-INT-02, RF-INT-03).
"""

from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods, require_POST

from lupa_web import cliente_api
from lupa_web.telas.sessao import (
    ROTULO_PAPEL,
    Sessao,
    contexto_da_moldura,
    nao_encontrado,
    obter,
    tela_autenticada,
    tem,
)

COLUNAS_USUARIOS = ("Usuário", "Papel", "Situação", "Autenticador", "Ações")
AVISOS = {
    "desativar": "desativado",
    "reativar": "reativado",
    "resetar-senha": "com senha temporária nova",
    "resetar-mfa": "com autenticador apagado; o próximo login cadastra outro",
}
ACOES_SEM_CONFIRMACAO = frozenset({"reativar", "resetar-senha", "resetar-mfa"})


def acoes_sobre(sessao: Sessao, usuario: dict[str, Any]) -> dict[str, bool]:
    """Ações que a sessão pode pedir sobre o usuário (só esconde botões; a API reconfere).

    Args:
        sessao: Dados da sessão.
        usuario: Usuário da lista.

    Returns:
        `gerir` (desativar e reativar) e `resetar` (senha e autenticador).
    """
    if usuario["id"] == sessao.get("usuario_id") or usuario["papel"] != "assessor":
        return {"gerir": False, "resetar": False}
    return {"gerir": tem(sessao, "gerir_assessor"), "resetar": tem(sessao, "resetar_assessor")}


def linha_do_usuario(sessao: Sessao, usuario: dict[str, Any]) -> dict[str, Any]:
    """Dados de uma linha da tabela de usuários.

    Args:
        sessao: Dados da sessão.
        usuario: Usuário da API.

    Returns:
        O usuário com papel, situação, autenticador e ações permitidas.
    """
    situacao = "Ativo" if usuario["ativo"] else "Inativo"
    if usuario["troca_senha_obrigatoria"]:
        situacao += " · troca de senha pendente"
    return usuario | {
        "papel_rotulo": ROTULO_PAPEL.get(usuario["papel"], usuario["papel"]),
        "situacao": situacao,
        "autenticador": "Cadastrado" if usuario["mfa_confirmado"] else "Pendente",
        "acoes": acoes_sobre(sessao, usuario),
    }


def aviso_da_acao(acao: str, usuarios: list[dict[str, Any]], usuario_id: str) -> str:
    """Confirmação da última ação, com o nome do usuário.

    Args:
        acao: Ação feita (`?aviso=`).
        usuarios: Usuários da lista.
        usuario_id: Usuário alvo (`?usuario=`).

    Returns:
        A mensagem, ou texto vazio para ação ou usuário desconhecido.
    """
    nome = next((u["nome_usuario"] for u in usuarios if u["id"] == usuario_id), None)
    if nome is None or acao not in AVISOS:
        return ""
    return f"Usuário {nome} {AVISOS[acao]}."


async def _usuarios(request: HttpRequest) -> list[dict[str, Any]]:
    usuarios: list[dict[str, Any]] = (await obter(request, "/usuarios")).json()
    return usuarios


async def _pagina(
    request: HttpRequest,
    sessao: Sessao,
    mensagens: dict[str, Any],
    status: int = 200,
) -> HttpResponse:
    usuarios = await _usuarios(request)
    aviso = aviso_da_acao(request.GET.get("aviso", ""), usuarios, request.GET.get("usuario", ""))
    contexto = contexto_da_moldura(request, sessao) | {
        "usuarios": [linha_do_usuario(sessao, u) for u in usuarios],
        "colunas_usuarios": COLUNAS_USUARIOS,
        "aviso": aviso,
        **mensagens,
    }
    resposta = render(request, "usuarios/usuarios.html", contexto, status=status)
    if "senha" in mensagens:
        resposta["Cache-Control"] = "no-store"
    return resposta


def _senha(criado: dict[str, Any]) -> dict[str, str]:
    return {"nome": criado["nome_usuario"], "valor": criado["senha_temporaria"]}


@require_http_methods(["GET", "POST"])
@tela_autenticada
async def usuarios(request: HttpRequest, sessao: Sessao) -> HttpResponse:
    """Lista de usuários (GET) e criação de assessor (POST) (RF-ACE-03).

    Args:
        request: GET com `?aviso=` e `?usuario=` depois de uma ação; POST com `nome_usuario`.
        sessao: Dados da sessão.

    Returns:
        A lista; depois da criação, a lista com a senha temporária exibida uma vez.
    """
    if request.method == "GET":
        return await _pagina(request, sessao, {})
    corpo = {"nome_usuario": request.POST.get("nome_usuario", "").strip(), "papel": "assessor"}
    resposta = await cliente_api.chamar(request, "POST", "/usuarios", json=corpo)
    if resposta.is_error:
        erro = cliente_api.detalhe_do_erro(resposta)
        return await _pagina(request, sessao, {"erro": erro}, resposta.status_code)
    criado = resposta.json()
    sucesso = f"Usuário {criado['nome_usuario']} criado."
    return await _pagina(request, sessao, {"sucesso": sucesso, "senha": _senha(criado)})


async def _confirmar_desativacao(
    request: HttpRequest, sessao: Sessao, usuario_id: str
) -> HttpResponse:
    alvo = next((u for u in await _usuarios(request) if u["id"] == usuario_id), None)
    if alvo is None:
        return nao_encontrado(request, sessao)
    contexto = contexto_da_moldura(request, sessao) | {
        "titulo": "Desativar usuário?",
        "mensagem": (
            f"{alvo['nome_usuario']} perde o acesso imediatamente e as sessões abertas são "
            "encerradas. Dá para reativar depois."
        ),
        "rotulo_confirmar": "Desativar",
        "perigo": True,
        "acao": f"/usuarios/{usuario_id}/desativar",
        "voltar": "/usuarios",
    }
    return render(request, "usuarios/desativar.html", contexto)


async def _agir(request: HttpRequest, sessao: Sessao, usuario_id: str, acao: str) -> HttpResponse:
    caminho = f"/usuarios/{usuario_id}/{acao}"
    resposta = await cliente_api.chamar(request, "POST", caminho, json={})
    if resposta.is_error:
        erro = cliente_api.detalhe_do_erro(resposta)
        return await _pagina(request, sessao, {"erro": erro}, resposta.status_code)
    alterado = resposta.json()
    if "senha_temporaria" in alterado:
        sucesso = f"Usuário {alterado['nome_usuario']} {AVISOS[acao]}."
        return await _pagina(request, sessao, {"sucesso": sucesso, "senha": _senha(alterado)})
    return cliente_api.redirecionar(request, f"/usuarios?aviso={acao}&usuario={usuario_id}")


@require_http_methods(["GET", "POST"])
@tela_autenticada
async def desativar(request: HttpRequest, sessao: Sessao, usuario_id: str) -> HttpResponse:
    """Confirmação (GET) e desativação (POST) de um assessor.

    Args:
        request: Pedido do navegador.
        sessao: Dados da sessão.
        usuario_id: Identificador público do usuário.

    Returns:
        Página de confirmação, redirecionamento à lista com o aviso ou a lista com o erro.
    """
    if request.method == "GET":
        return await _confirmar_desativacao(request, sessao, usuario_id)
    return await _agir(request, sessao, usuario_id, "desativar")


@require_POST
@tela_autenticada
async def agir(request: HttpRequest, sessao: Sessao, usuario_id: str, acao: str) -> HttpResponse:
    """Reativa ou reseta a senha ou o autenticador de um assessor.

    Args:
        request: Pedido do navegador.
        sessao: Dados da sessão.
        usuario_id: Identificador público do usuário.
        acao: `reativar`, `resetar-senha` ou `resetar-mfa`.

    Returns:
        Redirecionamento à lista com o aviso, a lista com a senha temporária nova, a lista com
        o erro ou 404 para ação desconhecida.
    """
    if acao not in ACOES_SEM_CONFIRMACAO:
        return nao_encontrado(request, sessao)
    return await _agir(request, sessao, usuario_id, acao)
