"""Repositórios de fatos e achados contra PostgreSQL real.

Fase 3 (D23): reescritos sobre o Data Vault em T3.10. A migração, o trigger de fato sem evidência
e o nome só em coluna autorizada estão em `test_migracao_0001.py`; a imutabilidade, em
`test_gravacao.py`; a RLS saiu com os gabinetes (T3.2).
"""

from uuid import UUID, uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, delete, insert, inspect, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from apoio_comum import FabricaFato, FabricaProcesso, criar_pagina, migrar
from lupa_pipeline.dominio.enums import ResultadoAchado, TipoFato
from lupa_pipeline.dominio.esquemas import Achado
from lupa_pipeline.dominio.repositorios import (
    ProcessoNaoEncontradoError,
    listar_achados,
    listar_fatos_por_processo,
    salvar_achado,
    salvar_fato,
)
from lupa_pipeline.dominio.sessao import assumir_papel_aplicacao, definir_gabinete
from lupa_pipeline.dominio.tabelas import (
    TABELAS_COM_GABINETE,
    AchadoTabela,
    Base,
    FatoEvidenciaTabela,
    FatoTabela,
    ProcessoTabela,
)

pytestmark = pytest.mark.integracao


def _forcar_constraints(sessao: Session) -> None:
    sessao.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def _achado(processo_id: UUID, fatos: tuple[UUID, ...] = ()) -> Achado:
    return Achado(
        processo_id=processo_id,
        validacao="tempestividade_recurso",
        versao_catalogo="2025.1",
        resultado=ResultadoAchado.CONFORME,
        fatos_usados=fatos,
        valores={"prazo_dias": 5, "base_legal": "art. 593 CPP"},
        explicacao="Recurso tempestivo.",
    )


def test_fato_salvo_volta_com_evidencias(
    sessao: Session, processo_id: UUID, pagina_id: UUID, fabrica_fato: FabricaFato
) -> None:
    """`salvar_fato` e `listar_fatos_por_processo` preservam o contrato do `Fato`."""
    primeiro = fabrica_fato(processo_id=processo_id, pagina_id=pagina_id)
    segundo = fabrica_fato(
        processo_id=processo_id, pagina_id=pagina_id, tipo=TipoFato.PENA_MAXIMA_ABSTRATA, valor=48
    )
    salvar_fato(sessao, primeiro)
    salvar_fato(sessao, segundo)
    _forcar_constraints(sessao)
    fatos = {fato.id: fato for fato in listar_fatos_por_processo(sessao, processo_id)}
    assert set(fatos) == {primeiro.id, segundo.id}
    assert fatos[primeiro.id].evidencias == primeiro.evidencias
    assert fatos[segundo.id].valor == 48
    assert fatos[segundo.id].tipo is TipoFato.PENA_MAXIMA_ABSTRATA


def test_salvar_fato_de_processo_inexistente_falha(
    sessao: Session, fabrica_fato: FabricaFato
) -> None:
    """Processo desconhecido (ou invisível pela RLS) gera erro claro."""
    with pytest.raises(ProcessoNaoEncontradoError):
        salvar_fato(sessao, fabrica_fato())
    with pytest.raises(ProcessoNaoEncontradoError):
        salvar_achado(sessao, _achado(uuid4()))


def test_achado_salvo_e_listado(sessao: Session, processo_id: UUID) -> None:
    """`salvar_achado` e `listar_achados` fazem ida e volta completa."""
    fatos_usados = (uuid4(), uuid4())
    achado = _achado(processo_id, fatos_usados)
    salvar_achado(sessao, achado)
    assert listar_achados(sessao, processo_id) == [achado]


