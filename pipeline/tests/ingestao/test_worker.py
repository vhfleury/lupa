"""Validação de arquivos hostis no sandbox e quarentena no banco (A5)."""

import stat
from pathlib import Path
from threading import Event
from zipfile import ZipInfo

import pytest
from sqlalchemy.orm import Session, sessionmaker

from apoio_arquivos import (
    pdf_assinado,
    pdf_bomba,
    pdf_com_senha,
    pdf_corrompido,
    pdf_minimo,
    pdf_truncado,
    zip_cifrado,
    zip_com_info,
    zip_de,
)
from apoio_ingestao import SemearArquivo
from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.enums import MotivoQuarentena
from lupa_pipeline.dominio.visoes import VisaoArquivo
from lupa_pipeline.ingestao.processamento import processar_arquivo
from lupa_pipeline.ingestao.storage import StorageCifrado

pytestmark = pytest.mark.integracao


@pytest.mark.parametrize(
    ("dados", "nome", "motivo"),
    [
        (pdf_com_senha(), "autos.pdf", MotivoQuarentena.SENHA),
        (pdf_truncado(), "autos.pdf", MotivoQuarentena.TRUNCADO),
        (pdf_corrompido(), "autos.pdf", MotivoQuarentena.CORROMPIDO),
        (pdf_assinado(cobre_tudo=False), "autos.pdf", MotivoQuarentena.ASSINATURA_INVALIDA),
        (
            zip_de({"a.pdf": pdf_minimo(), "b.txt": b"texto"}),
            "a.zip",
            MotivoQuarentena.TIPO_INVALIDO,
        ),
        (zip_de({"../fora.pdf": pdf_minimo()}), "a.zip", MotivoQuarentena.ZIP_MALICIOSO),
        (zip_de({"p.pdf": pdf_com_senha()}), "a.zip", MotivoQuarentena.SENHA),
        (zip_cifrado(), "a.zip", MotivoQuarentena.SENHA),
        (b"PK\x03\x04" + b"\x00" * 64, "a.zip", MotivoQuarentena.CORROMPIDO),
    ],
    ids=[
        "senha",
        "truncado",
        "corrompido",
        "assinatura",
        "tipo",
        "zip_malicioso",
        "zip_senha",
        "zip_cifrado",
        "zip_corrompido",
    ],
)
def test_cada_falha_vai_para_quarentena_com_motivo_e_nao_avanca(
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
    storage_memoria: StorageCifrado,
    semear_arquivo: SemearArquivo,
    dados: bytes,
    nome: str,
    motivo: MotivoQuarentena,
) -> None:
    """RF-ING-02: cada original recusado mantém um motivo de quarentena consultável."""
    hk = semear_arquivo(dados, nome).hk_arquivo
    processar_arquivo(fabrica_sessao, settings_ficticias, storage_memoria, hk, Event())
    with fabrica_sessao() as session:
        arquivo = session.get_one(VisaoArquivo, hk)
        assert (arquivo.estado, arquivo.motivo_quarentena) == ("quarentena", motivo.value)


def test_link_simbolico_do_zip_eh_recusado(
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
    storage_memoria: StorageCifrado,
    semear_arquivo: SemearArquivo,
) -> None:
    """RF-ING-02: links simbólicos não são extraídos nem atravessam o diretório temporário."""
    info = ZipInfo("vinculo.pdf")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    hk = semear_arquivo(zip_com_info(info, b"/fora"), "vinculo.zip").hk_arquivo
    processar_arquivo(fabrica_sessao, settings_ficticias, storage_memoria, hk, Event())
    with fabrica_sessao() as session:
        assert session.get_one(VisaoArquivo, hk).motivo_quarentena == "zip_malicioso"


def test_bomba_de_descompressao_esgota_memoria_no_sandbox(
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
    storage_memoria: StorageCifrado,
    semear_arquivo: SemearArquivo,
    tmp_path: Path,
) -> None:
    """RF-ING-04: a morte do parser por memória marca falho e deixa o worker disponível."""
    arquivo = tmp_path / "bomba.pdf"
    pdf_bomba(arquivo, 768)
    hk = semear_arquivo(arquivo.read_bytes(), "bomba.pdf").hk_arquivo
    limites = settings_ficticias.model_copy(
        update={"sandbox_memoria_mb": 512, "sandbox_cpu_segundos": 20, "sandbox_tempo_segundos": 60}
    )
    processar_arquivo(fabrica_sessao, limites, storage_memoria, hk, Event())
    with fabrica_sessao() as session:
        assert session.get_one(VisaoArquivo, hk).motivo_falha == "limite_memoria"


def test_objeto_ausente_marca_falho(
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
    storage_memoria: StorageCifrado,
    semear_arquivo: SemearArquivo,
) -> None:
    """RF-ING-06: arquivo sem objeto termina com a falha específica."""
    arquivo = semear_arquivo(pdf_minimo())
    for chave in storage_memoria.listar("processo/" + arquivo.processo.hk_processo.hex() + "/"):
        storage_memoria.apagar(chave)
    processar_arquivo(
        fabrica_sessao, settings_ficticias, storage_memoria, arquivo.hk_arquivo, Event()
    )
    with fabrica_sessao() as session:
        assert session.get_one(VisaoArquivo, arquivo.hk_arquivo).motivo_falha == "arquivo_ausente"
