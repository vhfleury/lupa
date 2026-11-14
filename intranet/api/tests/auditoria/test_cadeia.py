"""Imutabilidade e concorrência na cadeia de auditoria (RF-AUD-03)."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from apoio_comum import eventos_do_banco
from lupa_intranet.auditoria.eventos import AcaoAuditoria, NovoEvento
from lupa_intranet.auditoria.registrador import registrar, verificar_cadeia
from lupa_pipeline.dominio.sessao import assumir_papel_aplicacao

pytestmark = pytest.mark.integracao


@pytest.mark.parametrize(
    "verbo",
    ["UPDATE link_evento_auditoria SET resultado = 'falha'", "DELETE FROM link_evento_auditoria"],
)
def test_aplicacao_nao_pode_alterar_eventos(sessao: Session, verbo: str) -> None:
    """RF-AUD-03: a aplicação só pode inserir eventos."""
    registrar(sessao, NovoEvento(acao=AcaoAuditoria.BUSCA))
    assumir_papel_aplicacao(sessao)
    with pytest.raises(DBAPIError, match="permission denied"):
        sessao.execute(text(verbo))


def test_truncate_da_cadeia_e_recusado_mesmo_pelo_dono(sessao: Session) -> None:
    """RF-AUD-03: a proteção da cadeia recusa limpar a tabela inteira em um TRUNCATE."""
    registrar(sessao, NovoEvento(acao=AcaoAuditoria.BUSCA))
    with pytest.raises(DBAPIError, match="imutável"):
        sessao.execute(text("TRUNCATE link_evento_auditoria"))


@pytest.mark.parametrize("acao", ["apagar", "encadeamento", "conteudo"])
def test_cadeia_aponta_primeira_sequencia_afetada(sessao: Session, acao: str) -> None:
    """RF-AUD-03: remoção ou adulteração estoura na primeira sequência inconsistente."""
    seq = [registrar(sessao, NovoEvento(acao=AcaoAuditoria.BUSCA))["sequencia"] for _ in range(3)]
    sessao.execute(text("ALTER TABLE link_evento_auditoria DISABLE TRIGGER USER"))
    if acao == "apagar":
        comando = "DELETE FROM link_evento_auditoria WHERE sequencia = :seq"
        primeira, motivo = seq[2], "sequencia"
    elif acao == "encadeamento":
        comando = "UPDATE link_evento_auditoria SET hash_anterior = 'x' WHERE sequencia = :seq"
        primeira, motivo = seq[1], "encadeamento"
    else:
        comando = "UPDATE link_evento_auditoria SET objeto_id = 'alterado' WHERE sequencia = :seq"
        primeira, motivo = seq[1], "hash"
    sessao.execute(text(comando), {"seq": seq[1]})
    resultado = verificar_cadeia(sessao)
    assert not resultado.integra
    assert (resultado.primeira_sequencia_quebrada, resultado.motivo) == (primeira, motivo)


def test_registros_concorrentes_seguem_cadeia_unica(
    fabrica_sessao: sessionmaker[Session], engine_teste: Engine
) -> None:
    """RF-AUD-03: transações concorrentes produzem uma única cadeia sem lacunas."""
    marca = uuid4().hex
    barreira = Barrier(4)

    def gravar() -> None:
        barreira.wait(timeout=10)
        for _ in range(10):
            with fabrica_sessao.begin() as sessao:
                assumir_papel_aplicacao(sessao)
                registrar(sessao, NovoEvento(acao=AcaoAuditoria.BUSCA, objeto_id=marca))

    with ThreadPoolExecutor(max_workers=4) as executor:
        tarefas = [executor.submit(gravar) for _ in range(4)]
        for tarefa in tarefas:
            tarefa.result(timeout=30)
    eventos = eventos_do_banco(engine_teste, objeto_id=marca)
    assert len(eventos) == len({e.hash_anterior for e in eventos}) == 40
    with Session(engine_teste) as sessao:
        assert verificar_cadeia(sessao).integra


def test_falha_de_login_sem_usuario_integra_a_mesma_cadeia(
    cliente: TestClient, engine_teste: Engine
) -> None:
    """RF-AUD-02, RF-AUD-03: tentativa desconhecida entra na cadeia só com metadados."""
    nome = f"ninguem_{uuid4().hex[:8]}"
    cliente.post("/auth/login", json={"nome_usuario": nome, "senha": "senha-qualquer-x"})
    ultimo = eventos_do_banco(engine_teste, acao="login_falha")[-1]
    assert (ultimo.hk_usuario, ultimo.hk_processo, ultimo.objeto_id) == (None, None, None)
    with Session(engine_teste) as sessao:
        assert verificar_cadeia(sessao).integra
