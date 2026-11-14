"""Testes da configuração."""

import pytest
from pydantic import ValidationError

from lupa_pipeline.config import get_settings


@pytest.mark.usefixtures("ambiente_ficticio")
def test_configuracao_le_variaveis_do_ambiente() -> None:
    """Variáveis com prefixo LUPA_ preenchem a configuração."""
    settings = get_settings()
    assert settings.minio_bucket == "lupa-autos"
    assert "segredo" not in repr(settings)


@pytest.mark.usefixtures("ambiente_ficticio")
def test_ambiente_invalido_e_rejeitado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valor fora da lista de ambientes falha na validação."""
    monkeypatch.setenv("LUPA_AMBIENTE", "qualquer")
    with pytest.raises(ValidationError):
        get_settings()
