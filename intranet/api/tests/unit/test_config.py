"""Testes da configuração na criação da aplicação."""

import pytest
from pydantic import ValidationError

from lupa_api.api.app import create_app
from lupa_pipeline.config import get_settings


def test_aplicacao_nao_inicia_sem_variavel_obrigatoria(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem LUPA_DATABASE_URL a criação da aplicação falha."""
    for chave in (
        "LUPA_DATABASE_URL",
        "LUPA_MINIO_ENDPOINT",
        "LUPA_MINIO_BUCKET",
        "LUPA_MINIO_ACCESS_KEY",
        "LUPA_MINIO_SECRET_KEY",
    ):
        monkeypatch.delenv(chave, raising=False)
    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="database_url"):
        create_app()
    get_settings.cache_clear()
