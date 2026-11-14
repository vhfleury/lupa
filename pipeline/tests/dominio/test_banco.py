"""Repositórios, correção humana e vigência no Data Vault real."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apoio_comum import criar_pagina, criar_processo
from lupa_pipeline.dominio.correcoes import corrigir_fato
from lupa_pipeline.dominio.enums import ResultadoAchado, StatusFato, TipoFato
from lupa_pipeline.dominio.esquemas import Achado, Evidencia, Fato
from lupa_pipeline.dominio.repositorios import (
    listar_achados,
    listar_fatos_por_processo,
    salvar_achado,
    salvar_fato,
)
from lupa_pipeline.dominio.tabelas import sat_achado_resultado, sat_fato_valor
from lupa_pipeline.dominio.visoes import VisaoProcesso

pytestmark = pytest.mark.integracao


def evidencia(pagina: bytes, trecho: str, inicio: int) -> Evidencia:
    """RF-FAT-01. Monta o trecho da página sintética nos offsets indicados."""
    return Evidencia(
        id="0" * 64, pagina_id=pagina.hex(), trecho=trecho, inicio=inicio, fim=inicio + len(trecho)
    )


def test_correcao_troca_evidencias_preserva_id_e_reprocessamento(sessao: Session) -> None:
    """RF-FAT-03. A prova humana permanece sob o mesmo identificador no replay."""
    processo = criar_processo(sessao)
    autor = sessao.get_one(VisaoProcesso, processo).hk_criador
    assert autor
    pagina = criar_pagina(sessao, processo, "intimado em 03/03, retificado para 05/03")
    origem = evidencia(pagina, "03/03", 12)
    novo = evidencia(pagina, "05/03", 35)
    candidato = Fato(
        id="0" * 64,
        processo_id=processo.hex(),
        tipo=TipoFato.DATA_INTIMACAO,
        valor="2025-03-03",
        evidencias=(origem,),
        extraido_por="certidao",
        versao_extrator="1",
        confianca=1,
    )
    hk = salvar_fato(sessao, candidato)
    (fato,) = listar_fatos_por_processo(sessao, processo)
    assert fato.id == hk.hex()
    corrigir_fato(sessao, fato, StatusFato.CORRIGIDO, autor, "2025-03-05", novo)
    assert salvar_fato(sessao, candidato) == hk
    (vigente,) = listar_fatos_por_processo(sessao, processo)
    assert (vigente.id, vigente.valor, vigente.status) == (
        fato.id,
        "2025-03-05",
        StatusFato.CORRIGIDO,
    )
    assert [e.trecho for e in vigente.evidencias] == ["05/03"]
    assert (
        sessao.scalar(
            select(func.count()).select_from(sat_fato_valor).where(sat_fato_valor.c.hk_fato == hk)
        )
        == 2
    )


def test_recusa_evidencia_de_outro_processo_ou_trecho_incorreto(sessao: Session) -> None:
    """RF-FAT-01. Uma evidência precisa pertencer ao processo e ao trecho."""
    externo = criar_processo(sessao)
    pagina_externa = criar_pagina(sessao, externo, "origem")
    processo = criar_processo(sessao)
    pagina = criar_pagina(sessao, processo, "outra")
    for pagina_id in (pagina_externa, pagina):
        candidato = Fato(
            id="0" * 64,
            processo_id=processo.hex(),
            tipo=TipoFato.TIPO_RECURSO,
            valor="apelacao_civel",
            evidencias=(evidencia(pagina_id, "origem", 0),),
            extraido_por="teste",
            versao_extrator="1",
            confianca=1,
        )
        with pytest.raises(ValueError):
            salvar_fato(sessao, candidato)
    assert listar_fatos_por_processo(sessao, processo) == []


def test_achado_so_grava_quando_muda(sessao: Session) -> None:
    """RES-13. O satélite de resultado só ganha versão quando os atributos mudam."""
    processo = criar_processo(sessao)
    achado = Achado(
        id="0" * 64,
        processo_id=processo.hex(),
        validacao="tempestividade_recurso",
        versao_catalogo="1",
        resultado=ResultadoAchado.VERIFICAR,
        explicacao="Falta data.",
    )
    assert salvar_achado(sessao, achado)
    assert not salvar_achado(sessao, achado)
    (atual,) = listar_achados(sessao, processo)
    assert atual.id != achado.id and atual.explicacao == achado.explicacao
    assert salvar_achado(sessao, achado.model_copy(update={"explicacao": "Falta certidão."}))
    assert (
        sessao.scalar(
            select(func.count())
            .select_from(sat_achado_resultado)
            .where(sat_achado_resultado.c.hk_achado == bytes.fromhex(atual.id))
        )
        == 2
    )
