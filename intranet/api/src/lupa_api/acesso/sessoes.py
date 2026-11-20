"""Sessões server-side e desafios de MFA em hubs e satélites (A14; D6, D11).

O token entregue ao navegador tem 256 bits aleatórios; o banco guarda só o SHA-256 dele
(`hub_sessao.token_sha256`), de modo que uma cópia do banco não permite sequestrar sessões.
Expiração absoluta de 8 horas e por inatividade de 30 minutos. Toda mudança de estado é linha
nova de `sat_sessao_estado` ou `sat_desafio_mfa_estado`; `ultimo_acesso_em` só ganha linha nova
quando o último registro tem 60 s ou mais. O cookie é `HttpOnly`, `Secure` e `SameSite=Strict`.
"""

import secrets
from datetime import datetime, timedelta
from typing import Any

from fastapi import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.esquemas import calcular_hash
from lupa_pipeline.dominio.gravacao import gravar_hub, gravar_link, gravar_satelite
from lupa_pipeline.dominio.tabelas import (
    hub_desafio_mfa,
    hub_sessao,
    link_desafio_mfa_usuario,
    link_sessao_usuario,
    sat_desafio_mfa_estado,
    sat_sessao_estado,
)
from lupa_pipeline.dominio.visoes import VisaoDesafioMfa, VisaoSessao, VisaoUsuario, atual

NOME_COOKIE = "lupa_sessao"
BYTES_TOKEN = 32
DURACAO_ABSOLUTA = timedelta(hours=8)
INATIVIDADE_MAXIMA = timedelta(minutes=30)
INTERVALO_ULTIMO_ACESSO = timedelta(seconds=60)
DURACAO_DESAFIO = timedelta(minutes=5)
ORIGEM = "api.acesso"


def gerar_token() -> str:
    """Gera token aleatório de 256 bits.

    Returns:
        Token url-safe.
    """
    return secrets.token_urlsafe(BYTES_TOKEN)


def hash_do_token(token: str) -> str:
    """Deriva o valor armazenado a partir do token.

    Args:
        token: Token recebido do cliente.

    Returns:
        SHA-256 hexadecimal do token.
    """
    return calcular_hash(token)


def _gravar_estado_sessao(session: Session, hk_sessao: bytes, estado: dict[str, Any]) -> None:
    gravar_satelite(session, sat_sessao_estado, hk_sessao, estado, ORIGEM)


def _estado_de(sessao: VisaoSessao) -> dict[str, Any]:
    return {
        "papel": sessao.papel,
        "expira_em": sessao.expira_em,
        "ultimo_acesso_em": sessao.ultimo_acesso_em,
        "revogada": sessao.revogada,
        "ip_criacao": sessao.ip_criacao,
    }


def criar_sessao(session: Session, usuario: VisaoUsuario, ip: str | None, agora: datetime) -> str:
    """Cria a sessão do usuário (só depois do TOTP; A14, passo 7).

    Args:
        session: Sessão do banco.
        usuario: Usuário autenticado.
        ip: IP de criação.
        agora: Instante atual.

    Returns:
        Token a entregar no cookie.
    """
    token = gerar_token()
    hk_sessao = gravar_hub(session, hub_sessao, {"token_sha256": hash_do_token(token)}, ORIGEM)
    hks = {"hk_sessao": hk_sessao, "hk_usuario": usuario.hk_usuario}
    gravar_link(session, link_sessao_usuario, hks, ORIGEM)
    estado = {
        "papel": usuario.papel,
        "expira_em": agora + DURACAO_ABSOLUTA,
        "ultimo_acesso_em": agora,
        "revogada": False,
        "ip_criacao": ip,
    }
    _gravar_estado_sessao(session, hk_sessao, estado)
    return token


def _expirada(sessao: VisaoSessao, agora: datetime) -> bool:
    if sessao.expira_em is None or sessao.ultimo_acesso_em is None:
        return True
    return agora >= sessao.expira_em or agora - sessao.ultimo_acesso_em >= INATIVIDADE_MAXIMA


def carregar_sessao(session: Session, token: str, agora: datetime) -> VisaoSessao | None:
    """Carrega a sessão válida e renova o marcador de inatividade (A14, passos 8 e 9).

    Args:
        session: Sessão do banco.
        token: Token do cookie.
        agora: Instante atual.

    Returns:
        A sessão, ou None se inexistente, revogada ou expirada.
    """
    consulta = select(VisaoSessao).where(VisaoSessao.token_sha256 == hash_do_token(token))
    registro = session.scalars(atual(consulta)).one_or_none()
    if registro is None or registro.revogada or _expirada(registro, agora):
        return None
    ultimo = registro.ultimo_acesso_em
    if ultimo is not None and agora - ultimo >= INTERVALO_ULTIMO_ACESSO:
        _gravar_estado_sessao(
            session, registro.hk_sessao, _estado_de(registro) | {"ultimo_acesso_em": agora}
        )
    return registro


