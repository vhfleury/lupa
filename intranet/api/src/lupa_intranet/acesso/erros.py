"""Erros esperados dos casos de uso de acesso, cada um com seu status HTTP.

São recusas previstas (credencial errada, falta de permissão): a transação da requisição é
confirmada mesmo assim, para que o evento de auditoria da recusa não se perca.
"""

from typing import ClassVar

from fastapi import Request
from fastapi.responses import JSONResponse


class RecusaAcessoError(Exception):
    """Base dos erros esperados; `status` vira o código HTTP e a mensagem vai no `detail`."""

    status: ClassVar[int] = 400

    def __init__(self, mensagem: str) -> None:
        """Cria o erro.

        Args:
            mensagem: Texto devolvido ao cliente, sem dados sensíveis.
        """
        super().__init__(mensagem)
        self.mensagem = mensagem


class CredenciaisInvalidasError(RecusaAcessoError):
    """Usuário inexistente, inativo, senha errada ou código TOTP errado (resposta idêntica)."""

    status = 401


class NaoAutenticadoError(RecusaAcessoError):
    """Sem sessão válida."""

    status = 401


class LoginBloqueadoError(RecusaAcessoError):
    """Excesso de falhas recentes."""

    status = 429


class PermissaoNegadaError(RecusaAcessoError):
    """O papel não permite a ação."""

    status = 403


class TrocaSenhaObrigatoriaError(RecusaAcessoError):
    """O usuário precisa trocar a senha antes de qualquer outra ação."""

    status = 403


class NaoEncontradoError(RecusaAcessoError):
    """Objeto inexistente ou fora do alcance do usuário (não revela qual dos dois)."""

    status = 404


class ConflitoError(RecusaAcessoError):
    """Conflito com estado existente (nome de usuário em uso)."""

    status = 409


class DadosInvalidosError(RecusaAcessoError):
    """Entrada recusada por regra de negócio (senha fraca, papel inválido)."""

    status = 422


async def tratar_erro_acesso(_request: Request, erro: Exception) -> JSONResponse:
    """Converte recusas previstas em resposta JSON com o status do erro.

    Args:
        _request: Requisição (não usada).
        erro: `RecusaAcessoError` lançado pelo caso de uso.

    Returns:
        Resposta `{"detail": mensagem}`.
    """
    if not isinstance(erro, RecusaAcessoError):
        raise erro
    return JSONResponse(status_code=erro.status, content={"detail": erro.mensagem})
