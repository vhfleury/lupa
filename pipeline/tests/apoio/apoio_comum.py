"""Fábricas e fixtures comuns aos testes da pipeline e da intranet (todas sintéticas)."""

import os
from collections.abc import Callable, Iterator
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
from lupa_pipeline.dominio.enums import Materia, PapelUsuario, StatusProcesso, TipoFato, TipoPagina
from lupa_pipeline.dominio.esquemas import Evidencia, Fato, calcular_hash
from lupa_pipeline.dominio.tabelas import (
    ArquivoTabela,
    EventoAuditoriaTabela,
    GabineteTabela,
    PaginaTabela,
    ProcessoTabela,
    UsuarioTabela,
)

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
FabricaProcesso = Callable[[UUID], UUID]


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


@pytest.fixture(scope="session")
def engine_teste() -> Iterator[Engine]:
    """Banco PostgreSQL efêmero (database próprio no serviço `db` do compose) já migrado.

    Pula o teste se o PostgreSQL não estiver acessível.
    """
    url_principal = _url_banco_principal()
    if url_principal is None:
        pytest.skip("LUPA_DATABASE_URL não definida")
    nome_banco = f"lupa_teste_{os.getpid()}"
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
    migrar(engine, "head")
    yield engine
    engine.dispose()
    with admin.connect() as conexao:
        conexao.execute(text(f'DROP DATABASE IF EXISTS "{nome_banco}" WITH (FORCE)'))
    admin.dispose()


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
def fabrica_processo(sessao: Session) -> FabricaProcesso:
    """Cria gabinete-usuário-processo sintéticos e devolve o id do processo.

    Returns:
        Função que recebe o id do gabinete e cria (se preciso) gabinete, usuário e processo.
    """
    contador = iter(range(1, 10_000))

    def _criar(gabinete_id: UUID) -> UUID:
        if sessao.get(GabineteTabela, gabinete_id) is None:
            sessao.add(GabineteTabela(id=gabinete_id, nome=f"Gabinete {gabinete_id.hex[:6]}"))
            sessao.flush()
        usuario_id, processo_id = uuid4(), uuid4()
        sessao.add(
            UsuarioTabela(
                id=usuario_id,
                gabinete_id=gabinete_id,
                nome_usuario=f"assessor_{usuario_id.hex[:8]}",
                papel=PapelUsuario.ASSESSOR.value,
                senha_hash="hash-ficticio",
            )
        )
        sessao.flush()
        sessao.add(
            ProcessoTabela(
                id=processo_id,
                gabinete_id=gabinete_id,
                numero_cnj=gerar_numero_cnj(next(contador)),
                classe="Apelação Criminal",
                materia=Materia.CRIMINAL.value,
                sigiloso=False,
                status=StatusProcesso.CRIADO.value,
                criado_por=usuario_id,
            )
        )
        sessao.flush()
        return processo_id

    return _criar


@pytest.fixture
def gabinete_id() -> UUID:
    """Id do gabinete sintético A."""
    return uuid4()


@pytest.fixture
def processo_id(fabrica_processo: FabricaProcesso, gabinete_id: UUID) -> UUID:
    """Processo sintético no gabinete A."""
    return fabrica_processo(gabinete_id)


def criar_pagina(sessao: Session, processo_id: UUID) -> UUID:
    """Cria arquivo e página sintéticos para o processo.

    Args:
        sessao: Sessão de teste.
        processo_id: Processo dono do arquivo.

    Returns:
        Id da página criada.
    """
    processo = sessao.get(ProcessoTabela, processo_id)
    assert processo is not None
    arquivo_id, pagina_id = uuid4(), uuid4()
    sessao.add(
        ArquivoTabela(
            id=arquivo_id,
            gabinete_id=processo.gabinete_id,
            processo_id=processo_id,
            sha256=calcular_hash(str(arquivo_id)),
            tamanho_bytes=1024,
            nome_original="autos-sinteticos.pdf",
            mime="application/pdf",
            chave_storage=f"sintetico/{arquivo_id}",
            enviado_por=processo.criado_por,
        )
    )
    sessao.flush()
    sessao.add(
        PaginaTabela(
            id=pagina_id,
            gabinete_id=processo.gabinete_id,
            arquivo_id=arquivo_id,
            numero=1,
            tipo=TipoPagina.NATIVA.value,
            texto=TEXTO_PAGINA,
            hash_texto=calcular_hash(TEXTO_PAGINA),
            flags={},
        )
    )
    sessao.flush()
    return pagina_id


