"""Testes da máquina de estados do job e dos esquemas da ingestão (sem banco)."""

from itertools import product

import pytest
from pydantic import ValidationError

from lupa_pipeline.dominio.enums import CenarioArquivo, EstadoJob, MotivoQuarentena
from lupa_pipeline.dominio.esquemas import (
    DiagnosticoArquivo,
    EntradaManifesto,
    calcular_hash,
)
from lupa_pipeline.ingestao.estados import (
    ESTADOS_FINAIS,
    TransicaoInvalidaError,
    exigir_transicao,
    transicao,
)

E = EstadoJob

PERMITIDAS = {
    (E.RECEBIDO, E.VALIDADO),
    (E.RECEBIDO, E.FALHO),
    (E.RECEBIDO, E.QUARENTENA),
    (E.VALIDADO, E.EM_EXTRACAO),
    (E.VALIDADO, E.FALHO),
    (E.VALIDADO, E.QUARENTENA),
    (E.EM_EXTRACAO, E.PARCIAL),
    (E.EM_EXTRACAO, E.EM_REVISAO),
    (E.EM_EXTRACAO, E.CONCLUIDO),
    (E.EM_EXTRACAO, E.FALHO),
    (E.EM_EXTRACAO, E.QUARENTENA),
    (E.PARCIAL, E.EM_EXTRACAO),
    (E.PARCIAL, E.EM_REVISAO),
    (E.PARCIAL, E.FALHO),
    (E.EM_REVISAO, E.EM_EXTRACAO),
    (E.EM_REVISAO, E.CONCLUIDO),
    (E.EM_REVISAO, E.FALHO),
    (E.FALHO, E.RECEBIDO),
}


@pytest.mark.parametrize(("atual", "novo"), list(product(E, E)))
def test_matriz_completa_de_transicoes(atual: EstadoJob, novo: EstadoJob) -> None:
    """Cada um dos 64 pares tem exatamente o resultado da tabela acima."""
    assert transicao(atual, novo) is ((atual, novo) in PERMITIDAS)


def test_concluido_nunca_volta_para_em_extracao() -> None:
    """O critério da subetapa, explícito."""
    assert not transicao(E.CONCLUIDO, E.EM_EXTRACAO)
    with pytest.raises(TransicaoInvalidaError):
        exigir_transicao(E.CONCLUIDO, E.EM_EXTRACAO)


def test_concluido_e_quarentena_sao_finais() -> None:
    """Estados finais não têm destino."""
    assert frozenset({E.CONCLUIDO, E.QUARENTENA}) == ESTADOS_FINAIS
    assert not any(transicao(E.QUARENTENA, novo) for novo in E)


def test_exigir_transicao_valida_nao_lanca() -> None:
    """Transição permitida passa em silêncio."""
    exigir_transicao(E.RECEBIDO, E.VALIDADO)


def test_entrada_de_manifesto_exige_hash_valido() -> None:
    """Hash precisa ter 64 hexadecimais."""
    with pytest.raises(ValidationError):
        EntradaManifesto(ordem=1, nome="a.pdf", tamanho_bytes=1, sha256="x")
    entrada = EntradaManifesto(ordem=1, nome="a.pdf", tamanho_bytes=1, sha256="a" * 64)
    assert entrada.ordem == 1


def test_diagnostico_valida_campos() -> None:
    """O diagnóstico recusa cenário fora do enum e campo extra, e começa sem sinais."""
    with pytest.raises(ValidationError):
        DiagnosticoArquivo(
            arquivo_id=calcular_hash("arquivo"), cenario="outro", total_paginas=1, tem_indice=False
        )
    diagnostico = DiagnosticoArquivo(
        arquivo_id=calcular_hash("arquivo"),
        cenario=CenarioArquivo.PDF_LISO,
        total_paginas=3,
        tem_indice=False,
    )
    assert diagnostico.sinais == {}
    with pytest.raises(ValidationError, match="extra_forbidden"):
        DiagnosticoArquivo.model_validate(diagnostico.model_dump() | {"fencing_token": 1})


def test_quarentena_tem_texto_legivel_para_cada_motivo() -> None:
    """Toda entrada do enum tem descrição; resultado do parser vira motivo."""
    from lupa_pipeline.ingestao.quarentena import descrever, motivo_do_parser

    assert all(descrever(motivo) for motivo in MotivoQuarentena)
    assert motivo_do_parser({"ok": True}) is None
    assert motivo_do_parser({"ok": False, "motivo_quarentena": "senha"}) is MotivoQuarentena.SENHA
    assert motivo_do_parser({"ok": False, "motivo_quarentena": "?"}) is (
        MotivoQuarentena.CORROMPIDO
    )
