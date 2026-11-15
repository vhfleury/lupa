"""Correção da classe processual por quem tem a permissão de anotar."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from apoio_comum import criar_processo_teste, eventos_do_banco
from lupa_pipeline.dominio.enums import PapelUsuario
from lupa_pipeline.dominio.tabelas import sat_processo_dados
from tests.conftest import criar_usuario_teste, logar

pytestmark = pytest.mark.integracao


@pytest.mark.parametrize("papel", list(PapelUsuario))
def test_correcao_preserva_autoria_e_reexecuta_validacoes_da_nova_classe(
    cliente: TestClient, engine_teste: Engine, papel: PapelUsuario
) -> None:
    """RF-PRO-06: corrigir é auditado, produz achados aplicáveis e repetir não grava linha."""
    criador = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    autor = criar_usuario_teste(engine_teste, papel)
    hk = criar_processo_teste(engine_teste, criador)
    base = f"/processos/{hk.hex()}"
    logar(cliente, engine_teste, autor)
    dados = {"classe": "agravo_instrumento"}
    resposta = cliente.post(base + "/classe", json=dados)
    assert resposta.status_code == 200, resposta.text
    processo = resposta.json()
    assert processo["classe_anterior"] == "apelacao_civel"
    assert processo["classe"] == dados["classe"]
    assert processo["criador_id"] == criador.id
    assert processo["classe_corrigida_por_id"] == autor.id
    assert processo["classe_corrigida_em"]
    assert cliente.get(base).json() == processo
    achados = cliente.get(base + "/achados").json()["achados"]
    assert {a["validacao"] for a in achados} == {
        "tempestividade_recurso",
        "representacao_recurso",
        "preparo_recurso",
        "cabimento_agravo",
    }
    assert cliente.post(base + "/classe", json=dados).json() == processo
    for acao in ("classe_corrigida", "validacao_executada"):
        eventos = eventos_do_banco(engine_teste, acao=acao, processo_id=hk.hex())
        assert [(e.usuario_id, e.resultado) for e in eventos] == [(autor.id, "ok")]
    with Session(engine_teste) as sessao:
        linhas = (
            select(func.count())
            .select_from(sat_processo_dados)
            .where(sat_processo_dados.c.hk_processo == hk)
        )
        assert sessao.scalar(linhas) == 2


def test_correcao_do_processo_descartado_devolve_conflito(
    cliente: TestClient, engine_teste: Engine
) -> None:
    """RF-PRO-06: o descarte impede gravar uma classe, mesmo com a permissão de anotar."""
    gestor = criar_usuario_teste(engine_teste, PapelUsuario.DESEMBARGADOR)
    hk = criar_processo_teste(engine_teste, gestor)
    logar(cliente, engine_teste, gestor)
    base = f"/processos/{hk.hex()}"
    assert cliente.post(base + "/descartar").status_code == 200
    assert cliente.post(base + "/classe", json={"classe": "acao_originaria"}).status_code == 409
    assert not eventos_do_banco(engine_teste, acao="classe_corrigida", processo_id=hk.hex())
