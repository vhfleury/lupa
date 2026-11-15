"""Revisão do cadastro pelo arquivo e histórico de classe (RF-PRO-06, RF-FAT-01)."""

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Session

from apoio_comum import banco_vazio, criar_processo, migrar
from lupa_pipeline.dominio.gravacao import gravar_hub, gravar_satelite
from lupa_pipeline.dominio.tabelas import hub_usuario, sat_processo_dados

pytestmark = pytest.mark.integracao
TIPOS_CAPA = {
    "relator",
    "orgao_julgador",
    "assunto",
    "valor_causa",
    "juizo_origem",
    "data_distribuicao",
}


def _check(engine: Engine) -> str:
    return next(
        c["sqltext"]
        for c in inspect(engine).get_check_constraints("hub_fato")
        if c["name"] == "ck_hub_fato_tipo_valido"
    )


def test_subir_e_descer_preserva_o_criador_e_restaura_o_check() -> None:
    """RF-PRO-06, RF-FAT-01: dados anteriores sobrevivem e o downgrade restaura a revisão."""
    with banco_vazio("cadastro") as engine:
        migrar(engine, "0001")
        check_anterior = _check(engine)
        colunas = [c["name"] for c in inspect(engine).get_columns("v_processo")]
        assert all(tipo not in check_anterior for tipo in TIPOS_CAPA)
        with Session(engine) as session, session.begin():
            criador = gravar_hub(session, hub_usuario, {"nome_usuario": "criador"}, "teste")
            hk = criar_processo(session, criador=criador)
        migrar(engine, "head")
        assert all(tipo in _check(engine) for tipo in TIPOS_CAPA)
        consulta = text(
            "SELECT hk_criador, criador_id, classe, classe_anterior, hk_classe_corrigida_por, "
            "classe_corrigida_por_id, classe_corrigida_em FROM v_processo"
        )
        with Session(engine) as session, session.begin():
            assert tuple(session.execute(consulta).one()) == (
                criador,
                criador.hex(),
                "apelacao_civel",
                None,
                None,
                None,
                None,
            )
            autor = gravar_hub(session, hub_usuario, {"nome_usuario": "corretor"}, "teste")
            for classe in ("agravo_interno", "acao_originaria"):
                gravar_satelite(
                    session,
                    sat_processo_dados,
                    hk,
                    {"classe": classe, "hk_usuario": autor},
                    "teste",
                )
            linha = session.execute(consulta).one()
            assert tuple(linha)[:-1] == (
                criador,
                criador.hex(),
                "acao_originaria",
                "agravo_interno",
                autor,
                autor.hex(),
            )
            assert linha.classe_corrigida_em == session.scalar(
                text("SELECT max(load_dts) FROM sat_processo_dados")
            )
        migrar(engine, "0001", descer=True)
        assert _check(engine) == check_anterior
        assert [c["name"] for c in inspect(engine).get_columns("v_processo")] == colunas
        migrar(engine, "head")
