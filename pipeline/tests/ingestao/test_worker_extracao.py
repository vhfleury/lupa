"""Retentativas e resultados dos lotes do worker real (A5)."""

from threading import Event

import pytest
from sqlalchemy.orm import Session, sessionmaker

from apoio_arquivos import pdf_texto
from apoio_ingestao import SemearArquivo
from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.enums import MotivoFalha
from lupa_pipeline.dominio.visoes import VisaoArquivo
from lupa_pipeline.ingestao import processamento
from lupa_pipeline.ingestao.extracao import ResultadoTarefa, Tarefa, executar_tarefa
from lupa_pipeline.ingestao.sandbox import LimitesSandbox
from lupa_pipeline.ingestao.storage import ObjectStorage

pytestmark = pytest.mark.integracao


@pytest.mark.parametrize(
    ("motivo", "estado", "tentativas"),
    [
        (MotivoFalha.TEMPO_ESGOTADO, "parcial", 3),
        (MotivoFalha.ERRO_PARSER, "parcial", 3),
        (MotivoFalha.LIMITE_CPU, "falho", 1),
        (MotivoFalha.LIMITE_MEMORIA, "falho", 1),
    ],
)
def test_retentativas_e_paginas_faltantes(
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
    storage_memoria: ObjectStorage,
    semear_arquivo: SemearArquivo,
    monkeypatch: pytest.MonkeyPatch,
    motivo: MotivoFalha,
    estado: str,
    tentativas: int,
) -> None:
    """RF-ING-04, RF-ING-06: retenta falhas recuperáveis e identifica folhas faltantes."""
    hk = semear_arquivo(pdf_texto([f"falha {motivo.value}", "outra folha"])).hk_arquivo
    erros = []

    def simular(tarefa: Tarefa, limites: LimitesSandbox) -> ResultadoTarefa:
        if tarefa.inicio == 1:
            erros.append(tarefa.inicio)
            return ResultadoTarefa(tarefa, [], motivo)
        return executar_tarefa(tarefa, limites)

    monkeypatch.setattr(processamento, "executar_tarefa", simular)
    settings = settings_ficticias.model_copy(
        update={"max_retentativas": 2, "extracao_paginas_por_lote": 1}
    )
    processamento.processar_arquivo(fabrica_sessao, settings, storage_memoria, hk, Event())
    with fabrica_sessao() as session:
        arquivo = session.get_one(VisaoArquivo, hk)
        assert (arquivo.estado, len(erros)) == (estado, tentativas)
        if estado == "parcial":
            assert arquivo.relatorio["paginas_faltando_lista"] == [1]
        else:
            assert arquivo.motivo_falha == motivo.value
