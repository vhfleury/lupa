"""Fixtures da intranet (aplicação, login e MFA); as comuns vêm de `pipeline/tests/apoio/`."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pyotp
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from apoio_comum import UsuarioTeste, criar_gabinete_teste
from apoio_ingestao import CriarAssessor
from lupa_intranet.acesso import senhas
from lupa_intranet.acesso.autorizacao import relogio
from lupa_intranet.api.app import create_app
from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.enums import PapelUsuario
from lupa_pipeline.dominio.tabelas import UsuarioTabela

pytest_plugins = ["apoio_comum", "apoio_ingestao"]

SENHA_TESTE = "cavalo-bateria-grampo-correto"  # noqa: S105


class ResolvedorFalso:
    """Resolvedor de localização para testes: devolve texto fixo e conta as chamadas."""

    def __init__(self) -> None:
        """Cria o resolvedor com contador zerado."""
        self.chamadas = 0

    def resolver(self, ip: str | None) -> str:
        """Devolve localização fictícia.

        Args:
            ip: IP (ignorado).

        Returns:
            Texto fixo.
        """
        self.chamadas += 1
        return "Cidade Fictícia, Estado Fictício, País Fictício"


@pytest.fixture
def resolvedor_falso() -> ResolvedorFalso:
    """Resolvedor de localização falso."""
    return ResolvedorFalso()


@pytest.fixture
def app_teste(
    settings_ficticias: Settings,
    fabrica_sessao: sessionmaker[Session],
    resolvedor_falso: ResolvedorFalso,
) -> FastAPI:
    """Aplicação ligada ao banco de teste e ao resolvedor falso."""
    app = create_app(settings_ficticias)
    app.state.fabrica_sessao = fabrica_sessao
    app.state.resolvedor = resolvedor_falso
    return app


@pytest.fixture
def cliente(app_teste: FastAPI) -> TestClient:
    """Cliente HTTPS (o cookie de sessão é `Secure`)."""
    return TestClient(app_teste, base_url="https://testserver")


def criar_usuario_teste(
    engine: Engine,
    papel: PapelUsuario,
    gabinete_id: UUID | None,
    *,
    mfa: bool = True,
    troca_senha: bool = False,
) -> UsuarioTeste:
    """Cria usuário sintético com a senha `SENHA_TESTE` e, se pedido, MFA já confirmado.

    Args:
        engine: Engine do banco de teste.
        papel: Papel.
        gabinete_id: Gabinete (None para administrador).
        mfa: Se o MFA já está confirmado.
        troca_senha: Se a troca de senha é obrigatória.

    Returns:
        Dados do usuário criado.
    """
    usuario_id = uuid4()
    segredo = pyotp.random_base32() if mfa else None
    nome = f"{papel.value[:4]}_{usuario_id.hex[:10]}"
    with Session(engine) as session, session.begin():
        session.add(
            UsuarioTabela(
                id=usuario_id,
                gabinete_id=gabinete_id,
                nome_usuario=nome,
                papel=papel.value,
                senha_hash=senhas.gerar_hash(SENHA_TESTE),
                mfa_segredo=segredo,
                mfa_confirmado=mfa,
                ativo=True,
                troca_senha_obrigatoria=troca_senha,
            )
        )
    return UsuarioTeste(usuario_id, nome, gabinete_id, papel, segredo)


def _assessor_com_login(engine: Engine) -> UsuarioTeste:
    return criar_usuario_teste(engine, PapelUsuario.ASSESSOR, criar_gabinete_teste(engine))


@pytest.fixture(scope="session")
def criar_assessor() -> CriarAssessor:
    """Assessor da extração da sessão com senha e MFA, para os testes que fazem login."""
    return _assessor_com_login


PERIODO_TOTP = 30


def codigo_totp_e_instante(engine: Engine, usuario_id: UUID, segredo: str) -> tuple[str, datetime]:
    """Gera um código TOTP ainda não usado e o instante em que o servidor deve conferi-lo.

    Etapa 6.10: o relógio da requisição é injetado (`relogio`), então o passo não pode virar
    entre a geração e o uso. Se os passos da janela atual já foram gastos por logins anteriores
    do mesmo usuário, o instante avança para o próximo passo livre em vez de falhar.

    Args:
        engine: Engine do banco de teste.
        usuario_id: Usuário.
        segredo: Segredo TOTP.

    Returns:
        Código de 6 dígitos e instante (UTC) a injetar na conferência.
    """
    with Session(engine) as session:
        usuario = session.get(UsuarioTabela, usuario_id)
        assert usuario is not None
        ultimo = usuario.mfa_ultimo_passo
    totp = pyotp.TOTP(segredo)
    agora = datetime.now(UTC)
    atual = totp.timecode(agora)
    passo = max(atual - 1, (ultimo or 0) + 1)
    instante = agora
    if passo > atual + 1:
        instante = datetime.fromtimestamp(passo * PERIODO_TOTP + 1, UTC)
    return totp.generate_otp(passo), instante


def codigo_totp(engine: Engine, usuario_id: UUID, segredo: str) -> str:
    """Gera um código TOTP ainda não usado pelo usuário (use com `relogio_fixo`).

    Args:
        engine: Engine do banco de teste.
        usuario_id: Usuário.
        segredo: Segredo TOTP.

    Returns:
        Código de 6 dígitos.
    """
    return codigo_totp_e_instante(engine, usuario_id, segredo)[0]


@contextmanager
def relogio_fixo(app: Any, instante: datetime | None = None) -> Iterator[datetime]:
    """Congela o relógio das requisições no instante dado (ou agora) e restaura ao sair.

    Args:
        app: Aplicação FastAPI.
        instante: Instante a injetar; agora se None.

    Yields:
        O instante injetado.
    """
    fixo = instante or datetime.now(UTC)
    anterior = app.dependency_overrides.get(relogio)
    app.dependency_overrides[relogio] = lambda: fixo
    try:
        yield fixo
    finally:
        if anterior is None:
            app.dependency_overrides.pop(relogio, None)
        else:
            app.dependency_overrides[relogio] = anterior


def logar(cliente: TestClient, engine: Engine, usuario: UsuarioTeste) -> None:
    """Faz o login completo (senha + TOTP) e deixa o cookie no cliente.

    O código é conferido com o relógio injetado no instante em que foi gerado (6.10), para o
    passo TOTP não virar entre a geração e o uso.

    Args:
        cliente: Cliente HTTP.
        engine: Engine do banco de teste.
        usuario: Usuário com MFA confirmado.
    """
    assert usuario.segredo is not None
    resposta = cliente.post(
        "/auth/login", json={"nome_usuario": usuario.nome, "senha": SENHA_TESTE}
    )
    assert resposta.status_code == 200, resposta.text
    codigo, instante = codigo_totp_e_instante(engine, usuario.id, usuario.segredo)
    with relogio_fixo(cliente.app, instante):
        resposta = cliente.post(
            "/auth/mfa", json={"desafio": resposta.json()["desafio"], "codigo": codigo}
        )
    assert resposta.status_code == 200, resposta.text
