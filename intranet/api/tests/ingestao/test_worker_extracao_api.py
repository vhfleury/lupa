"""Rotas de diagnóstico, relatório e alertas de um arquivo extraído pelo worker (4C.8 a 4C.10)."""

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from apoio_arquivos import INSTRUCAO_OCULTA, INSTRUCAO_XMP, pdf_com_injecao
from apoio_comum import criar_gabinete_teste, criar_processo_teste, eventos_do_banco
from apoio_ingestao import calcular_hash_bytes
from lupa_pipeline.dominio.enums import EstadoJob, PapelUsuario
from lupa_pipeline.ingestao.recepcao import ArquivoRecebido, TipoArquivo, lacrar
from lupa_pipeline.ingestao.storage import ArmazenamentoMemoria
from lupa_pipeline.ingestao.worker import Dependencias, processar_job
from tests.conftest import criar_usuario_teste, logar

pytestmark = pytest.mark.integracao


def test_rotas_de_diagnostico_e_relatorio_sao_auditadas_e_isoladas(
    app_teste: FastAPI,
    engine_teste: Engine,
    deps_extracao: Dependencias,
    storage_memoria: ArmazenamentoMemoria,
    tmp_path: Any,
) -> None:
    """GET do diagnóstico, do relatório e dos alertas: 200 com dados, evento, 404 fora."""
    assessor = criar_usuario_teste(
        engine_teste, PapelUsuario.ASSESSOR, criar_gabinete_teste(engine_teste)
    )
    processo = criar_processo_teste(engine_teste, assessor)
    outro = criar_processo_teste(engine_teste, assessor)
    dados = pdf_com_injecao()
    caminho = tmp_path / "autos.pdf"
    caminho.write_bytes(dados)
    recebido = ArquivoRecebido(caminho, calcular_hash_bytes(dados), len(dados), TipoArquivo.PDF)
    with Session(engine_teste) as session, session.begin():
        assert assessor.gabinete_id is not None
        lacre = lacrar(
            session, storage_memoria, recebido, gabinete_id=assessor.gabinete_id,
            processo_id=processo, enviado_por=assessor.id, nome_original="autos.pdf",
        )  # fmt: skip
    cliente = TestClient(app_teste, base_url="https://testserver")
    logar(cliente, engine_teste, assessor)
    base = f"/processos/{processo}/arquivos/{lacre.arquivo_id}"
    assert cliente.get(f"{base}/diagnostico").status_code == 404
    assert cliente.get(f"{base}/relatorio").json()["relatorio"] is None

    assert processar_job(deps_extracao, lacre.job_id, assessor.gabinete_id) is EstadoJob.CONCLUIDO
    diagnostico = cliente.get(f"{base}/diagnostico")
    assert diagnostico.status_code == 200
    assert diagnostico.json()["cenario"] == "pdf_liso"
    relatorio = cliente.get(f"{base}/relatorio").json()
    assert relatorio["estado"] == "concluido"
    assert relatorio["relatorio"]["paginas_extraidas"] == 2
    fora = f"/processos/{outro}/arquivos/{lacre.arquivo_id}/relatorio"
    assert cliente.get(fora).status_code == 404
    assert relatorio["relatorio"]["saneamento"]["metadado_suspeito"] is True
    alertas = cliente.get(f"{base}/alertas")
    assert alertas.status_code == 200
    corpo = alertas.json()
    assert corpo["resumo"]["paginas_sinalizadas"] == 1
    assert {m["origem"] for m in corpo["metadados_suspeitos"]} == {"xmp", "anotacao"}
    primeira = corpo["paginas"][0]
    assert primeira["numero"] == 1
    assert {"texto_oculto", "padrao_instrucao", "metadado_suspeito"} <= set(primeira["flags"])
    assert all("texto" not in o for o in primeira["trechos_ocultos"])
    assert INSTRUCAO_OCULTA not in alertas.text and INSTRUCAO_XMP not in alertas.text
    assert cliente.get(f"/processos/{outro}/arquivos/{lacre.arquivo_id}/alertas").status_code == 404
    eventos = eventos_do_banco(engine_teste, processo_id=processo, acao="processo_aberto")
    assert len(eventos) >= 2
