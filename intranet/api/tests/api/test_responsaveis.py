"""Responsáveis do processo: compartilhar, transferir e recusar atribuição inválida (RF-PRO-03)."""

from uuid import uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from apoio_comum import ORIGEM_TESTE, criar_processo_teste, eventos_do_banco
from lupa_pipeline.dominio.enums import PapelUsuario
from lupa_pipeline.dominio.gravacao import gravar_satelite
from lupa_pipeline.dominio.tabelas import sat_usuario_cadastro
from lupa_pipeline.dominio.visoes import VisaoResponsavel
from tests.api.test_processos_lista import _cliente, _corpo
from tests.conftest import criar_usuario_teste

pytestmark = pytest.mark.integracao


def _vigencias(engine: Engine, processo_id: str) -> list[tuple[str, bool | None]]:
    with Session(engine) as session:
        linhas = session.scalars(
            select(VisaoResponsavel).where(VisaoResponsavel.processo_id == processo_id)
        )
        return sorted((linha.usuario_id, linha.vigente) for linha in linhas)


def test_desembargador_compartilha_e_transfere_e_assessor_nao_altera(
    app_teste: FastAPI, engine_teste: Engine
) -> None:
    """RF-PRO-03: vínculos mudam por linha nova de vigência e controlam `meus` processos."""
    a = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    b = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    desembargador = criar_usuario_teste(engine_teste, PapelUsuario.DESEMBARGADOR)
    ca, cb, gestor = (_cliente(app_teste, engine_teste, u) for u in (a, b, desembargador))
    processo = ca.post("/processos", json=_corpo(uuid4().int % 9_000_000 + 1)).json()["id"]
    rota = f"/processos/{processo}/responsaveis"
    inicial = gestor.get(rota).json()
    assert [r["id"] for r in inicial["responsaveis"]] == [a.id]
    assert {a.id, b.id} <= {r["id"] for r in inicial["disponiveis"]}
    assert desembargador.id not in {r["id"] for r in inicial["disponiveis"]}
    assert inicial["pode_gerir"] is True
    visto_pelo_assessor = ca.get(rota).json()
    assert (visto_pelo_assessor["disponiveis"], visto_pelo_assessor["pode_gerir"]) == ([], False)
    corpo = {"usuarios": [a.id, b.id], "anteriores": [a.id]}
    assert ca.post(rota, json=corpo).status_code == 403
    assert gestor.post(rota, json=corpo).status_code == 200
    listado = next(p for p in gestor.get("/processos").json() if p["id"] == processo)
    assert {u["id"] for u in listado["responsaveis"]} == {a.id, b.id}
    assert all(u["ativo"] for u in listado["responsaveis"])
    for cliente in (ca, cb):
        assert processo in {p["id"] for p in cliente.get("/processos?meus=true").json()}
    assert gestor.post(rota, json=corpo).status_code == 409
    anteriores = [a.id, b.id]
    for ids in ([], [desembargador.id], [b.id, b.id], ["zz"]):
        resposta = gestor.post(rota, json={"usuarios": ids, "anteriores": anteriores})
        assert resposta.status_code == 422, ids
    transferido = gestor.post(rota, json={"usuarios": [b.id], "anteriores": anteriores})
    assert transferido.status_code == 200
    assert [r["id"] for r in transferido.json()["responsaveis"]] == [b.id]
    assert ca.get("/processos?meus=true").json() == []
    assert [p["id"] for p in cb.get("/processos?meus=true").json()] == [processo]
    assert _vigencias(engine_teste, processo) == sorted([(a.id, False), (b.id, True)])
    adicionados = eventos_do_banco(
        engine_teste, acao="responsavel_adicionado", processo_id=processo
    )
    removidos = eventos_do_banco(engine_teste, acao="responsavel_removido", processo_id=processo)
    assert [e.objeto_id for e in adicionados] == [b.id]
    assert [e.objeto_id for e in removidos] == [a.id]


def test_assessor_desativado_nao_recebe_atribuicao(
    app_teste: FastAPI, engine_teste: Engine
) -> None:
    """RF-PRO-03: só assessor ativo pode ser responsável; reativado, volta a poder."""
    a = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    b = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    desembargador = criar_usuario_teste(engine_teste, PapelUsuario.DESEMBARGADOR)
    processo = criar_processo_teste(engine_teste, a).hex()
    gestor = _cliente(app_teste, engine_teste, desembargador)
    rota = f"/processos/{processo}/responsaveis"
    assert gestor.get(rota).json()["responsaveis"] == []
    corpo = {"usuarios": [b.id], "anteriores": []}
    for ativo, esperado in ((False, 422), (True, 200)):
        with Session(engine_teste) as session, session.begin():
            cadastro = {"papel": PapelUsuario.ASSESSOR.value, "ativo": ativo}
            gravar_satelite(session, sat_usuario_cadastro, b.hk, cadastro, ORIGEM_TESTE)
        assert gestor.post(rota, json=corpo).status_code == esperado
