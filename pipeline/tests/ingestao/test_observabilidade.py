"""Testes de observabilidade: logs do worker sem texto dos autos."""

import json

import pytest

from apoio_arquivos import TEXTO_SENTINELA, pdf_com_senha, pdf_minimo, zip_por_peca
from apoio_ingestao import SemearJob
from lupa_pipeline.ingestao.worker import Dependencias, processar_job
from lupa_pipeline.logging import CAMPOS_PROIBIDOS, configurar_logging

pytestmark = pytest.mark.integracao


def test_nenhum_log_do_worker_carrega_texto_dos_autos(
    deps: Dependencias, semear_job: SemearJob, capsys: pytest.CaptureFixture[str]
) -> None:
    """Logs só com ids, estados e contagens: sem o texto sentinela, sem nome de arquivo."""
    configurar_logging(nivel="DEBUG", estrito=True)
    nome_sensivel = f"{TEXTO_SENTINELA}-nome.zip"
    trabalhos = [
        semear_job(zip_por_peca(2), nome_sensivel),
        semear_job(pdf_minimo(2), f"{TEXTO_SENTINELA}.pdf"),
        semear_job(pdf_com_senha(), "senha.pdf"),
    ]
    capsys.readouterr()
    for job in trabalhos:
        processar_job(deps, job.job_id, job.processo.gabinete_id)
    saida = capsys.readouterr()
    linhas = [json.loads(linha) for linha in saida.out.splitlines() if linha.strip()]
    assert linhas, "o worker deveria ter emitido logs"
    assert TEXTO_SENTINELA not in saida.out + saida.err
    for linha in linhas:
        assert not CAMPOS_PROIBIDOS & {chave.lower() for chave in linha}
    eventos = {linha["event"] for linha in linhas}
    assert {"lote_gravado", "job_finalizado"} <= eventos
