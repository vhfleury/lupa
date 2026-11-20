"""Testes da rota de saúde e do middleware de request_id."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from apoio_comum import integracao_indisponivel
from lupa_api.api import saude
from lupa_api.api.app import create_app
from lupa_pipeline.config import Settings, get_settings
from lupa_pipeline.logging import get_logger

CREDENCIAL_FICTICIA = "valor-ficticio-de-metricas"


def _cliente(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


def test_saude_responde_ok_quando_dependencias_respondem(
    settings_ficticias: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Com banco e MinIO saudáveis, responde 200 e tudo ok."""
    monkeypatch.setattr(saude, "verificar_db", lambda _s: True)
    monkeypatch.setattr(saude, "verificar_minio", lambda _s: True)
    resposta = _cliente(settings_ficticias).get("/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"api": "ok", "db": "ok", "minio": "ok"}


def test_saude_responde_503_quando_banco_falha(
    settings_ficticias: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Com banco fora, responde 503 indicando a falha."""
    monkeypatch.setattr(saude, "verificar_db", lambda _s: False)
    monkeypatch.setattr(saude, "verificar_minio", lambda _s: True)
    resposta = _cliente(settings_ficticias).get("/saude")
    assert resposta.status_code == 503
    assert resposta.json()["db"] == "falha"


def test_saude_responde_503_quando_minio_falha(
    settings_ficticias: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RNF-06 (D4): com o MinIO fora, responde 503 indicando a falha."""
    monkeypatch.setattr(saude, "verificar_db", lambda _s: True)
    monkeypatch.setattr(saude, "verificar_minio", lambda _s: False)
    resposta = _cliente(settings_ficticias).get("/saude")
    assert resposta.status_code == 503
    assert resposta.json() == {"api": "ok", "db": "ok", "minio": "falha"}


def test_verificacoes_retornam_falso_sem_servicos(settings_ficticias: Settings) -> None:
    """Endereços inalcançáveis resultam em falha, sem exceção."""
    inalcancavel = settings_ficticias.model_copy(
        update={
            "minio_endpoint": "127.0.0.1:1",
            "timeout_saude_segundos": 0.2,
            "database_url": SecretStr("postgresql+psycopg://x:y@127.0.0.1:1/z"),
        }
    )
    assert saude.verificar_db(inalcancavel) is False
    assert saude.verificar_minio(inalcancavel) is False


@pytest.mark.integracao
@pytest.mark.parametrize("rota", ["/metricas/servico", "/metricas"])
def test_rotas_de_metricas_nao_existem(
    app_teste: FastAPI,
    settings_ficticias: Settings,
    monkeypatch: pytest.MonkeyPatch,
    rota: str,
) -> None:
    """D27 e decisão 16 da especificação: sem métricas Prometheus, mesmo com token configurado."""
    monkeypatch.setenv("LUPA_METRICAS_TOKEN", CREDENCIAL_FICTICIA)
    configurado = Settings(**settings_ficticias.model_dump(exclude={"metricas_token"}))
    app_teste.dependency_overrides[get_settings] = lambda: configurado
    cliente = TestClient(app_teste, base_url="https://testserver")
    resposta = cliente.get(rota, headers={"Authorization": f"Bearer {CREDENCIAL_FICTICIA}"})
    assert resposta.status_code == 404


def test_cada_requisicao_recebe_request_id_unico(
    settings_ficticias: Settings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """O middleware gera request_id distinto por requisição e o injeta no log."""
    monkeypatch.setattr(saude, "verificar_db", lambda _s: True)
    monkeypatch.setattr(saude, "verificar_minio", lambda _s: True)
    cliente = _cliente(settings_ficticias)
    primeiro = cliente.get("/saude").headers["X-Request-ID"]
    segundo = cliente.get("/saude").headers["X-Request-ID"]
    assert primeiro != segundo
    assert len(primeiro) == 32
    capsys.readouterr()


def test_log_dentro_da_requisicao_carrega_request_id(
    settings_ficticias: Settings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Eventos logados durante a requisição carregam o request_id do cabeçalho."""

    def _db(_s: Settings) -> bool:
        get_logger("teste").info("verificando_db")
        return True

    monkeypatch.setattr(saude, "verificar_db", _db)
    monkeypatch.setattr(saude, "verificar_minio", lambda _s: True)
    cliente = _cliente(settings_ficticias)
    capsys.readouterr()
    request_id = cliente.get("/saude").headers["X-Request-ID"]
    linhas = [json.loads(linha) for linha in capsys.readouterr().out.strip().splitlines()]
    assert any(linha.get("request_id") == request_id for linha in linhas)


@pytest.mark.integracao
@pytest.mark.usefixtures("ambiente_ficticio")
def test_saude_integracao_com_servicos_reais() -> None:
    """RNF-06. A rota verifica o PostgreSQL e o MinIO reais da implantação."""
    with TestClient(create_app(get_settings())) as cliente:
        resposta = cliente.get("/saude")
    if resposta.status_code == 503:
        falhas = [servico for servico, estado in resposta.json().items() if estado == "falha"]
        integracao_indisponivel("Serviços indisponíveis na rota /saude: " + ", ".join(falhas))
    assert resposta.status_code == 200
    assert resposta.json() == {"api": "ok", "db": "ok", "minio": "ok"}
