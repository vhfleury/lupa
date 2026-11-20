"""Rota de saúde da API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from lupa_api.api import saude
from lupa_pipeline.config import Settings, get_settings

router = APIRouter()


@router.get("/saude")
def obter_saude(
    response: Response, settings: Annotated[Settings, Depends(get_settings)]
) -> dict[str, str]:
    """Informa o estado da API, do banco e do MinIO (RF-SEG-02 removido).

    Args:
        response: Resposta HTTP, para ajustar o status.
        settings: Configuração da aplicação.

    Returns:
        Estado de cada componente (`ok` ou `falha`); 503 se algum falhar.
    """
    corpo = {
        "api": "ok",
        "db": "ok" if saude.verificar_db(settings) else "falha",
        "minio": "ok" if saude.verificar_minio(settings) else "falha",
    }
    if "falha" in corpo.values():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return corpo
