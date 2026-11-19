"""Verificações de saúde das dependências externas."""

import urllib.request

from sqlalchemy import create_engine, text

from lupa_pipeline.config import Settings


def verificar_db(settings: Settings) -> bool:
    """Verifica se o banco responde a uma consulta trivial.

    Args:
        settings: Configuração da aplicação.

    Returns:
        Verdadeiro se o banco respondeu.
    """
    engine = create_engine(
        settings.database_url.get_secret_value(),
        connect_args={"connect_timeout": max(1, int(settings.timeout_saude_segundos))},
    )
    try:
        with engine.connect() as conexao:
            conexao.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        engine.dispose()


def verificar_minio(settings: Settings) -> bool:
    """Verifica se o MinIO está vivo pelo endpoint de saúde.

    Args:
        settings: Configuração da aplicação.

    Returns:
        Verdadeiro se o MinIO respondeu 200.
    """
    esquema = "https" if settings.minio_secure else "http"
    url = f"{esquema}://{settings.minio_endpoint}/minio/health/live"
    try:
        with urllib.request.urlopen(url, timeout=settings.timeout_saude_segundos) as resposta:  # noqa: S310
            return bool(resposta.status == 200)
    except Exception:
        return False
