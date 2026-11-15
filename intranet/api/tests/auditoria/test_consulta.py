"""Consulta por filtros, exportação e relatório com a cadeia única da 0.2."""

import csv
import io
import json
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from apoio_comum import UsuarioTeste, criar_processo_teste, eventos_do_banco
from lupa_intranet.auditoria.eventos import AcaoAuditoria, NovoEvento
from lupa_intranet.auditoria.registrador import registrar
from lupa_pipeline.dominio.enums import PapelUsuario
from lupa_pipeline.logging import CAMPOS_PROIBIDOS
from tests.auditoria.conftest import ChamadaTeste
from tests.conftest import SENHA_TESTE, criar_usuario_teste, logar

pytestmark = pytest.mark.integracao


@pytest.fixture
def desembargador(cliente: TestClient, engine_teste: Engine) -> UsuarioTeste:
    """Desembargador autenticado no cliente HTTPS."""
    usuario = criar_usuario_teste(engine_teste, PapelUsuario.DESEMBARGADOR)
    logar(cliente, engine_teste, usuario)
    return usuario


def test_consulta_filtra_pagina_por_cursor_e_registra_o_ato(
    cliente: TestClient, engine_teste: Engine, desembargador: UsuarioTeste
) -> None:
    """RF-AUD-01, RF-AUD-04: os filtros, os ids hex e a localização sobrevivem à paginação."""
    processo = criar_processo_teste(engine_teste, desembargador)
    with Session(engine_teste) as sessao, sessao.begin():
        for acao in [AcaoAuditoria.PAGINA_VISTA] * 5 + [AcaoAuditoria.BUSCA]:
            registrar(
                sessao,
                NovoEvento(acao=acao, hk_processo=processo, hk_usuario=desembargador.hk),
            )
    params = {"processo_id": processo.hex(), "acao": "pagina_vista", "limite": "2"}
    vistos: list[str] = []
    while True:
        resposta = cliente.get("/auditoria", params=params)
        assert resposta.status_code == 200
        pagina = resposta.json()
        vistos.extend(e["id"] for e in pagina["eventos"])
        if pagina["proximo_cursor"] is None:
            break
        params["cursor"] = pagina["proximo_cursor"]
    assert len(vistos) == len(set(vistos)) == 5
    assert all(len(bytes.fromhex(ident)) == 32 for ident in vistos)
    consultas = eventos_do_banco(
        engine_teste, usuario_id=desembargador.id, acao="auditoria_consultada"
    )
    assert consultas[-1].hk_processo == processo
    assert consultas[-1].ip and "Fictícia" in (consultas[-1].localizacao or "")
    assert cliente.get("/auditoria", params={"cursor": "lixo"}).status_code == 422
    assert cliente.get("/auditoria", params={"processo_id": "invalido"}).status_code == 422
    ausente = cliente.get("/auditoria", params={"processo_id": "0" * 64})
    assert ausente.status_code == 200 and ausente.json()["eventos"] == []


def test_assessor_nao_ve_auditoria(cliente: TestClient, engine_teste: Engine) -> None:
    """RF-ACE-03: cada rota de auditoria exige o papel desembargador."""
    logar(cliente, engine_teste, criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR))
    for rota in ("", "/verificar", "/exportar", "/relatorio-uso"):
        assert cliente.get(f"/auditoria{rota}").status_code == 403, rota


@pytest.mark.parametrize("formato", ["csv", "json"])
def test_exportacao_em_csv_e_json_registra_o_proprio_ato(
    cliente: TestClient, engine_teste: Engine, desembargador: UsuarioTeste, formato: str
) -> None:
    """RF-AUD-01, RF-AUD-04: exporta os eventos filtrados e grava auditoria_exportada."""
    processo = criar_processo_teste(engine_teste, desembargador)
    with Session(engine_teste) as sessao, sessao.begin():
        registrar(sessao, NovoEvento(acao=AcaoAuditoria.BUSCA, hk_processo=processo))
    resposta = cliente.get(
        "/auditoria/exportar", params={"formato": formato, "processo_id": processo.hex()}
    )
    assert resposta.status_code == 200
    assert f"auditoria.{formato}" in resposta.headers["content-disposition"]
    linhas = (
        list(csv.DictReader(io.StringIO(resposta.text))) if formato == "csv" else resposta.json()
    )
    assert [linha["acao"] for linha in linhas] == ["busca"]
    eventos = eventos_do_banco(
        engine_teste, usuario_id=desembargador.id, acao="auditoria_exportada"
    )
    assert eventos[-1].hk_processo == processo