def revogar_sessao(session: Session, hk_sessao: bytes) -> None:
    """Revoga uma sessão gravando o estado `revogada` (A14, passo 10).

    Args:
        session: Sessão do banco.
        hk_sessao: Sessão a revogar.
    """
    consulta = select(VisaoSessao).where(VisaoSessao.hk_sessao == hk_sessao)
    registro = session.scalars(atual(consulta)).one_or_none()
    if registro is None or registro.revogada:
        return
    _gravar_estado_sessao(session, hk_sessao, _estado_de(registro) | {"revogada": True})


def revogar_sessoes_do_usuario(
    session: Session, hk_usuario: bytes, exceto: bytes | None = None
) -> None:
    """Revoga as sessões e consome os desafios pendentes do usuário (A14, passo 10).

    Args:
        session: Sessão do banco.
        hk_usuario: Usuário dono das sessões.
        exceto: Sessão a preservar.
    """
    sessoes = session.scalars(
        atual(
            select(VisaoSessao).where(
                VisaoSessao.hk_usuario == hk_usuario, VisaoSessao.revogada.is_(False)
            )
        )
    ).all()
    for registro in sessoes:
        if registro.hk_sessao != exceto:
            _gravar_estado_sessao(
                session, registro.hk_sessao, _estado_de(registro) | {"revogada": True}
            )
    desafios = session.scalars(
        atual(
            select(VisaoDesafioMfa).where(
                VisaoDesafioMfa.hk_usuario == hk_usuario, VisaoDesafioMfa.consumido.is_(False)
            )
        )
    ).all()
    for desafio in desafios:
        consumir_desafio(session, desafio)


def criar_desafio(session: Session, usuario: VisaoUsuario, agora: datetime) -> str:
    """Cria o desafio do segundo passo do login, válido por 5 minutos (A14, passo 5).

    Args:
        session: Sessão do banco.
        usuario: Usuário que acertou a senha.
        agora: Instante atual.

    Returns:
        Token do desafio, a devolver ao cliente.
    """
    token = gerar_token()
    chave = {"token_sha256": hash_do_token(token)}
    hk_desafio = gravar_hub(session, hub_desafio_mfa, chave, ORIGEM)
    hks = {"hk_desafio_mfa": hk_desafio, "hk_usuario": usuario.hk_usuario}
    gravar_link(session, link_desafio_mfa_usuario, hks, ORIGEM)
    estado = {"papel": usuario.papel, "expira_em": agora + DURACAO_DESAFIO, "consumido": False}
    gravar_satelite(session, sat_desafio_mfa_estado, hk_desafio, estado, ORIGEM)
    return token


def carregar_desafio(session: Session, token: str, agora: datetime) -> VisaoDesafioMfa | None:
    """Carrega o desafio ainda válido (A14, passo 6).

    Args:
        session: Sessão do banco.
        token: Token do desafio.
        agora: Instante atual.

    Returns:
        O desafio, ou None se inexistente, consumido ou expirado.
    """
    consulta = select(VisaoDesafioMfa).where(VisaoDesafioMfa.token_sha256 == hash_do_token(token))
    desafio = session.scalars(atual(consulta)).one_or_none()
    if desafio is None or desafio.consumido or desafio.expira_em is None:
        return None
    if agora >= desafio.expira_em:
        return None
    return desafio


def consumir_desafio(session: Session, desafio: VisaoDesafioMfa) -> None:
    """Marca o desafio como consumido (A14, passo 7).

    Args:
        session: Sessão do banco.
        desafio: Desafio corrente.
    """
    estado = {"papel": desafio.papel, "expira_em": desafio.expira_em, "consumido": True}
    gravar_satelite(session, sat_desafio_mfa_estado, desafio.hk_desafio_mfa, estado, ORIGEM)


def definir_cookie(response: Response, token: str) -> None:
    """Grava o cookie de sessão com as flags de segurança.

    Args:
        response: Resposta HTTP.
        token: Token da sessão.
    """
    response.set_cookie(
        NOME_COOKIE,
        token,
        max_age=int(DURACAO_ABSOLUTA.total_seconds()),
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )


def apagar_cookie(response: Response) -> None:
    """Remove o cookie de sessão.

    Args:
        response: Resposta HTTP.
    """
    response.delete_cookie(NOME_COOKIE, httponly=True, secure=True, samesite="strict", path="/")
