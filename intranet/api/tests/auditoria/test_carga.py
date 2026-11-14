"""Consulta filtrada no conjunto sintético de um milhão de eventos."""

import statistics
import time
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from lupa_intranet.auditoria import consulta
from lupa_pipeline.dominio.chaves import chave_hash
from lupa_pipeline.dominio.sessao import assumir_papel_aplicacao
from lupa_pipeline.dominio.visoes import VisaoAuditoria

pytestmark = [pytest.mark.integracao, pytest.mark.carga]

TOTAL_EVENTOS = 1_000_000
TOTAL_USUARIOS = 1000
LIMITE_MS = 200
INICIO = datetime(2025, 1, 1, tzinfo=UTC)


def test_um_milhao_de_eventos_consulta_por_usuario_e_intervalo_abaixo_de_200ms(
    engine_teste: Engine,
) -> None:
    """RF-AUD-04: mediana inferior a 200 ms para filtrar por usuário e intervalo."""
    with Session(engine_teste) as sessao, sessao.begin():
        sessao.execute(
            text("""
            INSERT INTO hub_usuario(hk_usuario, nome_usuario, record_source)
            SELECT sha256(convert_to('CARGA' || i, 'UTF8')), 'carga' || i, 'teste.carga'
            FROM generate_series(0, :usuarios - 1) AS i
        """),
            {"usuarios": TOTAL_USUARIOS},
        )
        sequencia = sessao.scalar(select(func.max(VisaoAuditoria.sequencia))) or 0
        sessao.execute(
            text("""
            INSERT INTO link_evento_auditoria(hk_evento, sequencia, ocorrido_em, hk_usuario,
                                                record_source, acao, resultado, hash_evento)
            SELECT sha256(convert_to((:anterior + i)::text, 'UTF8')), :anterior + i,
                   CAST(:inicio AS timestamptz) + i * interval '31.5 seconds',
                   sha256(convert_to('CARGA' || (i % :usuarios), 'UTF8')),
                   'teste.carga', 'busca', 'ok', repeat('0', 64)
            FROM generate_series(1, :total) AS i
        """),
            {
                "total": TOTAL_EVENTOS,
                "usuarios": TOTAL_USUARIOS,
                "inicio": INICIO,
                "anterior": sequencia,
            },
        )
        sessao.execute(text("ANALYZE link_evento_auditoria"))
        assert (
            sessao.scalar(select(func.count()).select_from(VisaoAuditoria))
            == sequencia + TOTAL_EVENTOS
        )
        assumir_papel_aplicacao(sessao)
        usuario = chave_hash(["CARGA7"]).hex()
        filtro = consulta.FiltroAuditoria(
            usuario_id=usuario, inicio=INICIO + timedelta(days=90), fim=INICIO + timedelta(days=180)
        )
        tempos = []
        for _ in range(10):
            inicio = time.perf_counter()
            pagina = consulta.consultar(sessao, filtro, limite=50)
            tempos.append((time.perf_counter() - inicio) * 1000)
        assert pagina.eventos and all(e.usuario_id == usuario for e in pagina.eventos)
        assert statistics.median(tempos) < LIMITE_MS
        sessao.rollback()
