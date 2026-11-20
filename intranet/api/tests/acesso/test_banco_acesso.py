"""Usuário de conexão, papel `lupa_app` e scripts de instalação (RF-ACE-05; RES-13)."""

import os
import runpy
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from apoio_comum import banco_vazio, migrar
from lupa_api.acesso import instalacao
from lupa_pipeline.config import Settings, get_settings
from lupa_pipeline.dominio.sessao import assumir_papel_aplicacao
from lupa_pipeline.dominio.visoes import VisaoAuditoria, VisaoUsuario

pytestmark = pytest.mark.integracao

SENHA_PAPEL = "senha-do-papel-de-teste"
SENHA_DESEMBARGADOR = "frase-longa-do-desembargador"
RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture
def papel_conexao(engine_teste: Engine) -> Iterator[Engine]:
    """Cria papel de login sem superusuário (nome único) e devolve um engine com ele."""
    nome = f"lupa_api_teste_{os.getpid()}"
    with engine_teste.begin() as conexao:
        instalacao.garantir_usuario_conexao(conexao, nome, "provisoria-123456")
        instalacao.garantir_usuario_conexao(conexao, nome, SENHA_PAPEL)
    url = make_url(str(engine_teste.url.render_as_string(hide_password=False)))
    engine = create_engine(url.set(username=nome, password=SENHA_PAPEL))
    yield engine
    engine.dispose()
    with engine_teste.begin() as conexao:
        conexao.execute(text(f'DROP OWNED BY "{nome}"'))
        conexao.execute(text(f'DROP ROLE "{nome}"'))


def test_usuario_de_conexao_nao_e_superusuario_e_assume_lupa_app(papel_conexao: Engine) -> None:
    """RES-13: sem superusuário, mas membro de `lupa_app`: `SET LOCAL ROLE` funciona."""
    with papel_conexao.begin() as conexao:
        atributos = conexao.execute(
            text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        ).one()
        assert tuple(atributos) == (False,)
        conexao.execute(text("SET LOCAL ROLE lupa_app"))
        assert conexao.execute(text("SELECT current_user")).scalar() == "lupa_app"


def test_lupa_app_nao_altera_a_auditoria(papel_conexao: Engine) -> None:
    """RF-AUD-03, RES-13: `lupa_app` não tem UPDATE em `link_evento_auditoria`."""
    with Session(papel_conexao) as session, session.begin():
        assumir_papel_aplicacao(session)
        with pytest.raises(DBAPIError, match="permission denied"):
            session.execute(text("UPDATE link_evento_auditoria SET resultado = 'x'"))


@pytest.fixture
def banco_migrado() -> Iterator[Engine]:
    """Banco recém-migrado só para este teste (sem usuários semeados)."""
    with banco_vazio("desembargador") as engine:
        migrar(engine, "head")
        yield engine


def _settings(engine: Engine, **extra: Any) -> Settings:
    return Settings(
        ambiente="teste",
        database_url=SecretStr(engine.url.render_as_string(hide_password=False)),
        minio_endpoint="localhost:9000",
        minio_bucket="lupa-autos",
        minio_access_key=SecretStr("x"),
        minio_secret_key=SecretStr("y"),
        **extra,
    )


def test_url_da_aplicacao_troca_usuario_quando_configurado(engine_teste: Engine) -> None:
    """RES-13: com usuário e senha da aplicação, a URL muda só nas credenciais."""
    sem = _settings(engine_teste)
    assert sem.url_banco_aplicacao() == sem.database_url.get_secret_value()
    com = _settings(engine_teste, db_usuario_app="lupa_api", db_senha_app=SecretStr("s3"))
    url = make_url(com.url_banco_aplicacao())
    assert (url.username, url.password, url.database) == (
        "lupa_api",
        "s3",
        engine_teste.url.database,
    )


def test_scripts_de_instalacao(engine_teste: Engine) -> None:
    """RES-13: `criar_usuario_banco` valida a configuração e é idempotente."""
    nome = f"lupa_api_script_{os.getpid()}"
    assert instalacao.criar_usuario_banco(_settings(engine_teste)) == 2
    configurado = _settings(engine_teste, db_usuario_app=nome, db_senha_app=SecretStr("s-123456"))
    assert instalacao.criar_usuario_banco(configurado) == 0
    with pytest.raises(ValueError, match="inválido"):
        with engine_teste.begin() as conexao:
            instalacao.garantir_usuario_conexao(conexao, "Nome Ruim;", "x")
    with engine_teste.begin() as conexao:
        conexao.execute(text(f'DROP OWNED BY "{nome}"'))
        conexao.execute(text(f'DROP ROLE "{nome}"'))


def _variaveis(nome: str, senha: str = SENHA_DESEMBARGADOR) -> dict[str, str]:
    return {instalacao.VARIAVEL_USUARIO: nome, instalacao.VARIAVEL_SENHA: senha}


def test_criar_desembargador_cria_um_e_nao_repete(banco_migrado: Engine) -> None:
    """RF-ACE-05: banco sem usuários ganha um desembargador temporário; o segundo não é criado."""
    configuracao = _settings(banco_migrado)
    assert instalacao.criar_desembargador_inicial(configuracao, {}) == 2
    assert (
        instalacao.criar_desembargador_inicial(configuracao, _variaveis("des.fraco", "curta")) == 2
    )
    assert instalacao.criar_desembargador_inicial(configuracao, _variaveis("Des Ruim")) == 2
    for nome in ("des.principal", "des.segundo"):
        assert instalacao.criar_desembargador_inicial(configuracao, _variaveis(nome)) == 0
    with Session(banco_migrado) as session:
        usuarios = session.execute(
            select(
                VisaoUsuario.nome_usuario, VisaoUsuario.papel, VisaoUsuario.troca_senha_obrigatoria
            )
        ).all()
        eventos = session.execute(select(VisaoAuditoria.acao, VisaoAuditoria.nome_usuario)).all()
    assert [tuple(u) for u in usuarios] == [("des.principal", "desembargador", True)]
    assert [tuple(e) for e in eventos] == [("usuario_criado", "des.principal")]


@pytest.mark.parametrize("script", ["criar_desembargador.py", "criar_usuario_banco.py"])
def test_scripts_rodam_como_programa(
    engine_teste: Engine, monkeypatch: pytest.MonkeyPatch, script: str
) -> None:
    """RF-ACE-05: os scripts leem o ambiente e terminam com código 2 sem as variáveis."""
    for variavel in (instalacao.VARIAVEL_USUARIO, instalacao.VARIAVEL_SENHA):
        monkeypatch.delenv(variavel, raising=False)
    monkeypatch.setenv("LUPA_DATABASE_URL", engine_teste.url.render_as_string(hide_password=False))
    monkeypatch.setenv("LUPA_DB_USUARIO_APP", "")
    get_settings.cache_clear()
    with pytest.raises(SystemExit) as saida:
        runpy.run_path(str(RAIZ / "scripts" / script), run_name="__main__")
    get_settings.cache_clear()
    assert saida.value.code == 2
