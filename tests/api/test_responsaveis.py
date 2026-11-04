"""Responsabilidade compartilhada, transferência e isolamento por gabinete."""

import pytest
from fastapi import FastAPI
from sqlalchemy import Engine

from lupa.dominio.enums import PapelUsuario
from tests.api.test_processos import _criar_processo
from tests.api.test_processos_lista import _cliente
from tests.conftest import criar_gabinete_teste, criar_usuario_teste, eventos_do_banco

pytestmark = pytest.mark.integracao


def test_compartilhar_transferir_e_bloquear_atribuicao_invalida(
    app_teste: FastAPI, engine_teste: Engine
) -> None:
    """Vínculos controlam meus processos sem alterar o gabinete nem o criador."""
    gabinete = criar_gabinete_teste(engine_teste)
    a = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR, gabinete)
    b = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR, gabinete)
    des = criar_usuario_teste(engine_teste, PapelUsuario.DESEMBARGADOR, gabinete)
    outro = criar_usuario_teste(
        engine_teste, PapelUsuario.ASSESSOR, criar_gabinete_teste(engine_teste)
    )
    processo = _criar_processo(engine_teste, a)
    rota = f"/processos/{processo}/responsaveis"
    ca, cb, gestor = (_cliente(app_teste, engine_teste, u) for u in (a, b, des))
    inicial = gestor.get(rota).json()
    assert [r["id"] for r in inicial["responsaveis"]] == [str(a.id)]
    assert {r["id"] for r in inicial["disponiveis"]} == {str(a.id), str(b.id)}
    assert ca.get(rota).json()["disponiveis"] == []
    corpo = {"usuarios": [str(a.id), str(b.id)], "anteriores": [str(a.id)]}
    assert ca.post(rota, json=corpo).status_code == 403
    assert gestor.post(rota, json=corpo).status_code == 200
    lista = gestor.get("/processos").json()
    listado = next(p for p in lista if p["id"] == str(processo))
    assert {u["id"] for u in listado["responsaveis"]} == {str(a.id), str(b.id)}
    assert all(u["ativo"] for u in listado["responsaveis"])
    for cliente in (ca, cb):
        assert str(processo) in {p["id"] for p in cliente.get("/processos?meus=true").json()}
    assert gestor.post(rota, json=corpo).status_code == 409
    anteriores = [str(a.id), str(b.id)]
    for ids in ([], [str(outro.id)], [str(des.id)], [str(b.id), str(b.id)]):
        assert (
            gestor.post(rota, json={"usuarios": ids, "anteriores": anteriores}).status_code == 422
        )
    assert (
        gestor.post(rota, json={"usuarios": [str(b.id)], "anteriores": anteriores}).status_code
        == 200
    )
    assert ca.get("/processos?meus=true").json() == []
    assert [p["id"] for p in cb.get("/processos?meus=true").json()] == [str(processo)]
    estrangeiro = _cliente(app_teste, engine_teste, outro)
    assert estrangeiro.get(rota).status_code == 404
    assert estrangeiro.post(rota, json=corpo).status_code == 404
    assert (
        len(eventos_do_banco(engine_teste, acao="responsavel_adicionado", processo_id=processo))
        == 1
    )
    assert (
        len(eventos_do_banco(engine_teste, acao="responsavel_removido", processo_id=processo)) == 1
    )


def test_migracao_preserva_responsavel_dos_processos_existentes(engine_teste: Engine) -> None:
    """Upgrade atribui o criador assessor dos processos anteriores à migração."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from lupa.dominio.tabelas import ProcessoResponsavelTabela
    from tests.conftest import migrar

    migrar(engine_teste, "0010", descer=True)
    try:
        gabinete = criar_gabinete_teste(engine_teste)
        assessor = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR, gabinete)
        processo = _criar_processo(engine_teste, assessor)
    finally:
        migrar(engine_teste, "head")
    with Session(engine_teste) as sessao:
        ids = list(
            sessao.scalars(
                select(ProcessoResponsavelTabela.usuario_id).where(
                    ProcessoResponsavelTabela.processo_id == processo
                )
            )
        )
        assert ids == [assessor.id]


def test_admin_pode_atribuir_mas_nao_a_assessor_desativado(
    app_teste: FastAPI, engine_teste: Engine
) -> None:
    """Administrador gerencia os vínculos; assessor desativado não recebe novas atribuições."""
    from sqlalchemy.orm import Session

    from lupa.dominio.tabelas import UsuarioTabela

    gabinete = criar_gabinete_teste(engine_teste)
    a = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR, gabinete)
    b = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR, gabinete)
    admin = criar_usuario_teste(engine_teste, PapelUsuario.ADMINISTRADOR, None)
    processo = _criar_processo(engine_teste, a)
    cliente = _cliente(app_teste, engine_teste, admin)
    rota = f"/processos/{processo}/responsaveis"
    corpo = {"usuarios": [str(b.id)], "anteriores": [str(a.id)]}
    with Session(engine_teste) as sessao, sessao.begin():
        usuario = sessao.get(UsuarioTabela, b.id)
        assert usuario is not None
        usuario.ativo = False
    assert cliente.post(rota, json=corpo).status_code == 422
    with Session(engine_teste) as sessao, sessao.begin():
        usuario = sessao.get(UsuarioTabela, b.id)
        assert usuario is not None
        usuario.ativo = True
    assert cliente.post(rota, json=corpo).status_code == 200
