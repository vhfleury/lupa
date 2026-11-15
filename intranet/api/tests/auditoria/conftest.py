"""Fábrica de chamadas ao modelo sintéticas com o evento da mesma transação."""

from collections.abc import Callable
from uuid import uuid4

import pytest
from sqlalchemy import insert
from sqlalchemy.orm import Session

from lupa_intranet.auditoria.eventos import AcaoAuditoria, NovoEvento
from lupa_intranet.auditoria.registrador import registrar
from lupa_pipeline.dominio.chaves import chave_hash
from lupa_pipeline.dominio.tabelas import link_chamada_modelo

ChamadaTeste = Callable[[Session, bytes, bytes, str, bytes | None], None]


@pytest.fixture
def chamada_teste() -> ChamadaTeste:
    """RF-AUD-05: registra os tokens, o modelo e o responsável pela chamada."""

    def gravar(
        sessao: Session, processo: bytes, usuario: bytes, modelo: str, conversa: bytes | None
    ) -> None:
        hk = chave_hash([uuid4()])
        sessao.execute(
            insert(link_chamada_modelo).values(
                hk_chamada=hk,
                hk_processo=processo,
                hk_conversa=conversa,
                record_source="teste",
                modelo=modelo,
                versao_prompt="p1",
                hash_prompt_sistema="s",
                hash_entrada="e",
                hash_saida="r",
                tokens_entrada=250_000,
                tokens_saida=50_000,
                latencia_ms=1,
                ferramentas=[],
                resultado="ok",
            )
        )
        registrar(
            sessao,
            NovoEvento(
                acao=AcaoAuditoria.CHAMADA_MODELO,
                hk_processo=processo,
                hk_usuario=usuario,
                objeto_tipo="chamada_modelo",
                objeto_id=hk.hex(),
                versao_modelo=modelo,
                versao_prompt="p1",
            ),
        )

    return gravar
