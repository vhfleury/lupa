"""Fábrica da aplicação FastAPI."""

import logging

from fastapi import FastAPI

from lupa_intranet.acesso import rotas as rotas_acesso
from lupa_intranet.acesso.erros import RecusaAcessoError, tratar_erro_acesso
from lupa_intranet.agente.cliente_roteirizado import criar_cliente
from lupa_intranet.api.banco import configurar_banco
from lupa_intranet.api.middleware import auditoria_middleware, request_id_middleware
from lupa_intranet.api.rotas import (
    achados,
    chat,
    descarte,
    dossie,
    ingestao,
    pecas,
    processos,
    saude,
    visualizador,
)
from lupa_intranet.api.rotas import revisao as rotas_revisao
from lupa_intranet.auditoria import rotas as rotas_auditoria
from lupa_intranet.auditoria.geoip import criar_resolvedor
from lupa_pipeline.config import Settings, get_settings
from lupa_pipeline.ingestao.storage import criar_storage
from lupa_pipeline.logging import configurar_logging, get_logger


def _preservar_sigilo_url(registro: logging.LogRecord) -> bool:
    """Retém IP, método, versão HTTP e status do Uvicorn, que também recebe a URL bruta."""
    campos = registro.args
    if not isinstance(campos, tuple) or len(campos) != 5:
        return False
    ip, metodo, _url, versao, status = campos
    registro.args = (ip, metodo, "[rota]", versao, status)
    return True


def create_app(settings: Settings | None = None) -> FastAPI:
    """Cria a aplicação, validando a configuração antes de tudo.

    Args:
        settings: Configuração explícita; se ausente, lida do ambiente.

    Returns:
        A aplicação FastAPI configurada.

    Raises:
        pydantic.ValidationError: Se faltar variável obrigatória.
    """
    configuracao = settings or get_settings()
    configurar_logging(nivel=configuracao.log_level, estrito=configuracao.ambiente == "teste")
    logging.getLogger("uvicorn.access").addFilter(_preservar_sigilo_url)
    app = FastAPI(title="Lupa", version="0.2.0")
    app.dependency_overrides[get_settings] = lambda: configuracao
    configurar_banco(app, configuracao)
    app.state.resolvedor = criar_resolvedor(configuracao)
    app.state.storage = criar_storage(configuracao)
    app.state.cliente_agente = criar_cliente(configuracao)
    app.add_exception_handler(RecusaAcessoError, tratar_erro_acesso)
    app.middleware("http")(auditoria_middleware)
    app.middleware("http")(request_id_middleware)
    for modulo in (
        saude,
        rotas_acesso,
        processos,
        rotas_auditoria,
        ingestao,
        pecas,
        achados,
        chat,
        dossie,
        rotas_revisao,
        visualizador,
        descarte,
    ):
        app.include_router(modulo.router)
    get_logger(__name__).info("aplicacao_iniciada", ambiente=configuracao.ambiente)
    return app