@pytest.fixture
def pagina_id(sessao: Session, processo_id: UUID) -> UUID:
    """Página sintética do processo do gabinete A."""
    return criar_pagina(sessao, processo_id)


# --- Etapa 3: acesso e auditoria -------------------------------------------------------------


@dataclass(frozen=True)
class UsuarioTeste:
    """Usuário sintético semeado direto no banco.

    Attributes:
        id: Id.
        nome: Nome de usuário.
        gabinete_id: Gabinete (None para administrador).
        papel: Papel.
        segredo: Segredo TOTP (None se MFA ainda não configurado).
    """

    id: UUID
    nome: str
    gabinete_id: UUID | None
    papel: PapelUsuario
    segredo: str | None


@pytest.fixture
def fabrica_sessao(engine_teste: Engine) -> sessionmaker[Session]:
    """Fábrica de sessões (com commit real) no banco de teste."""
    return sessionmaker(engine_teste, expire_on_commit=False)


def criar_gabinete_teste(engine: Engine) -> UUID:
    """Cria um gabinete sintético com commit.

    Args:
        engine: Engine do banco de teste (superusuário, sem RLS).

    Returns:
        Id do gabinete.
    """
    gabinete_id = uuid4()
    with Session(engine) as session, session.begin():
        session.add(GabineteTabela(id=gabinete_id, nome=f"Gabinete {gabinete_id.hex[:6]}"))
    return gabinete_id


def criar_processo_teste(engine: Engine, autor: UsuarioTeste) -> UUID:
    """Cria um processo sintético no gabinete do autor, com commit.

    Args:
        engine: Engine do banco de teste.
        autor: Usuário criador do processo.

    Returns:
        Id do processo.
    """
    processo_id = uuid4()
    with Session(engine) as session, session.begin():
        session.add(
            ProcessoTabela(
                id=processo_id,
                gabinete_id=autor.gabinete_id,
                numero_cnj=gerar_numero_cnj(int(processo_id.int % 9_000_000) + 1),
                classe="Apelação Criminal",
                materia=Materia.CRIMINAL.value,
                sigiloso=False,
                status=StatusProcesso.CRIADO.value,
                criado_por=autor.id,
            )
        )
    return processo_id


def eventos_do_banco(engine: Engine, **filtros: Any) -> list[EventoAuditoriaTabela]:
    """Lê eventos de auditoria direto do banco (superusuário), filtrando por igualdade.

    Args:
        engine: Engine do banco de teste.
        **filtros: Coluna = valor.

    Returns:
        Eventos em ordem de gravação na cadeia (`sequencia`).
    """
    with Session(engine) as session:
        consulta = select(EventoAuditoriaTabela).filter_by(**filtros)
        return list(session.scalars(consulta.order_by(EventoAuditoriaTabela.sequencia)))


# --- Etapa 4A: ingestão --------------------------------------------------------------------

VARIAVEIS_DE_AMBIENTE_ISOLADAS = ("LUPA_DB_USUARIO_APP", "LUPA_DB_SENHA_APP")


@pytest.fixture(autouse=True)
def _sem_usuario_de_conexao_do_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    """Os testes não herdam o usuário de conexão da API definido no `.env` do desenvolvedor.

    Com `LUPA_DB_USUARIO_APP` no ambiente, `Settings()` trocaria o usuário das URLs montadas nos
    testes; cada teste que precisa dele passa o valor explicitamente.
    """
    for variavel in VARIAVEIS_DE_AMBIENTE_ISOLADAS:
        monkeypatch.delenv(variavel, raising=False)
