"""Fixtures de acesso à aplicação real com serviços e dados sintéticos."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pyotp
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from apoio_comum import UsuarioTeste, semear_usuario
from lupa_intranet.acesso import senhas
from lupa_intranet.acesso.autorizacao import relogio
from lupa_intranet.api.app import create_app
from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.enums import PapelUsuario
from lupa_pipeline.dominio.visoes import VisaoUsuario
from lupa_pipeline.ingestao.storage import ArmazenamentoMemoria, StorageCifrado
from lupa_pipeline.seguranca.contexto import definir_cofre, obter_cofre

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
    fabrica_sessao: sessionmaker[Session],
    resolvedor_falso: ResolvedorFalso,
    settings_ficticias: Settings,
) -> FastAPI:
    """Sobe a fábrica pública e aponta suas dependências para o banco efêmero."""
    cofre = obter_cofre()
    app = create_app(settings_ficticias.model_copy(update={"cofre_backend": "memoria"}))
    definir_cofre(cofre)
    app.state.cofre = cofre
    app.state.fabrica_sessao = fabrica_sessao
    app.state.resolvedor = resolvedor_falso
    app.state.storage = StorageCifrado(ArmazenamentoMemoria())
    return app


@pytest.fixture
def cliente(app_teste: FastAPI) -> TestClient:
    """Cliente HTTPS (o cookie de sessão é `Secure`)."""
    return TestClient(app_teste, base_url="https://testserver")


def criar_usuario_teste(
    engine: Engine,
    papel: PapelUsuario,
    *,
    mfa: bool = True,
    troca_senha: bool = False,
) -> UsuarioTeste:
    """Cria usuário sintético com a senha `SENHA_TESTE` e, se pedido, MFA já confirmado.

    Args:
        engine: Engine do banco de teste.
        papel: Papel.
        mfa: Se o MFA já está confirmado.
        troca_senha: Se a troca de senha é obrigatória.

    Returns:
        Dados do usuário criado.
    """
    segredo = pyotp.random_base32() if mfa else None
    hash_senha = senhas.gerar_hash(SENHA_TESTE)
    return semear_usuario(engine, papel, hash_senha, segredo=segredo, troca_senha=troca_senha)


PERIODO_TOTP = 30


def codigo_totp_e_instante(engine: Engine, hk_usuario: bytes, segredo: str) -> tuple[str, datetime]:
    """Gera um código TOTP ainda não usado e o instante em que o servidor deve conferi-lo.

    Etapa 6.10: o relógio da requisição é injetado (`relogio`), então o passo não pode virar
    entre a geração e o uso. Se os passos da janela atual já foram gastos por logins anteriores
    do mesmo usuário, o instante avança para o próximo passo livre em vez de falhar.

    Args:
        engine: Engine do banco de teste.
        hk_usuario: Usuário.
        segredo: Segredo TOTP.

    Returns:
        Código de 6 dígitos e instante (UTC) a injetar na conferência.
    """
    with Session(engine) as session:
        consulta = select(VisaoUsuario.mfa_ultimo_passo).where(
            VisaoUsuario.hk_usuario == hk_usuario
        )
        ultimo = session.scalar(consulta)
    totp = pyotp.TOTP(segredo)
    agora = datetime.now(UTC)
    atual = totp.timecode(agora)
    passo = max(atual - 1, (ultimo or 0) + 1)
    instante = agora
    if passo > atual + 1:
        instante = datetime.fromtimestamp(passo * PERIODO_TOTP + 1, UTC)
    return totp.generate_otp(passo), instante


def codigo_totp(engine: Engine, hk_usuario: bytes, segredo: str) -> str:
    """Gera um código TOTP ainda não usado pelo usuário (use com `relogio_fixo`).

    Args:
        engine: Engine do banco de teste.
        hk_usuario: Usuário.
        segredo: Segredo TOTP.

    Returns:
        Código de 6 dígitos.
    """
    return codigo_totp_e_instante(engine, hk_usuario, segredo)[0]


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
    codigo, instante = codigo_totp_e_instante(engine, usuario.hk, usuario.segredo)
    with relogio_fixo(cliente.app, instante):
        resposta = cliente.post(
            "/auth/mfa", json={"desafio": resposta.json()["desafio"], "codigo": codigo}
        )
    assert resposta.status_code == 200, resposta.text
