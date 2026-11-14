"""Fábricas e fixtures comuns aos testes da pipeline e da intranet (todas sintéticas).

O banco de teste é um database próprio no serviço `db`, migrado até a cabeça (Data Vault da
0.2); `sessao` roda cada teste numa transação desfeita ao final.
"""

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import Engine, create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

import lupa_pipeline.migrations
from lupa_pipeline.config import Settings, get_settings
from lupa_pipeline.dominio.cnj import calcular_digito_verificador
from lupa_pipeline.dominio.enums import PapelUsuario, TipoFato
from lupa_pipeline.dominio.esquemas import Evidencia, Fato
from lupa_pipeline.dominio.gravacao import gravar_hub, gravar_satelite
from lupa_pipeline.dominio.tabelas import hub_usuario, sat_usuario_cadastro, sat_usuario_credencial
from lupa_pipeline.dominio.visoes import VisaoAuditoria

VARIAVEIS_FICTICIAS = {
    "LUPA_AMBIENTE": "teste",
    "LUPA_DATABASE_URL": "postgresql+psycopg://lupa:ficticia@localhost:5432/lupa",
    "LUPA_MINIO_ENDPOINT": "localhost:9000",
    "LUPA_MINIO_BUCKET": "lupa-autos",
    "LUPA_MINIO_ACCESS_KEY": "lupa-ficticio",
    "LUPA_MINIO_SECRET_KEY": "segredo-ficticio",
}

# Etapa 7: os testes usam o cofre em memória (o contrato com o Vault real fica em
# tests/seguranca, marcado `integracao`, com as variáveis LUPA_VAULT_* do contêiner).
os.environ["LUPA_COFRE_BACKEND"] = "memoria"

CAMINHO_ALEMBIC_INI = Path(lupa_pipeline.migrations.__file__).parent / "alembic.ini"
TEXTO_PAGINA = "Certidão: intimado o defensor em 10/03/2025. Recurso interposto em 14/03/2025."

FabricaFato = Callable[..., Fato]


