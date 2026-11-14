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
@pytest.mark.parametrize(
    ("variavel", "campo"),
    [
        ("LUPA_METRICAS_TOKEN", "metricas_token"),
        ("LUPA_BACKUP_DIR", "backup_dir"),
        ("LUPA_BACKUP_CHAVES_DIR", "backup_chaves_dir"),
        ("LUPA_BACKUP_RETENCAO_DIAS", "backup_retencao_dias"),
    ],
)
def test_configuracao_ignora_chaves_de_metricas_e_backup(
    monkeypatch: pytest.MonkeyPatch, variavel: str, campo: str
) -> None:
    """RES-11 e decisão 16 da especificação: métricas e backup não têm mais configuração."""
    monkeypatch.setenv(variavel, "valor-ficticio")
    settings = get_settings()
    assert campo not in type(settings).model_fields
    assert not hasattr(settings, campo)


@pytest.mark.usefixtures("ambiente_ficticio")
def test_worker_consulta_banco_no_intervalo_configurado(monkeypatch: pytest.MonkeyPatch) -> None:
    """RES-07: a fila usa intervalo positivo, de dois segundos quando omitido."""
    monkeypatch.delenv("LUPA_FILA_INTERVALO_S", raising=False)
    assert get_settings().model_dump().get("fila_intervalo_s") == 2
    monkeypatch.setenv("LUPA_FILA_INTERVALO_S", "0.25")
    get_settings.cache_clear()
    assert get_settings().model_dump()["fila_intervalo_s"] == 0.25
    monkeypatch.setenv("LUPA_FILA_INTERVALO_S", "0")
    get_settings.cache_clear()
    with pytest.raises(ValidationError):
        get_settings()


@pytest.mark.usefixtures("ambiente_ficticio")
@pytest.mark.parametrize("campo", ["redis_url", "fila_ingestao", "lease_segundos"])
def test_fila_dispensa_as_chaves_de_redis_e_lease(
    monkeypatch: pytest.MonkeyPatch, campo: str
) -> None:
    """RES-07: o ambiente legado não reativa a fila externa nem o lease."""
    monkeypatch.setenv(f"LUPA_{campo.upper()}", "13")
    assert campo not in get_settings().model_dump()


@pytest.mark.usefixtures("ambiente_ficticio")
def test_ambiente_invalido_e_rejeitado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valor fora da lista de ambientes falha na validação."""
    monkeypatch.setenv("LUPA_AMBIENTE", "qualquer")
    with pytest.raises(ValidationError):
        get_settings()
