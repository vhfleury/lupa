"""Conferência humana do valor e das evidências de um fato (A11)."""

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from lupa_pipeline.dominio.enums import StatusFato
from lupa_pipeline.dominio.esquemas import Evidencia, Fato
from lupa_pipeline.dominio.repositorios import (
    evidencia_da_pagina,
    gravar_valor,
    listar_fatos_por_processo,
    processo_para_gravar,
    vincular_evidencia,
)


class CorrecaoInvalidaError(ValueError):
    """Valor, evidência ou estado incompatível com a correção."""


def _tipo_json(valor: Any) -> str:
    if isinstance(valor, bool):
        return "booleano"
    if isinstance(valor, int | float):
        return "numero"
    if isinstance(valor, str):
        try:
            date.fromisoformat(valor)
        except ValueError:
            return "texto"
        return "data"
    return type(valor).__name__


def valor_corrigido(original: Any, novo: Any) -> Any:
    """Exige um novo valor do mesmo tipo do anterior."""
    if _tipo_json(original) != _tipo_json(novo):
        raise CorrecaoInvalidaError(
            f"valor deve ser do mesmo tipo do original ({_tipo_json(original)})"
        )
    if original == novo:
        raise CorrecaoInvalidaError("valor igual ao original: use confirmar")
    return novo


def obter_fato(session: Session, processo_id: bytes, fato_id: str) -> Fato | None:
    """Retorna o fato com as evidências vigentes, se pertencer ao processo."""
    return next(
        (f for f in listar_fatos_por_processo(session, processo_id) if f.id == fato_id), None
    )


def corrigir_fato(
    session: Session,
    original: Fato,
    status: StatusFato,
    autor: bytes,
    valor: Any = None,
    evidencia: Evidencia | None = None,
) -> Fato:
    """Aplica a decisão humana sob a trava do processo, preservando a chave de origem."""
    processo_id = bytes.fromhex(original.processo_id)
    processo_para_gravar(session, processo_id)
    corrente = obter_fato(session, processo_id, original.id)
    if corrente is None:
        raise CorrecaoInvalidaError("fato indisponível")
    hk = bytes.fromhex(corrente.id)
    if status == StatusFato.CORRIGIDO and evidencia is not None:
        valor = valor_corrigido(corrente.valor, valor)
        nova = evidencia_da_pagina(session, processo_id, evidencia)
        for anterior in corrente.evidencias:
            if anterior.id != nova.hex():
                vincular_evidencia(session, hk, bytes.fromhex(anterior.id), False)
        vincular_evidencia(session, hk, nova, True)
    elif status == StatusFato.CONFIRMADO and valor is None and evidencia is None:
        valor = corrente.valor
    else:
        raise CorrecaoInvalidaError("correção exige valor e evidência; confirmação mantém ambos")
    novo = corrente.model_copy(
        update={
            "status": status,
            "valor": valor,
            "extraido_por": "revisao_humana",
            "versao_extrator": "manual",
            "confianca": 1.0,
        }
    )
    gravar_valor(session, hk, novo, autor)
    salvo = obter_fato(session, processo_id, original.id)
    if salvo is None:
        raise CorrecaoInvalidaError("fato indisponível após a correção")
    return salvo