def test_relatorio_de_uso_por_processo_e_por_usuario(
    cliente: TestClient,
    engine_teste: Engine,
    desembargador: UsuarioTeste,
    chamada_teste: ChamadaTeste,
) -> None:
    """RF-AUD-05: JSON e CSV contam chamadas no período e custeiam chat e resumos por autor."""
    processo = criar_processo_teste(engine_teste, desembargador)
    assessor = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    with Session(engine_teste) as sessao, sessao.begin():
        chamada_teste(sessao, processo, assessor.hk, "claude-opus-5-5", None)
        chamada_teste(sessao, processo, desembargador.hk, "modelo-sem-preco", None)
        chamada_teste(sessao, processo, desembargador.hk, "claude-opus-5-5", None)
    inicios = [e.ocorrido_em for e in eventos_do_banco(engine_teste, processo_id=processo.hex())]
    periodo = {
        "inicio": inicios[1].isoformat(),
        "fim": (inicios[-1] + timedelta(seconds=1)).isoformat(),
    }
    por_processo = cliente.get(
        "/auditoria/relatorio-uso", params={"processo": processo.hex(), **periodo}
    ).json()
    assert por_processo["contagem_por_acao"] == {"chamada_modelo": 2}
    assert por_processo["primeiro_acesso"] <= por_processo["ultimo_acesso"]
    assert por_processo["chamadas_modelo"] == [
        {"versao_modelo": modelo, "versao_prompt": "p1", "total": 1}
        for modelo in ("claude-opus-5-5", "modelo-sem-preco")
    ]
    assert por_processo["custo_estimado"]["total"] == "2.0000"
    assert por_processo["custo_estimado"]["por_modelo"][1]["custo"] is None
    por_usuario = cliente.get(
        "/auditoria/relatorio-uso", params={"usuario": assessor.id, **periodo}
    ).json()
    assert por_usuario["custo_estimado"]["total"] == "0.0000"
    exportacao = cliente.get("/auditoria/relatorio-uso", params={"formato": "csv", **periodo})
    assert exportacao.status_code == 200
    assert "text/csv" in exportacao.headers["content-type"]
    linhas = [
        x
        for x in csv.DictReader(io.StringIO(exportacao.text))
        if x["processo_id"] == processo.hex()
    ]
    assert len(linhas) == 1
    assert linhas[0]["usuario_id"] == desembargador.id
    assert linhas[0]["chamadas_modelo"] == "2" and linhas[0]["custo_estimado"] == "2.0000"
    assert linhas[0]["chamadas_sem_preco"] == "1" and linhas[0]["versao_tabela"]
    assert eventos_do_banco(
        engine_teste,
        usuario_id=desembargador.id,
        objeto_tipo="relatorio_uso",
        acao="auditoria_exportada",
    )
    assert cliente.get("/auditoria/relatorio-uso").status_code == 422


def test_filtros_por_intervalo_usuario_e_ip(
    cliente: TestClient, engine_teste: Engine, desembargador: UsuarioTeste
) -> None:
    """RF-AUD-04: intervalo semiaberto e filtros por usuário e IP."""
    with Session(engine_teste) as sessao, sessao.begin():
        eventos = [
            registrar(
                sessao, NovoEvento(acao=AcaoAuditoria.BUSCA, hk_usuario=desembargador.hk, ip=ip)
            )
            for ip in ("203.0.113.1", "203.0.113.2")
        ]
    params = {
        "usuario_id": desembargador.id,
        "acao": "busca",
        "inicio": eventos[0]["ocorrido_em"].isoformat(),
        "fim": eventos[1]["ocorrido_em"].isoformat(),
        "ip": "203.0.113.1",
    }
    pagina = cliente.get("/auditoria", params=params).json()["eventos"]
    assert [x["id"] for x in pagina] == [eventos[0]["hk_evento"].hex()]
    assert cliente.get("/auditoria", params=params | {"ip": "203.0.113.2"}).json()["eventos"] == []


def test_desembargador_verifica_cadeia_unica(
    cliente: TestClient, desembargador: UsuarioTeste
) -> None:
    """RF-AUD-03: a verificação atravessa a cadeia de todos os usuários."""
    resposta = cliente.get("/auditoria/verificar").json()
    assert resposta["integra"] and resposta["total"] >= 2
    assert resposta["primeira_sequencia_quebrada"] is None


def test_nenhum_evento_contem_campo_proibido_nem_segredo(
    cliente: TestClient, engine_teste: Engine, desembargador: UsuarioTeste
) -> None:
    """RF-AUD-02: eventos persistidos não contêm senha, token nem texto sintético do fluxo."""
    criado = cliente.post(
        "/usuarios", json={"nome_usuario": f"x_{uuid4().hex[:8]}", "papel": "assessor"}
    )
    segredos = [
        SENHA_TESTE,
        criado.json()["senha_temporaria"],
        "senha-digitada-no-usuario",
        cliente.cookies["lupa_sessao"],
    ]
    cliente.post("/auth/login", json={"nome_usuario": segredos[2], "senha": SENHA_TESTE})
    resposta = cliente.get("/auditoria/exportar", params={"formato": "json"}).json()
    assert resposta and all(not (CAMPOS_PROIBIDOS & set(evento)) for evento in resposta)
    assert all(s not in json.dumps(resposta, ensure_ascii=False) for s in segredos)
    with pytest.raises(ValueError, match="extra"):
        NovoEvento.model_validate({"acao": "busca", "texto": "conteúdo dos autos"})
