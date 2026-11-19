"""Custo das chamadas a partir da tabela versionada (RF-AUD-05)."""

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from apoio_comum import criar_processo_teste
from lupa_api.agente.precos import CAMINHO_PRECOS, Preco, custo, ler_tabela, tabela_padrao
from lupa_api.auditoria.consulta import FiltroAuditoria, custo_estimado
from lupa_pipeline.dominio.enums import PapelUsuario
from lupa_pipeline.dominio.gravacao import gravar_hub
from lupa_pipeline.dominio.tabelas import hub_conversa
from tests.auditoria.conftest import ChamadaTeste
from tests.conftest import criar_usuario_teste


def test_tabela_versionada_tem_fonte_e_modelo_configurado() -> None:
    """A tabela tem versão, fonte, ressalva e o preço do modelo padrão."""
    tabela = tabela_padrao()
    assert tabela.versao and tabela.fonte and "fatura" in tabela.observacao
    assert tabela.preco_de("claude-opus-5-5") == Preco(Decimal("4.00"), Decimal("20.00"))
    assert tabela.preco_de("claude-opus-5-5-20261001") is not None
    assert tabela.preco_de("modelo-desconhecido") is None
    assert ler_tabela(CAMINHO_PRECOS) == tabela


def test_custo_por_milhao_de_tokens() -> None:
    """Um milhão de tokens de entrada e meio de saída a 4 e 20 dólares custam 14 dólares."""
    assert custo(Preco(Decimal(4), Decimal(20)), 1_000_000, 500_000) == Decimal("14.0000")


def test_tabela_alternativa_e_lida(tmp_path: Path) -> None:
    """Outra tabela (nova versão) pode ser lida do disco."""
    arquivo = tmp_path / "precos.yaml"
    arquivo.write_text(
        'versao: "x"\nfonte: "f"\nmoeda: "USD"\nobservacao: "o"\n'
        "modelos:\n  m:\n    entrada_por_milhao: 1\n    saida_por_milhao: 2\n",
        encoding="utf-8",
    )
    assert ler_tabela(arquivo).preco_de("m") == Preco(Decimal(1), Decimal(2))


@pytest.mark.integracao
def test_custo_estimado_por_processo_e_por_usuario(
    sessao: Session, engine_teste: Engine, chamada_teste: ChamadaTeste
) -> None:
    """RF-AUD-05: soma chat e resumo, separa autores e explicita modelos sem preço."""
    autor = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    outro = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    processo = criar_processo_teste(engine_teste, autor)
    conversa = gravar_hub(sessao, hub_conversa, {"conversa_id": uuid4()}, "teste")
    chamada_teste(sessao, processo, autor.hk, "claude-opus-5-5", conversa)
    chamada_teste(sessao, processo, outro.hk, "claude-opus-5-5", None)
    chamada_teste(sessao, processo, autor.hk, "modelo-x", None)
    por_processo = custo_estimado(sessao, FiltroAuditoria(processo_id=processo.hex()))
    assert por_processo["total"] == "4.0000" and por_processo["moeda"] == "USD"
    assert {m["modelo"]: m["custo"] for m in por_processo["por_modelo"]} == {
        "claude-opus-5-5": "4.0000",
        "modelo-x": None,
    }
    assert custo_estimado(sessao, FiltroAuditoria(usuario_id=autor.id))["total"] == "2.0000"
    assert custo_estimado(sessao, FiltroAuditoria(usuario_id=outro.id))["total"] == "2.0000"
    assert custo_estimado(sessao, FiltroAuditoria(usuario_id="0" * 64))["total"] == "0.0000"
