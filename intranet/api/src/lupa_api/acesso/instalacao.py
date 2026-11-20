"""Tarefas de instalação chamadas pelos scripts: usuário de conexão e primeiro desembargador.

`garantir_usuario_conexao` cria (ou atualiza a senha de) um papel PostgreSQL com LOGIN, sem
superusuário, membro de `lupa_app` (só SELECT e INSERT). É o usuário que a API usa; o dono das
tabelas (usuário das migrações) fica restrito às migrações e a estes scripts.
`criar_desembargador_inicial` cria o primeiro desembargador (A14, passo 11; RF-ACE-05).
"""

import re
from collections.abc import Mapping
from datetime import UTC, datetime

from psycopg import sql
from sqlalchemy import Connection, create_engine
from sqlalchemy.orm import Session

from lupa_api.acesso.erros import RecusaAcessoError
from lupa_api.acesso.servico import Contexto, criar_desembargador
from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.sessao import PAPEL_APLICACAO, assumir_papel_aplicacao
from lupa_pipeline.logging import get_logger

PADRAO_PAPEL = re.compile(r"^[a-z_][a-z0-9_]{2,62}$")
VARIAVEL_USUARIO = "LUPA_DESEMBARGADOR_USUARIO"
VARIAVEL_SENHA = "LUPA_DESEMBARGADOR_SENHA"


def garantir_usuario_conexao(conexao: Connection, nome: str, senha: str) -> None:
    """Cria ou atualiza o usuário de conexão da aplicação, membro de `lupa_app`.

    Args:
        conexao: Conexão de um usuário com CREATEROLE (o dono das migrações).
        nome: Nome do papel de login.
        senha: Senha do papel.

    Raises:
        ValueError: Se o nome não for um identificador simples.
    """
    if not PADRAO_PAPEL.fullmatch(nome):
        raise ValueError("nome de papel inválido")
    cursor = conexao.connection.driver_connection.cursor()  # type: ignore[union-attr]
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (nome,))
    verbo = "ALTER" if cursor.fetchone() else "CREATE"
    cursor.execute(
        sql.SQL(
            verbo + " ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE INHERIT "
            "PASSWORD {}"
        ).format(sql.Identifier(nome), sql.Literal(senha))
    )
    cursor.execute(
        sql.SQL("GRANT {} TO {}").format(sql.Identifier(PAPEL_APLICACAO), sql.Identifier(nome))
    )


def criar_usuario_banco(settings: Settings) -> int:
    """Cria o usuário de conexão a partir de `LUPA_DB_USUARIO_APP` e `LUPA_DB_SENHA_APP`.

    Args:
        settings: Configuração; `database_url` deve ser do dono das tabelas.

    Returns:
        Código de saída (0 sucesso, 2 configuração ausente).
    """
    logger = get_logger(__name__)
    if not settings.db_usuario_app or settings.db_senha_app is None:
        logger.error("usuario_banco_sem_configuracao")
        return 2
    engine = create_engine(settings.database_url.get_secret_value())
    try:
        with engine.begin() as conexao:
            garantir_usuario_conexao(
                conexao, settings.db_usuario_app, settings.db_senha_app.get_secret_value()
            )
    finally:
        engine.dispose()
    logger.info("usuario_banco_pronto", papel=settings.db_usuario_app)
    return 0


def criar_desembargador_inicial(settings: Settings, ambiente: Mapping[str, str]) -> int:
    """Cria o primeiro desembargador a partir de `LUPA_DESEMBARGADOR_USUARIO` e `_SENHA`.

    Não faz nada se já existir desembargador. A senha exige troca no primeiro acesso e o MFA é
    cadastrado no primeiro login.

    Args:
        settings: Configuração da aplicação.
        ambiente: Variáveis de ambiente.

    Returns:
        Código de saída (0 criado ou já existente, 2 configuração ausente ou inválida).
    """
    logger = get_logger(__name__)
    nome, senha = ambiente.get(VARIAVEL_USUARIO), ambiente.get(VARIAVEL_SENHA)
    if not nome or not senha:
        logger.error("desembargador_sem_configuracao")
        return 2
    engine = create_engine(settings.url_banco_aplicacao())
    try:
        with Session(engine) as session, session.begin():
            assumir_papel_aplicacao(session)
            criado = criar_desembargador(
                session, nome, senha, Contexto(None, None, datetime.now(UTC))
            )
    except RecusaAcessoError as erro:
        logger.error("desembargador_invalido", motivo=erro.mensagem)
        return 2
    finally:
        engine.dispose()
    logger.info("desembargadores_criados", total=int(criado))
    return 0
