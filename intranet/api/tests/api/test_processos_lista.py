"""Cadastro, lista e arquivos do processo (RF-PRO-01, RF-PRO-02, RF-PRO-03)."""

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from apoio_comum import (
    ORIGEM_TESTE,
    UsuarioTeste,
    criar_processo_teste,
    eventos_do_banco,
)
from lupa_api.api.rotas.processos import resumir_ingestao
from lupa_pipeline.dominio.enums import ClasseProcessual, EstadoJob, PapelUsuario
from lupa_pipeline.dominio.esquemas import calcular_hash
from lupa_pipeline.dominio.gravacao import gravar_hub, gravar_link, gravar_satelite
from lupa_pipeline.dominio.tabelas import (
    hub_arquivo,
    link_processo_arquivo,
    link_processo_responsavel,
    sat_arquivo_dados,
    sat_arquivo_ingestao,
    sat_processo_responsavel_vigencia,
)
from lupa_pipeline.dominio.visoes import VisaoProcesso
from lupa_pipeline.ingestao.storage import chave_objeto
from tests.conftest import criar_usuario_teste, logar

pytestmark = pytest.mark.integracao


def _cliente(app: FastAPI, engine: Engine, usuario: UsuarioTeste) -> TestClient:
    cliente = TestClient(app, base_url="https://testserver")
    logar(cliente, engine, usuario)
    return cliente


def processo_com_responsavel(engine: Engine, assessor: UsuarioTeste) -> str:
    """Prepara processo e vínculo inicial para os testes da lista e de responsáveis."""
    hk = criar_processo_teste(engine, assessor, classe=ClasseProcessual.AGRAVO_INSTRUMENTO)
    with Session(engine) as session, session.begin():
        vinculo = gravar_link(
            session,
            link_processo_responsavel,
            {"hk_processo": hk, "hk_usuario": assessor.hk},
            ORIGEM_TESTE,
        )
        gravar_satelite(
            session, sat_processo_responsavel_vigencia, vinculo, {"vigente": True}, ORIGEM_TESTE
        )
    return hk.hex()


def _semear_arquivo(engine: Engine, hk_processo: bytes, nome: str, estado: EstadoJob) -> None:
    with Session(engine) as session, session.begin():
        processo = session.scalars(
            select(VisaoProcesso).where(VisaoProcesso.hk_processo == hk_processo)
        ).one()
        sha256 = calcular_hash(uuid4().hex)
        chave = {"numero_cnj": processo.numero_cnj, "sha256": sha256}
        hk_arquivo = gravar_hub(session, hub_arquivo, chave, ORIGEM_TESTE)
        ligacao = {"hk_processo": hk_processo, "hk_arquivo": hk_arquivo}
        gravar_link(session, link_processo_arquivo, ligacao, ORIGEM_TESTE)
        dados = {
            "tamanho_bytes": 10,
            "nome_original": nome,
            "mime": "application/pdf",
            "chave_storage": chave_objeto(hk_processo, sha256),
            "hk_usuario": processo.hk_criador,
        }
        gravar_satelite(session, sat_arquivo_dados, hk_arquivo, dados, ORIGEM_TESTE)
        ingestao = {
            "estado": estado.value,
            "motivo_quarentena": "senha" if estado is EstadoJob.QUARENTENA else None,
            "motivo_falha": None,
            "tentativas": 0,
            "total_paginas": None,
            "manifesto": None,
            "relatorio": None,
            "versao_extrator": None,
        }
        gravar_satelite(session, sat_arquivo_ingestao, hk_arquivo, ingestao, ORIGEM_TESTE)


def test_lista_e_igual_para_dois_usuarios_com_classe_estado_e_responsaveis(
    app_teste: FastAPI, engine_teste: Engine
) -> None:
    """RF-PRO-02: dois usuários veem a mesma lista, com classe, ingestão e responsáveis."""
    assessor = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    desembargador = criar_usuario_teste(engine_teste, PapelUsuario.DESEMBARGADOR)
    cliente_assessor = _cliente(app_teste, engine_teste, assessor)
    cliente_desembargador = _cliente(app_teste, engine_teste, desembargador)
    criado = processo_com_responsavel(engine_teste, assessor)
    alheio = criar_processo_teste(engine_teste)
    _semear_arquivo(engine_teste, bytes.fromhex(criado), "a.pdf", EstadoJob.RECEBIDO)
    _semear_arquivo(engine_teste, bytes.fromhex(criado), "b.pdf", EstadoJob.QUARENTENA)

    lista_assessor = cliente_assessor.get("/processos")
    lista_desembargador = cliente_desembargador.get("/processos")
    assert lista_assessor.status_code == lista_desembargador.status_code == 200
    assert lista_assessor.json() == lista_desembargador.json()
    ids = [p["id"] for p in lista_assessor.json()]
    assert criado in ids and alheio.hex() in ids
    item = next(p for p in lista_assessor.json() if p["id"] == criado)
    assert item["classe"] == "agravo_instrumento"
    assert item["ingestao"]["situacao"] == "processando"
    assert item["ingestao"]["por_estado"] == {"recebido": 1, "quarentena": 1}
    assert [r["id"] for r in item["responsaveis"]] == [assessor.id]
    assert eventos_do_banco(engine_teste, acao="busca", usuario_id=assessor.id)

    arquivos = cliente_desembargador.get(f"/processos/{criado}/arquivos")
    assert arquivos.status_code == 200
    corpo = arquivos.json()
    assert {(a["nome"], a["estado"]) for a in corpo["arquivos"]} == {
        ("a.pdf", "recebido"),
        ("b.pdf", "quarentena"),
    }
    assert {a["motivo_quarentena"] for a in corpo["arquivos"]} == {None, "senha"}


@pytest.mark.parametrize(
    ("estados", "esperado"),
    [
        ([], "sem_arquivos"),
        (["recebido", "concluido"], "processando"),
        (["quarentena"], "quarentena"),
        (["quarentena", "falho"], "falho"),
        (["concluido", "em_revisao"], "pendencias"),
        (["concluido", "parcial"], "pendencias"),
        (["concluido", "quarentena"], "concluido"),
    ],
)
def test_resumo_da_ingestao(estados: list[str], esperado: str) -> None:
    """RF-PRO-02: situação agregada a partir dos estados dos arquivos."""
    assert resumir_ingestao(estados) == esperado


def test_meus_processos_filtra_pelo_responsavel_sem_restringir_a_lista(
    app_teste: FastAPI, engine_teste: Engine
) -> None:
    """RF-PRO-03: o assessor que cadastra é o responsável; a lista completa não muda."""
    a = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    b = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    desembargador = criar_usuario_teste(engine_teste, PapelUsuario.DESEMBARGADOR)
    cliente_a = _cliente(app_teste, engine_teste, a)
    cliente_b = _cliente(app_teste, engine_teste, b)
    gestor = _cliente(app_teste, engine_teste, desembargador)
    meu = processo_com_responsavel(engine_teste, a)
    colega = processo_com_responsavel(engine_teste, b)
    do_gestor = criar_processo_teste(engine_teste, desembargador).hex()
    assert {p["id"] for p in cliente_a.get("/processos?meus=true").json()} == {meu}
    assert {meu, colega, do_gestor} <= {p["id"] for p in cliente_a.get("/processos").json()}
    assert gestor.get("/processos?meus=true").json() == []
    assert cliente_b.get(f"/processos/{meu}").status_code == 200
