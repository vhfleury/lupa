"""Dependências FastAPI de autenticação e autorização, verificadas no servidor a cada requisição.

`usuario_autenticado` carrega a sessão do cookie (A14, passos 8 e 9) e devolve o `Ator`.
`exige_papel` confere a matriz de `papeis.py` (RF-ACE-03). `exige_processo` carrega o processo
do caminho pela view `v_processo` e responde 404 quando ele não existe ou foi descartado,
registrando a tentativa. Responsável não restringe acesso (RF-PRO-03): qualquer usuário vê
qualquer processo.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from lupa_intranet.acesso import sessoes
from lupa_intranet.acesso.erros import (
    NaoAutenticadoError,
    NaoEncontradoError,
    PermissaoNegadaError,
    TrocaSenhaObrigatoriaError,
)
from lupa_intranet.acesso.papeis import Permissao, tem_permissao
from lupa_intranet.acesso.servico import Ator, Contexto, auditar, ler_usuario
from lupa_intranet.api.banco import obter_sessao_banco
from lupa_intranet.auditoria.eventos import AcaoAuditoria, ResultadoEvento
from lupa_pipeline.dominio.enums import PapelUsuario, StatusProcesso
from lupa_pipeline.dominio.esquemas import calcular_hash
from lupa_pipeline.dominio.visoes import VisaoProcesso

SessaoBanco = Annotated[Session, Depends(obter_sessao_banco)]


def relogio() -> datetime:
    """Instante atual em UTC (dependência substituível nos testes).

    Returns:
        Agora, com fuso.
    """
    return datetime.now(UTC)


def contexto_requisicao(request: Request, agora: Annotated[datetime, Depends(relogio)]) -> Contexto:
    """Monta IP, localização e instante da requisição.

    O IP é o da conexão; atrás de proxy reverso, configure o uvicorn com `--proxy-headers` e
    `--forwarded-allow-ips` apenas para o proxy confiável.

    Args:
        request: Requisição corrente.
        agora: Instante atual.

    Returns:
        Contexto para auditoria.
    """
    ip = request.client.host if request.client else None
    return Contexto(ip=ip, localizacao=request.app.state.resolvedor.resolver(ip), agora=agora)


ContextoReq = Annotated[Contexto, Depends(contexto_requisicao)]


def _ator(session: Session, request: Request, ctx: Contexto) -> Ator:
    token = request.cookies.get(sessoes.NOME_COOKIE)
    registro = sessoes.carregar_sessao(session, token, ctx.agora) if token else None
    if registro is None:
        raise NaoAutenticadoError("não autenticado")
    usuario = ler_usuario(session, registro.hk_usuario)
    if usuario is None or not usuario.ativo or usuario.papel is None:
        raise NaoAutenticadoError("não autenticado")
    ator = Ator(
        hk_usuario=usuario.hk_usuario,
        usuario_id=usuario.id,
        papel=PapelUsuario(usuario.papel),
        nome_usuario=usuario.nome_usuario,
        hk_sessao=registro.hk_sessao,
        troca_senha_obrigatoria=bool(usuario.troca_senha_obrigatoria),
    )
    request.state.ator = ator
    return ator


def usuario_autenticado_permitindo_troca(
    request: Request, session: SessaoBanco, ctx: ContextoReq
) -> Ator:
    """Autentica sem barrar quem precisa trocar a senha (só para a rota de troca).

    Args:
        request: Requisição corrente.
        session: Sessão do banco.
        ctx: Contexto da requisição.

    Returns:
        O ator autenticado.

    Raises:
        NaoAutenticadoError: Sem sessão válida.
    """
    return _ator(session, request, ctx)


def usuario_autenticado(
    ator: Annotated[Ator, Depends(usuario_autenticado_permitindo_troca)],
) -> Ator:
    """Autentica e barra quem tem troca de senha pendente (RF-ACE-04).

    Args:
        ator: Ator carregado da sessão.

    Returns:
        O ator autenticado.

    Raises:
        TrocaSenhaObrigatoriaError: Se a troca de senha estiver pendente.
    """
    if ator.troca_senha_obrigatoria:
        raise TrocaSenhaObrigatoriaError("troca de senha obrigatória")
    return ator


AtorAutenticado = Annotated[Ator, Depends(usuario_autenticado)]


def exige_papel(permissao: Permissao) -> Callable[[Ator], Ator]:
    """Cria dependência que exige que o papel do ator tenha a permissão.

    Args:
        permissao: Permissão exigida.

    Returns:
        Dependência que devolve o ator ou lança `PermissaoNegadaError`.
    """

    def _dependencia(ator: AtorAutenticado) -> Ator:
        if not tem_permissao(ator.papel, permissao):
            raise PermissaoNegadaError("ação não permitida para o seu papel")
        return ator

    return _dependencia


def carregar_processo(
    processo_id: str,
    ator: AtorAutenticado,
    session: SessaoBanco,
    ctx: ContextoReq,
) -> VisaoProcesso:
    """Lê o processo pelo identificador público, auditando a tentativa que não o encontra."""
    consulta = select(VisaoProcesso).where(VisaoProcesso.id == processo_id.lower())
    processo = session.scalars(consulta).one_or_none()
    if processo is None:
        identificador = processo_id.lower()
        publico = len(identificador) == 64 and all(c in "0123456789abcdef" for c in identificador)
        auditar(
            session,
            ctx,
            AcaoAuditoria.PROCESSO_ABERTO,
            ResultadoEvento.NEGADO,
            hk_usuario=ator.hk_usuario,
            objeto_tipo="processo" if publico else "identificador_sha256",
            objeto_id=identificador if publico else calcular_hash(processo_id),
        )
        raise NaoEncontradoError("processo não encontrado")
    return processo


def exige_processo(
    processo: Annotated[VisaoProcesso, Depends(carregar_processo)], request: Request
) -> VisaoProcesso:
    """Exige um processo disponível para leitura (RF-PRO-05)."""
    if processo.status == StatusProcesso.DESCARTADO.value:
        raise NaoEncontradoError("processo descartado")
    request.state.processo = processo.hk_processo
    return processo
