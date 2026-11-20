"""Aplicação ASGI do front, servida pelo uvicorn (D1).

O Django não trata o ciclo de vida do ASGI; este módulo responde a ele, põe na partida os
temporários no volume dos pendentes, fecha no encerramento o cliente da API e repassa ao Django os
pedidos HTTP.
"""

import os
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from django.core.asgi import get_asgi_application

from lupa_web.cliente_api import encerrar_cliente
from lupa_web.envios_pendentes import preparar_temporarios

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lupa_web.configuracao")

Escopo = dict[str, Any]
Receber = Callable[[], Awaitable[dict[str, Any]]]
Enviar = Callable[[Mapping[str, Any]], Awaitable[None]]

aplicacao_django = get_asgi_application()


async def ciclo_de_vida(receive: Receber, send: Enviar) -> None:
    """Atende `lifespan.startup` e `lifespan.shutdown`.

    Na partida prepara os temporários no volume dos pendentes; no encerramento fecha o cliente da
    API.

    Args:
        receive: Canal de entrada do servidor ASGI.
        send: Canal de saída do servidor ASGI.
    """
    while True:
        mensagem = await receive()
        if mensagem["type"] == "lifespan.startup":
            preparar_temporarios()
            await send({"type": "lifespan.startup.complete"})
        elif mensagem["type"] == "lifespan.shutdown":
            await encerrar_cliente()
            await send({"type": "lifespan.shutdown.complete"})
            return


async def application(scope: Escopo, receive: Receber, send: Enviar) -> None:
    """Ponto de entrada ASGI: ciclo de vida aqui, HTTP no Django.

    Args:
        scope: Escopo da conexão ASGI.
        receive: Canal de entrada do servidor ASGI.
        send: Canal de saída do servidor ASGI.
    """
    if scope["type"] == "lifespan":
        await ciclo_de_vida(receive, send)
        return
    await aplicacao_django(scope, receive, send)
