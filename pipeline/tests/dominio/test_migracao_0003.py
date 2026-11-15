"""Revisão que remove o cofre de chaves do banco (RF-SEG-01)."""

import hashlib

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Session

from apoio_comum import banco_vazio, gerar_numero_cnj, migrar

pytestmark = pytest.mark.integracao
COLUNA_REMOVIDA = "chave_dados_cifrada"


def _colunas_v_processo(engine: Engine) -> list[str]:
    return [c["name"] for c in inspect(engine).get_columns("v_processo")]


def _retorno_descarte(engine: Engine) -> str:
    consulta = text(
        "SELECT t.typname FROM pg_proc p JOIN pg_type t ON t.oid = p.prorettype "
        "WHERE p.proname = 'lupa_descartar_processo'"
    )
    with engine.connect() as conexao:
        return str(conexao.execute(consulta).scalar_one())


def _gravar_processo_em_revisao(session: Session) -> bytes:
    hk = hashlib.sha256(b"processo-sintetico-0003").digest()
    session.execute(
        text(
            "INSERT INTO hub_processo (hk_processo, numero_cnj, load_dts, record_source) "
            "VALUES (:hk, :numero, now(), 'teste')"
        ),
        {"hk": hk, "numero": gerar_numero_cnj(3)},
    )
    session.execute(
        text(
            "INSERT INTO sat_processo_revisao (hk_processo, load_dts, hash_diff, record_source, "
            "situacao, motivo, status_anterior) "
            "VALUES (:hk, now(), :diff, 'teste', 'aberta', 'motivo sintético', 'criado')"
        ),
        {"hk": hk, "diff": hashlib.sha256(b"revisao").digest()},
    )
    return hk


def test_subir_remove_o_cofre_e_descer_o_restaura() -> None:
    """RF-SEG-01: a 0003 remove sat_processo_chave e a coluna cifrada; o downgrade restaura."""
    with banco_vazio("sem_cofre") as engine:
        migrar(engine, "0002")
        colunas_0002 = _colunas_v_processo(engine)
        assert COLUNA_REMOVIDA in colunas_0002

        migrar(engine, "0003")
        assert not inspect(engine).has_table("sat_processo_chave")
        assert _colunas_v_processo(engine) == [c for c in colunas_0002 if c != COLUNA_REMOVIDA]
        assert _retorno_descarte(engine) == "void"
        with Session(engine) as session, session.begin():
            assert session.scalar(
                text("SELECT has_table_privilege('lupa_app', 'v_processo', 'SELECT')")
            )
            hk = _gravar_processo_em_revisao(session)
            session.execute(text("SELECT lupa_descartar_processo(:hk)"), {"hk": hk})
            restantes = session.scalar(
                text("SELECT count(*) FROM sat_processo_revisao WHERE hk_processo = :hk"),
                {"hk": hk},
            )
            assert restantes == 0

        migrar(engine, "0002", descer=True)
        assert inspect(engine).has_table("sat_processo_chave")
        with engine.connect() as conexao:
            assert conexao.scalar(text("SELECT count(*) FROM sat_processo_chave")) == 0
        assert _colunas_v_processo(engine) == colunas_0002
        assert _retorno_descarte(engine) == "text"
