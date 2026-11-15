"""Limpeza dos processos semeados pelos scripts, preservando o restante e a auditoria."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from apoio_comum import criar_processo
from lupa_intranet.auditoria.eventos import AcaoAuditoria, NovoEvento
from lupa_intranet.auditoria.registrador import registrar, verificar_cadeia
from lupa_pipeline.dominio.enums import ClasseProcessual
from lupa_pipeline.dominio.visoes import VisaoProcesso
from lupa_pipeline.ingestao.storage import ArmazenamentoMemoria

pytestmark = pytest.mark.integracao
CAMINHO = Path(__file__).resolve().parents[4] / "pipeline" / "scripts" / "limpar_dev.py"


def _modulo() -> ModuleType:
    spec = importlib.util.spec_from_file_location("limpar_dev", CAMINHO)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_recusa_fora_de_desenvolvimento(engine_teste: Engine) -> None:
    """A operação não aceita o banco de produção."""
    script = _modulo()
    with pytest.raises(script.RecusaError, match="desenvolvimento"):
        script.limpar(
            engine_teste, ambiente="producao", executar=True, storage=ArmazenamentoMemoria()
        )


def test_so_descarta_conteudo_criado_por_scripts_e_preserva_a_cadeia(engine_teste: Engine) -> None:
    """O dry run deixa as chaves intactas e o descarte mantém o rastro e o processo vizinho."""
    from lupa_pipeline.ingestao.calibracao import novo_processo, semear_assessor

    script = _modulo()
    storage = ArmazenamentoMemoria()
    with Session(engine_teste) as sessao, sessao.begin():
        assessor = semear_assessor(sessao, "scripts.calibrar")
        hk = novo_processo(sessao, assessor, ClasseProcessual.APELACAO_CIVEL, "scripts.calibrar")
        vizinho = criar_processo(sessao)
        registrar(sessao, NovoEvento(acao=AcaoAuditoria.PROCESSO_ABERTO, hk_processo=hk))
    assert (
        script.limpar(engine_teste, executar=False, ambiente="teste", storage=storage).processos
        == 1
    )
    with Session(engine_teste) as sessao:
        assert sessao.get_one(VisaoProcesso, hk).status != "descartado"
    feito = script.limpar(engine_teste, executar=True, ambiente="teste", storage=storage)
    assert feito.processos == 1
    with Session(engine_teste) as sessao:
        assert sessao.get_one(VisaoProcesso, vizinho).status != "descartado"
        assert verificar_cadeia(sessao).integra
        assert (
            sessao.scalar(select(VisaoProcesso.status).where(VisaoProcesso.hk_processo == hk))
            == "descartado"
        )
    assert (
        script.limpar(engine_teste, executar=True, ambiente="teste", storage=storage).processos == 0
    )
