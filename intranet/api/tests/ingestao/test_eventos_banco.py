"""Correspondência dos fatos, das partes e dos resultados com os autos enviados."""

from datetime import date

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.tabelas import sat_achado_resultado, sat_fato_valor
from lupa_pipeline.dominio.visoes import VisaoAchado, VisaoFato, VisaoParte, VisaoProcesso
from lupa_pipeline.ingestao.eventos.etapa import processar_eventos
from lupa_pipeline.seguranca.contexto import ativar_processo
from tests.ingestao.conftest import Autos


@pytest.mark.integracao
def test_eventos_e_reprocessamento_idempotente(autos_civeis: Autos, engine_teste: Engine) -> None:
    """RF-FAT-01, RF-FAT-04, RF-ING-08: o replay mantém as provas e as versões."""
    hk = autos_civeis.processo
    with Session(engine_teste) as s, s.begin():
        ativar_processo(hk, s.get_one(VisaoProcesso, hk).chave_dados_cifrada)
        partes = s.scalars(select(VisaoParte).where(VisaoParte.hk_processo == hk))
        assert {(p.nome, p.polo) for p in partes} == {
            ("Marina do Lago", "ativo"),
            ("Instituto das Flores", "passivo"),
        }
        fatos = select(VisaoFato.hk_fato).where(VisaoFato.hk_processo == hk)
        achados = select(VisaoAchado.hk_achado).where(VisaoAchado.hk_processo == hk)
        quantidades = [
            select(func.count()).select_from(tab).where(col.in_(ids))
            for tab, col, ids in (
                (sat_fato_valor, sat_fato_valor.c.hk_fato, fatos),
                (sat_achado_resultado, sat_achado_resultado.c.hk_achado, achados),
            )
        ]
        antes = [s.scalar(q) for q in quantidades]
        resultado = processar_eventos(s, hk, date(2025, 4, 30))
        assert resultado["achados_gravados"] == 0 and [s.scalar(q) for q in quantidades] == antes
        assert {
            a.resultado for a in s.scalars(select(VisaoAchado).where(VisaoAchado.hk_processo == hk))
        } == {"conforme"}
