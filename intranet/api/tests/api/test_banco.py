"""Testes da sessão de banco por requisição (confirmação em recusas, desfazer em erros)."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from lupa_api.acesso.erros import NaoEncontradoError
from lupa_api.api.banco import sessao_aplicacao
from lupa_pipeline.dominio.gravacao import gravar_hub
from lupa_pipeline.dominio.tabelas import hub_usuario
from lupa_pipeline.dominio.visoes import VisaoUsuario

pytestmark = pytest.mark.integracao


def _existe(engine: Engine, hk: bytes) -> bool:
    with Session(engine) as session:
        return session.get(VisaoUsuario, hk) is not None


def _inserir(session: Session) -> bytes:
    return gravar_hub(session, hub_usuario, {"nome_usuario": f"teste.{uuid4().hex}"}, "teste")


@pytest.mark.parametrize(
    ("erro", "confirma"),
    [
        (NaoEncontradoError("x"), True),
        (HTTPException(status_code=404), True),
        (RuntimeError("falha inesperada"), False),
    ],
)
def test_recusa_prevista_confirma_e_erro_inesperado_desfaz(
    fabrica_sessao: sessionmaker[Session], engine_teste: Engine, erro: Exception, confirma: bool
) -> None:
    """`RecusaAcessoError`/`HTTPException` confirmam; outra exceção desfaz."""
    gravado: list[bytes] = []
    with pytest.raises(type(erro)), sessao_aplicacao(fabrica_sessao) as session:
        assert session.execute(text("SELECT current_user")).scalar() == "lupa_app"
        gravado.append(_inserir(session))
        raise erro
    assert _existe(engine_teste, gravado[0]) is confirma
