"""Views `v_*` mapeadas só para leitura (D12, D13; RES-02)."""

import pytest
from sqlalchemy import Engine, inspect, select
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.gravacao import gravar_hub, gravar_satelite
from lupa_pipeline.dominio.sessao import assumir_papel_aplicacao
from lupa_pipeline.dominio.tabelas import hub_usuario, sat_usuario_cadastro
from lupa_pipeline.dominio.visoes import BaseVisao, VisaoSomenteLeituraError, VisaoUsuario
from lupa_pipeline.migrations.esquema_v0001 import VISOES

pytestmark = pytest.mark.integracao

ORIGEM = "teste"


def test_toda_view_da_migracao_esta_mapeada() -> None:
    """D13: a API lê por classes de `dominio.visoes`, uma por view criada na revisão."""
    assert set(BaseVisao.metadata.tables) == set(VISOES)


def test_colunas_mapeadas_sao_as_da_view(engine_teste: Engine) -> None:
    """D13: cada classe tem exatamente as colunas da view no banco."""
    inspetor = inspect(engine_teste)
    for nome, tabela in BaseVisao.metadata.tables.items():
        no_banco = {coluna["name"] for coluna in inspetor.get_columns(nome)}
        assert set(tabela.columns.keys()) == no_banco, nome


def _cadastro(sessao: Session, hk: bytes, papel: str, ativo: bool) -> None:
    gravar_satelite(sessao, sat_usuario_cadastro, hk, {"papel": papel, "ativo": ativo}, ORIGEM)


def test_view_traz_a_linha_mais_recente_do_satelite(sessao: Session) -> None:
    """RES-02: `v_usuario` mostra o cadastro corrente e o `id` em hex do `hk` (D12)."""
    hk = gravar_hub(sessao, hub_usuario, {"nome_usuario": "assessor.dois"}, ORIGEM)
    _cadastro(sessao, hk, "assessor", True)
    _cadastro(sessao, hk, "assessor", False)
    usuario = sessao.scalars(select(VisaoUsuario).where(VisaoUsuario.hk_usuario == hk)).one()
    assert (usuario.id, usuario.nome_usuario, usuario.ativo) == (hk.hex(), "assessor.dois", False)


def test_papel_da_aplicacao_le_as_views(sessao: Session) -> None:
    """RES-13: `lupa_app` tem SELECT nas views."""
    hk = gravar_hub(sessao, hub_usuario, {"nome_usuario": "assessor.tres"}, ORIGEM)
    _cadastro(sessao, hk, "desembargador", True)
    assumir_papel_aplicacao(sessao)
    papel = sessao.scalar(select(VisaoUsuario.papel).where(VisaoUsuario.hk_usuario == hk))
    assert papel == "desembargador"


def test_view_recusa_gravacao_pelo_orm(sessao: Session) -> None:
    """D13: gravar por uma view é recusado antes de chegar ao banco."""
    hk = gravar_hub(sessao, hub_usuario, {"nome_usuario": "assessor.quatro"}, ORIGEM)
    _cadastro(sessao, hk, "assessor", True)
    usuario = sessao.scalars(select(VisaoUsuario).where(VisaoUsuario.hk_usuario == hk)).one()
    usuario.ativo = False
    with pytest.raises(VisaoSomenteLeituraError, match="v_usuario"):
        sessao.flush()
