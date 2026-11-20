"""Registro na cadeia única de auditoria e verificação dela (A15; RF-AUD-03)."""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from lupa_api.auditoria.eventos import AcaoAuditoria, NovoEvento
from lupa_api.auditoria.registrador import registrar, verificar_cadeia
from lupa_pipeline.dominio.chaves import chave_hash
from lupa_pipeline.dominio.sessao import assumir_papel_aplicacao

pytestmark = pytest.mark.integracao


def _registrar_tres(sessao: Session) -> list[int]:
    acoes = (AcaoAuditoria.LOGIN_OK, AcaoAuditoria.MFA_OK, AcaoAuditoria.LOGOUT)
    return [
        registrar(sessao, NovoEvento(acao=acao, ip="203.0.113.9"))["sequencia"] for acao in acoes
    ]


def test_eventos_encadeiam_em_sequencia_unica(sessao: Session) -> None:
    """RF-AUD-03: cada evento aponta o hash do anterior, com `hk_evento` da `sequencia`."""
    inicio = verificar_cadeia(sessao).total
    assumir_papel_aplicacao(sessao)
    primeiro = registrar(sessao, NovoEvento(acao=AcaoAuditoria.LOGIN_OK))
    segundo = registrar(sessao, NovoEvento(acao=AcaoAuditoria.LOGOUT))
    assert (primeiro["sequencia"], segundo["sequencia"]) == (inicio + 1, inicio + 2)
    assert segundo["hash_anterior"] == primeiro["hash_evento"]
    assert segundo["hk_evento"] == chave_hash([inicio + 2])
    assert verificar_cadeia(sessao).integra


def test_alteracao_direta_no_banco_e_apontada(sessao: Session) -> None:
    """RF-AUD-03: evento alterado por fora da aplicação quebra a cadeia nele."""
    sequencias = _registrar_tres(sessao)
    sessao.execute(text("ALTER TABLE link_evento_auditoria DISABLE TRIGGER USER"))
    sessao.execute(
        text("UPDATE link_evento_auditoria SET ip = '198.51.100.1' WHERE sequencia = :s"),
        {"s": sequencias[1]},
    )
    resultado = verificar_cadeia(sessao)
    assert (resultado.integra, resultado.primeira_sequencia_quebrada, resultado.motivo) == (
        False,
        sequencias[1],
        "hash",
    )


def test_evento_novo_grava_record_source_api(sessao: Session) -> None:
    """RES-12 (D9): a linha nova de auditoria grava `record_source` `api.auditoria`."""
    assumir_papel_aplicacao(sessao)
    evento = registrar(sessao, NovoEvento(acao=AcaoAuditoria.LOGIN_OK))
    origem = sessao.execute(
        text("SELECT record_source FROM link_evento_auditoria WHERE sequencia = :s"),
        {"s": evento["sequencia"]},
    ).scalar_one()
    assert origem == "api.auditoria"
