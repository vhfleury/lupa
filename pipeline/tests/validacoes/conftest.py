"""Fatos e evidências determinísticos para as regras cíveis."""

from collections.abc import Callable
from hashlib import sha256
from typing import Any

import pytest

from lupa_pipeline.dominio.esquemas import Evidencia, Fato
from lupa_pipeline.validacoes.modelo import ModeloProcesso


def id_sintetico(nome: str) -> str:
    """Calcula o identificador público de um objeto sintético."""
    return sha256(nome.encode()).hexdigest()


PROCESSO_SINTETICO = id_sintetico("processo")
PAGINA_SINTETICA = id_sintetico("pagina")
SUJEITO = id_sintetico("recorrente")


def criar_fato(
    tipo: str, valor: Any, *, sujeito: str = SUJEITO, fato_id: str | None = None
) -> Fato:
    """Monta um fato com referência reprodutível a um trecho de página."""
    nome = fato_id or f"{tipo}-{valor}-{sujeito}"
    trecho = f"{tipo} em autos sintéticos"
    evidencia = Evidencia(
        id=id_sintetico(f"ev-{nome}"),
        pagina_id=PAGINA_SINTETICA,
        trecho=trecho,
        inicio=0,
        fim=len(trecho),
    )
    return Fato(
        id=id_sintetico(nome),
        processo_id=PROCESSO_SINTETICO,
        tipo=tipo,
        valor=valor,
        sujeito=sujeito,
        evidencias=(evidencia,),
        extraido_por="teste",
        versao_extrator="0.2",
        confianca=1.0,
        status="confirmado",
    )


def modelo_de(*fatos: Fato) -> ModeloProcesso:
    """Indexa fatos sintéticos."""
    return ModeloProcesso(fatos)


@pytest.fixture
def fato() -> Callable[..., Fato]:
    """Fábrica de fatos sintéticos."""
    return criar_fato
