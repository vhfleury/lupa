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
    gerar_numero_cnj,
)
from lupa_intranet.api.rotas.processos import resumir_ingestao
from lupa_pipeline.dominio.chaves import chave_hash
from lupa_pipeline.dominio.enums import EstadoJob, PapelUsuario
from lupa_pipeline.dominio.esquemas import calcular_hash
from lupa_pipeline.dominio.gravacao import gravar_hub, gravar_link, gravar_satelite
from lupa_pipeline.dominio.tabelas import (
    hub_arquivo,
    link_processo_arquivo,
    sat_arquivo_dados,
    sat_arquivo_ingestao,
)
from lupa_pipeline.dominio.visoes import VisaoProcesso
from lupa_pipeline.ingestao.storage import chave_objeto
from lupa_pipeline.seguranca.contexto import ativar_processo
from tests.conftest import criar_usuario_teste, logar

pytestmark = pytest.mark.integracao


def _cliente(app: FastAPI, engine: Engine, usuario: UsuarioTeste) -> TestClient:
    cliente = TestClient(app, base_url="https://testserver")
    logar(cliente, engine, usuario)
    return cliente


def _corpo(sequencial: int, classe: str = "agravo_instrumento") -> dict[str, object]:
    return {"numero_cnj": gerar_numero_cnj(sequencial), "classe": classe}


def _semear_arquivo(engine: Engine, hk_processo: bytes, nome: str, estado: EstadoJob) -> None:
    with Session(engine) as session, session.begin():
        processo = session.scalars(
            select(VisaoProcesso).where(VisaoProcesso.hk_processo == hk_processo)
        ).one()
        ativar_processo(hk_processo, processo.chave_dados_cifrada)
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


def test_cadastro_com_classe_valida_o_cnj_e_recusa_duplicado_apontando_o_existente(
    app_teste: FastAPI, engine_teste: Engine
) -> None:
    """RF-PRO-01: 201 auditado; dígito errado dá 422; repetido dá 409 com o id do existente."""
    assessor = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    cliente = _cliente(app_teste, engine_teste, assessor)
    sequencial = uuid4().int % 9_000_000 + 1
    resposta = cliente.post("/processos", json=_corpo(sequencial))
    assert resposta.status_code == 201, resposta.text
    criado = resposta.json()
    numero = gerar_numero_cnj(sequencial)
    assert criado["id"] == chave_hash([numero.replace("-", "").replace(".", "")]).hex()
    assert (criado["classe"], criado["status"], criado["numero_cnj"]) == (
        "agravo_instrumento",
        "criado",
        numero,
    )
    eventos = eventos_do_banco(engine_teste, acao="processo_criado", objeto_id=criado["id"])
    assert [(e.resultado, e.processo_id) for e in eventos] == [("ok", criado["id"])]
    repetido = cliente.post("/processos", json=_corpo(sequencial, "apelacao_civel"))
    assert repetido.status_code == 409
    assert repetido.json()["processo_id"] == criado["id"]
    assert "já cadastrado" in repetido.json()["detail"]
    valido = gerar_numero_cnj(sequencial + 1)
    digito_errado = f"{(int(valido[8:10]) + 1) % 100:02d}"
    errado = _corpo(1) | {"numero_cnj": valido[:8] + digito_errado + valido[10:]}
    assert cliente.post("/processos", json=errado).status_code == 422


@pytest.mark.parametrize(
    "extra",
    [{"classe": "Apelação Criminal"}, {"materia": "civel"}, {"sigiloso": True}, {"classe": None}],
)
def test_cadastro_recusa_classe_fora_da_lista_e_campos_da_versao_anterior(
    app_teste: FastAPI, engine_teste: Engine, extra: dict[str, object]
) -> None:
    """RF-PRO-01, RF-PRO-04: classe só da seção 3.1; `materia` e `sigiloso` não existem."""
    assessor = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    corpo = _corpo(uuid4().int % 9_000_000 + 1) | extra
    resposta = _cliente(app_teste, engine_teste, assessor).post("/processos", json=corpo)
    assert resposta.status_code == 422


def test_lista_e_igual_para_dois_usuarios_com_classe_estado_e_responsaveis(
    app_teste: FastAPI, engine_teste: Engine
) -> None:
    """RF-PRO-02: dois usuários veem a mesma lista, com classe, ingestão e responsáveis."""
    assessor = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    desembargador = criar_usuario_teste(engine_teste, PapelUsuario.DESEMBARGADOR)
    cliente_assessor = _cliente(app_teste, engine_teste, assessor)
    cliente_desembargador = _cliente(app_teste, engine_teste, desembargador)
    criado = cliente_assessor.post("/processos", json=_corpo(uuid4().int % 9_000_000 + 1)).json()
    alheio = criar_processo_teste(engine_teste)
    _semear_arquivo(engine_teste, bytes.fromhex(criado["id"]), "a.pdf", EstadoJob.RECEBIDO)
    _semear_arquivo(engine_teste, bytes.fromhex(criado["id"]), "b.pdf", EstadoJob.QUARENTENA)

    lista_assessor = cliente_assessor.get("/processos")
    lista_desembargador = cliente_desembargador.get("/processos")
    assert lista_assessor.status_code == lista_desembargador.status_code == 200
    assert lista_assessor.json() == lista_desembargador.json()
    ids = [p["id"] for p in lista_assessor.json()]
    assert criado["id"] in ids and alheio.hex() in ids
    item = next(p for p in lista_assessor.json() if p["id"] == criado["id"])
    assert item["classe"] == "agravo_instrumento"
    assert item["ingestao"]["situacao"] == "processando"
    assert item["ingestao"]["por_estado"] == {"recebido": 1, "quarentena": 1}
    assert [r["id"] for r in item["responsaveis"]] == [assessor.id]
    assert eventos_do_banco(engine_teste, acao="busca", usuario_id=assessor.id)

    arquivos = cliente_desembargador.get(f"/processos/{criado['id']}/arquivos")
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
    meu = cliente_a.post("/processos", json=_corpo(uuid4().int % 9_000_000 + 1)).json()["id"]
    colega = cliente_b.post("/processos", json=_corpo(uuid4().int % 9_000_000 + 1)).json()["id"]
    do_gestor = gestor.post("/processos", json=_corpo(uuid4().int % 9_000_000 + 1)).json()["id"]
    assert {p["id"] for p in cliente_a.get("/processos?meus=true").json()} == {meu}
    assert {meu, colega, do_gestor} <= {p["id"] for p in cliente_a.get("/processos").json()}
    assert gestor.get("/processos?meus=true").json() == []
    assert cliente_b.get(f"/processos/{meu}").status_code == 200
