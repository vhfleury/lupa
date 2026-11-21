"""Conversão do domínio para o motor e do achado calculado para persistência."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from apoio_comum import FabricaFato, criar_pagina, criar_processo
from lupa_pipeline.dominio.enums import TipoFato
from lupa_pipeline.dominio.gravacao import chave_do_hub
from lupa_pipeline.dominio.repositorios import (
    listar_achados,
    listar_fatos_por_processo,
    salvar_achado,
    salvar_fato,
)
from lupa_pipeline.dominio.tabelas import hub_achado
from lupa_pipeline.dominio.visoes import VisaoProcesso
from lupa_pipeline.validacoes.adaptador import para_dominio
from lupa_pipeline.validacoes.apoio import data_de
from lupa_pipeline.validacoes.modelo import ModeloProcesso
from lupa_pipeline.validacoes.motor import executar_catalogo
from tests.validacoes.conftest import PROCESSO_SINTETICO, SUJEITO, criar_fato, id_sintetico


def test_data_de_aceita_string_iso_e_date() -> None:
    """RF-VAL-02: datas de fatos lidos do banco e montados no código têm a mesma contagem."""
    assert data_de(criar_fato("data_intimacao", "2030-01-02")) == date(2030, 1, 2)
    assert data_de(criar_fato("data_intimacao", date(2030, 1, 2))) == date(2030, 1, 2)
    with pytest.raises(ValueError):
        data_de(criar_fato("data_intimacao", None))


def test_para_dominio_vincula_processo_sujeito_e_fontes() -> None:
    """RF-VAL-01: achado serializável mantém o sujeito, o hk e os fatos da validação."""
    fatos = [
        criar_fato("tipo_recurso", "apelacao_civel"),
        criar_fato("data_intimacao", "2026-08-03"),
        criar_fato("data_interposicao", "2026-08-24"),
        criar_fato("qualidade_recorrente", "particular"),
    ]
    achados = executar_catalogo(ModeloProcesso(fatos), "apelacao_civel", date(2026, 8, 24))
    assert len(achados) == 3
    for calculado in achados:
        hk = id_sintetico(calculado.validacao)
        achado = para_dominio(calculado, PROCESSO_SINTETICO, hk)
        assert (achado.id, achado.processo_id, achado.sujeito) == (hk, PROCESSO_SINTETICO, SUJEITO)
        assert achado.fatos_usados == calculado.fatos_usados
        assert achado.model_dump_json()


@pytest.mark.integracao
def test_ida_e_volta_pelo_data_vault_preserva_referencias(
    sessao: Session, fabrica_fato: FabricaFato
) -> None:
    """RF-VAL-01 e RF-FAT-01: achados do catálogo voltam com os valores e fatos que os sustentam."""
    processo = criar_processo(sessao)
    pagina = criar_pagina(sessao, processo)
    for tipo, valor in (
        (TipoFato.TIPO_RECURSO, "apelacao_civel"),
        (TipoFato.DATA_INTIMACAO, "2026-08-03"),
        (TipoFato.DATA_INTERPOSICAO, "2026-08-24"),
        (TipoFato.QUALIDADE_RECORRENTE, "particular"),
    ):
        salvar_fato(sessao, fabrica_fato(processo, pagina, tipo, valor))
    lidos = listar_fatos_por_processo(sessao, processo)
    assert len(lidos) == 4
    calculados = executar_catalogo(ModeloProcesso(lidos), "apelacao_civel", date(2026, 8, 24))
    cnj = sessao.get_one(VisaoProcesso, processo).numero_cnj
    novos = []
    for calculado in calculados:
        hk = chave_do_hub(
            hub_achado,
            {"numero_cnj": cnj, "validacao": calculado.validacao, "sujeito": calculado.sujeito},
        )
        achado = para_dominio(calculado, processo.hex(), hk.hex())
        assert salvar_achado(sessao, achado)
        novos.append(achado)
    voltaram = {a.id: a for a in listar_achados(sessao, processo)}
    assert len(voltaram) == len(novos) == 3
    assert any(a.resultado == "conforme" for a in novos)
    for achado in novos:
        assert voltaram[achado.id].model_dump(exclude={"criado_em"}) == achado.model_dump(
            exclude={"criado_em"}
        )
