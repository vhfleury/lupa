"""Contexto de cifra por requisição e configuração do cofre da aplicação (D14; RF-SEG-01).

Cada requisição ganha um `ContextoCifra` vazio. `exige_processo` abre a DEK do processo do
caminho (`ativar_processo`); campos de outros processos lidos pelas views são abertos pelo
carregador, que lê `v_processo`. No fim da requisição as DEKs abertas são descartadas.
"""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from lupa_pipeline.config import Settings
from lupa_pipeline.seguranca.chaves import carregador_sql
from lupa_pipeline.seguranca.cofre import criar_cofre
from lupa_pipeline.seguranca.contexto import contexto_cifra, definir_cofre


def configurar_cifra(app: FastAPI, settings: Settings) -> None:
    """Cria o cofre da aplicação e o registra para o processo Python.

    Args:
        app: Aplicação.
        settings: Configuração (`cofre_backend`, `vault_*`).
    """
    app.state.cofre = criar_cofre(settings)
    definir_cofre(app.state.cofre)


async def cifra_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Abre o contexto de cifra da requisição.

    Args:
        request: Requisição recebida.
        call_next: Próximo manipulador da cadeia.

    Returns:
        A resposta.
    """
    with contexto_cifra(carregador_sql(lambda: request.app.state.fabrica_sessao())):
        return await call_next(request)
