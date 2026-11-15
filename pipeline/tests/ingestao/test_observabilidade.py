"""Logs do worker com PDF e ZIP processados em banco e sandbox reais."""

import json
from threading import Event

import pytest
from sqlalchemy.orm import Session, sessionmaker

from apoio_arquivos import TEXTO_SENTINELA, pdf_com_senha, pdf_texto, zip_por_peca
from apoio_ingestao import SemearArquivo
from lupa_pipeline.config import Settings
from lupa_pipeline.ingestao.processamento import processar_arquivo
from lupa_pipeline.ingestao.storage import ObjectStorage
from lupa_pipeline.logging import CAMPOS_PROIBIDOS, configurar_logging


@pytest.mark.integracao
def test_nenhum_log_do_worker_carrega_texto_dos_autos(
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
    storage_memoria: ObjectStorage,
    semear_arquivo: SemearArquivo,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """RF-AUD-02. Somente identificadores, estados e contagens podem ir ao log."""
    configurar_logging(nivel="DEBUG", estrito=True)
    capsys.readouterr()
    for dados, ext in [
        (zip_por_peca(2), "zip"),
        (pdf_texto([TEXTO_SENTINELA + "-log"]), "pdf"),
        (pdf_com_senha(), "pdf"),
    ]:
        arquivo = semear_arquivo(dados, f"{TEXTO_SENTINELA}.{ext}")
        processar_arquivo(
            fabrica_sessao, settings_ficticias, storage_memoria, arquivo.hk_arquivo, Event()
        )
    saida = capsys.readouterr()
    assert TEXTO_SENTINELA not in saida.out + saida.err
    linhas = [json.loads(x) for x in saida.out.splitlines() if x.strip()]
    assert {"lote_gravado", "arquivo_finalizado"} <= {x["event"] for x in linhas}
    assert all(not CAMPOS_PROIBIDOS.intersection(k.lower() for k in x) for x in linhas)