@pytest.fixture
def ambiente_ficticio(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Define variáveis de ambiente fictícias e limpa o cache de configuração."""
    for chave, valor in VARIAVEIS_FICTICIAS.items():
        monkeypatch.setenv(chave, os.environ.get(chave, valor))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings_ficticias() -> Settings:
    """Configuração fictícia para testes sem depender do ambiente."""
    return Settings(
        ambiente="teste",
        database_url=SecretStr(VARIAVEIS_FICTICIAS["LUPA_DATABASE_URL"]),
        minio_endpoint="localhost:9000",
        minio_bucket="lupa-autos",
        minio_access_key=SecretStr("lupa-ficticio"),
        minio_secret_key=SecretStr("segredo-ficticio"),
        timeout_saude_segundos=0.5,
    )


def gerar_numero_cnj(sequencial: int) -> str:
    """Gera um número CNJ sintético válido (justiça estadual, TR 09).

    Args:
        sequencial: Número sequencial do processo.

    Returns:
        Número formatado com dígito verificador correto.
    """
    seq, ano, justica, tribunal, origem = f"{sequencial:07d}", "2025", "8", "09", "0001"
    digito = calcular_digito_verificador(seq, ano, justica, tribunal, origem)
    return f"{seq}-{digito}.{ano}.{justica}.{tribunal}.{origem}"


@pytest.fixture
def fabrica_fato() -> FabricaFato:
    """Fábrica de `Fato` sintético com uma evidência, sem banco.

    Returns:
        Função `(processo_id=..., pagina_id=..., tipo=..., valor=...) -> Fato`.
    """

    def _criar(
        processo_id: UUID | None = None,
        pagina_id: UUID | None = None,
        tipo: TipoFato = TipoFato.DATA_INTIMACAO_DEFESA,
        valor: Any = "2025-03-10",
    ) -> Fato:
        trecho = "intimado o defensor em 10/03/2025"
        inicio = TEXTO_PAGINA.index(trecho)
        evidencia = Evidencia(
            pagina_id=pagina_id or uuid4(),
            trecho=trecho,
            inicio=inicio,
            fim=inicio + len(trecho),
        )
        return Fato(
            processo_id=processo_id or uuid4(),
            tipo=tipo,
            valor=valor,
            evidencias=(evidencia,),
            extraido_por="regra_teste",
            versao_extrator="0.0.1",
            confianca=0.9,
        )

    return _criar


def _url_banco_principal() -> str | None:
    return os.environ.get("LUPA_DATABASE_URL")


@contextmanager
def banco_vazio(sufixo: str) -> Iterator[Engine]:
    """Cria um database de teste vazio (`lupa_teste_<sufixo>_<pid>`) e o apaga ao sair.

    Só toca databases com o prefixo `lupa_teste_`; o banco de desenvolvimento fica intacto.
    Pula o teste se o PostgreSQL não estiver acessível.

    Args:
        sufixo: Distingue o database dos demais da mesma execução.

    Yields:
        Engine do database novo, sem migração.
    """
    url_principal = _url_banco_principal()
    if url_principal is None:
        pytest.skip("LUPA_DATABASE_URL não definida")
    nome_banco = f"lupa_teste_{sufixo}_{os.getpid()}"
    admin = create_engine(
        url_principal, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 2}
    )
    try:
        with admin.connect() as conexao:
            conexao.execute(text(f'DROP DATABASE IF EXISTS "{nome_banco}" WITH (FORCE)'))
            conexao.execute(text(f'CREATE DATABASE "{nome_banco}"'))
    except Exception:
        admin.dispose()
        pytest.skip("PostgreSQL inacessível neste ambiente")
    engine = create_engine(make_url(url_principal).set(database=nome_banco))
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.connect() as conexao:
            conexao.execute(text(f'DROP DATABASE IF EXISTS "{nome_banco}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture(scope="session")
def engine_teste() -> Iterator[Engine]:
    """Banco PostgreSQL efêmero (database próprio no serviço `db` do compose) já migrado."""
    with banco_vazio("sessao") as engine:
        migrar(engine, "head")
        yield engine


def migrar(engine: Engine, alvo: str, *, descer: bool = False) -> None:
    """Executa `alembic upgrade` ou `downgrade` no banco do engine.

    Args:
        engine: Engine do banco alvo.
        alvo: Revisão alvo (`head`, `base`...).
        descer: Se verdadeiro, faz downgrade.
    """
    config = Config(str(CAMINHO_ALEMBIC_INI))
    with engine.begin() as conexao:
        config.attributes["connection"] = conexao
        if descer:
            command.downgrade(config, alvo)
        else:
            command.upgrade(config, alvo)


@pytest.fixture
def sessao(engine_teste: Engine) -> Iterator[Session]:
    """Sessão dentro de transação desfeita ao final do teste."""
    with engine_teste.connect() as conexao:
        transacao = conexao.begin()
        with Session(bind=conexao, join_transaction_mode="create_savepoint") as session:
            yield session
        transacao.rollback()


@pytest.fixture
def fabrica_sessao(engine_teste: Engine) -> sessionmaker[Session]:
    """Fábrica de sessões (com commit real) no banco de teste."""
    return sessionmaker(engine_teste, expire_on_commit=False)


@dataclass(frozen=True)
class UsuarioTeste:
    """Usuário sintético semeado direto no banco.

    Attributes:
        hk: `hk_usuario`.
        id: Hex do `hk_usuario` (identificador público, D12).
        nome: Nome de usuário.
        papel: Papel.
        segredo: Segredo TOTP (None se MFA ainda não configurado).
    """

    hk: bytes
    id: str
    nome: str
    papel: PapelUsuario
    segredo: str | None


def semear_usuario(
    engine: Engine,
    papel: PapelUsuario,
    senha_hash: str,
    *,
    segredo: str | None = None,
    troca_senha: bool = False,
) -> UsuarioTeste:
    """Grava, com commit, hub, cadastro e credencial de um usuário sintético ativo.

    Args:
        engine: Engine do banco de teste.
        papel: Papel.
        senha_hash: Hash Argon2 da senha (quem chama escolhe a senha).
        segredo: Segredo TOTP já confirmado, ou None para MFA por configurar.
        troca_senha: Se a troca de senha é obrigatória.

    Returns:
        Dados do usuário criado.
    """
    nome = f"{papel.value[:4]}_{uuid4().hex[:10]}"
    credencial = {
        "senha_hash": senha_hash,
        "troca_senha_obrigatoria": troca_senha,
        "mfa_segredo": segredo,
        "mfa_confirmado": segredo is not None,
        "mfa_ultimo_passo": None,
    }
    with Session(engine) as session, session.begin():
        hk = gravar_hub(session, hub_usuario, {"nome_usuario": nome}, "teste")
        cadastro = {"papel": papel.value, "ativo": True}
        gravar_satelite(session, sat_usuario_cadastro, hk, cadastro, "teste")
        gravar_satelite(session, sat_usuario_credencial, hk, credencial, "teste")
    return UsuarioTeste(hk, hk.hex(), nome, papel, segredo)


def eventos_do_banco(engine: Engine, **filtros: Any) -> list[VisaoAuditoria]:
    """Lê eventos de auditoria direto do banco pela `v_auditoria`, filtrando por igualdade.

    Args:
        engine: Engine do banco de teste.
        **filtros: Coluna da view = valor (`usuario_id` é o hex do `hk_usuario`).

    Returns:
        Eventos em ordem de gravação na cadeia (`sequencia`).
    """
    with Session(engine) as session:
        consulta = select(VisaoAuditoria).filter_by(**filtros)
        return list(session.scalars(consulta.order_by(VisaoAuditoria.sequencia)))


VARIAVEIS_DE_AMBIENTE_ISOLADAS = ("LUPA_DB_USUARIO_APP", "LUPA_DB_SENHA_APP")


@pytest.fixture(autouse=True)
def _sem_usuario_de_conexao_do_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    """Os testes não herdam o usuário de conexão da API definido no `.env` do desenvolvedor.

    Com `LUPA_DB_USUARIO_APP` no ambiente, `Settings()` trocaria o usuário das URLs montadas nos
    testes; cada teste que precisa dele passa o valor explicitamente.
    """
    for variavel in VARIAVEIS_DE_AMBIENTE_ISOLADAS:
        monkeypatch.delenv(variavel, raising=False)
