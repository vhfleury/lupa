"""Cria o desembargador do E2E pela instalação A14 e imprime seu nome e senha temporária."""

import os
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from lupa_api.acesso.senhas import gerar_senha_temporaria
from lupa_api.acesso.servico import Contexto, criar_desembargador
from lupa_pipeline.config import get_settings
from lupa_pipeline.dominio.sessao import assumir_papel_aplicacao


def preparar() -> tuple[str, str]:
    """Entrega uma credencial nova, sem redefinir a conta de outra execução."""
    settings = get_settings()
    if settings.ambiente not in {"teste", "desenvolvimento"}:
        raise SystemExit("e2e_preparar exige ambiente de teste ou desenvolvimento")
    nome = os.environ.get("LUPA_DESEMBARGADOR_USUARIO") or "desembargador.e2e"
    senha = gerar_senha_temporaria()
    engine = create_engine(settings.url_banco_aplicacao())
    try:
        with Session(engine) as sessao, sessao.begin():
            assumir_papel_aplicacao(sessao)
            criado = criar_desembargador(
                sessao, nome, senha, Contexto(None, None, datetime.now(UTC))
            )
            if not criado:
                raise SystemExit("já existe um desembargador. Inicie o E2E em uma stack nova.")
    finally:
        engine.dispose()
    return nome, senha


if __name__ == "__main__":
    print(*preparar(), sep="\n")
