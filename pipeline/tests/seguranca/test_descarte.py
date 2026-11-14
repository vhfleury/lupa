"""Proteção concorrente do conteúdo durante o descarte do processo (A13)."""

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from apoio_comum import criar_processo_teste
from lupa_pipeline.dominio import gravacao

pytestmark = pytest.mark.integracao


def test_trava_por_processo_serializa_escritores_e_libera_no_commit(engine_teste: Engine) -> None:
    """RF-PRO-05: a trava retida até o commit protege só o processo em descarte."""
    hk = criar_processo_teste(engine_teste)
    outro = criar_processo_teste(engine_teste)
    with Session(engine_teste) as primeira, Session(engine_teste) as segunda:
        processo = gravacao.travar_processo(primeira, hk)
        assert processo is not None and processo.hk_processo == hk
        assert gravacao.travar_processo(segunda, outro) is not None
        segunda.execute(select(func.set_config("lock_timeout", "200ms", True)))
        with pytest.raises(OperationalError, match="lock timeout"):
            gravacao.travar_processo(segunda, hk)
        segunda.rollback()
        primeira.commit()
        assert gravacao.travar_processo(segunda, hk) is not None
        assert gravacao.travar_processo(segunda, bytes(32)) is None
