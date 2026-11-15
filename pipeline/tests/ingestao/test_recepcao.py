"""Testes da recepção em streaming, do lacre e do estado do arquivo (RF-ING-01, 02 e 06)."""

import hashlib
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from apoio_arquivos import pdf_minimo, zip_por_peca
from apoio_ingestao import lacrar_bytes, semear_processo
from lupa_pipeline.config import get_settings
from lupa_pipeline.dominio.enums import EstadoJob
from lupa_pipeline.dominio.tabelas import sat_arquivo_ingestao
from lupa_pipeline.dominio.visoes import VisaoArquivo
from lupa_pipeline.ingestao import repositorio
from lupa_pipeline.ingestao.estados import TransicaoInvalidaError
from lupa_pipeline.ingestao.recepcao import (
    MotivoRecusa,
    RecepcaoRecusadaError,
    ResultadoLacre,
    TipoArquivo,
    detectar_tipo,
    extensao_confere,
    lacrar,
    receber,
)
from lupa_pipeline.ingestao.storage import (
    ArmazenamentoMemoria,
    StorageCifrado,
    chave_objeto,
    criar_storage,
)
from lupa_pipeline.seguranca.contexto import contexto_cifra


async def _blocos(dados: bytes, tamanho: int = 7) -> AsyncIterator[bytes]:
    for inicio in range(0, len(dados), tamanho):
        yield dados[inicio : inicio + tamanho]


def test_tipo_pelo_conteudo() -> None:
    """Bytes mágicos decidem o tipo."""
    assert detectar_tipo(b"%PDF-1.7") is TipoArquivo.PDF
    assert detectar_tipo(b"PK\x03\x04rest") is TipoArquivo.ZIP
    assert detectar_tipo(b"MZ\x90\x00") is None
    assert detectar_tipo(b"PK\x05\x06") is None


def test_extensao_conhecida_que_contradiz_o_conteudo() -> None:
    """`.pdf` com ZIP dentro é recusado; extensão desconhecida não decide nada."""
    assert extensao_confere("autos.PDF", TipoArquivo.PDF)
    assert not extensao_confere("autos.pdf", TipoArquivo.ZIP)
    assert extensao_confere("autos.bin", TipoArquivo.ZIP)


async def test_recebe_em_blocos_com_hash_tamanho_e_tipo(tmp_path: Path) -> None:
    """Hash calculado no streaming é igual ao hash do conteúdo inteiro."""
    dados = pdf_minimo(2)
    recebido = await receber(_blocos(dados), "autos.pdf", 10_000_000, tmp_path)
    assert recebido.sha256 == hashlib.sha256(dados).hexdigest()
    assert (recebido.tamanho_bytes, recebido.tipo) == (len(dados), TipoArquivo.PDF)
    assert recebido.caminho.read_bytes() == dados


@pytest.mark.parametrize(
    ("dados", "nome", "limite", "motivo"),
    [
        (b"", "autos.pdf", 10_000, MotivoRecusa.VAZIO),
        (pdf_minimo(), "autos.pdf", 100, MotivoRecusa.TAMANHO),
    ],
    ids=["vazio", "grande"],
)
async def test_recusas_apagam_o_temporario(
    tmp_path: Path, dados: bytes, nome: str, limite: int, motivo: MotivoRecusa
) -> None:
    """Toda recusa tem motivo e não deixa arquivo para trás."""
    with pytest.raises(RecepcaoRecusadaError) as erro:
        await receber(_blocos(dados), nome, limite, tmp_path)
    assert erro.value.motivo is motivo
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("dados", [b"MZ\x90\x00sintetico", zip_por_peca(1)])
async def test_tipo_invalido_preserva_bytes_para_quarentena(tmp_path: Path, dados: bytes) -> None:
    """RF-ING-02: o worker recebe os bytes que originaram o tipo inválido."""
    recebido = await receber(_blocos(dados), "autos.pdf", 10_000_000, tmp_path)
    assert recebido.tipo.value == "application/octet-stream"
    assert recebido.caminho.read_bytes() == dados


@pytest.mark.integracao
async def test_mesmo_arquivo_duas_vezes_nao_duplica(engine_teste: Engine, tmp_path: Path) -> None:
    """RF-ING-01 e RF-SEG-01: o segundo lacre não altera o original cifrado no MinIO."""
    processo = semear_processo(engine_teste)
    dados = pdf_minimo()
    recebido = await receber(_blocos(dados), "autos.pdf", 10_000_000, tmp_path)
    chave = chave_objeto(processo.hk_processo, recebido.sha256)
    storage = criar_storage(get_settings().model_copy(update={"storage_backend": "s3"}))
    assert isinstance(storage, StorageCifrado)
    try:
        primeiro = lacrar_bytes(engine_teste, storage, processo, recebido.caminho)
        objeto = storage.interno.ler(chave)
        assert objeto.startswith(b"LUPAOBJ")
        assert storage.ler(chave) == dados
        segundo = lacrar_bytes(engine_teste, storage, processo, recebido.caminho, "copia.pdf")
        assert (primeiro.duplicado, segundo.duplicado) == (False, True)
        assert primeiro.hk_arquivo == segundo.hk_arquivo
        assert storage.interno.ler(chave) == objeto
    finally:
        storage.apagar(chave)
    with Session(engine_teste) as sessao:
        arquivo = repositorio.ler_arquivo(sessao, primeiro.hk_arquivo)
        assert (arquivo.nome_original, arquivo.sha256, arquivo.estado) == (
            "autos.pdf",
            hashlib.sha256(dados).hexdigest(),
            "recebido",
        )
        assert (
            sessao.scalar(
                select(func.count()).where(sat_arquivo_ingestao.c.hk_arquivo == primeiro.hk_arquivo)
            )
            == 1
        )


@pytest.mark.integracao
def test_corrida_no_lacre_devolve_o_arquivo_do_concorrente(
    engine_teste: Engine, tmp_path: Path
) -> None:
    """RF-ING-01: dois envios simultâneos têm um só vencedor e devolvem a mesma chave."""
    processo = semear_processo(engine_teste)
    caminho = tmp_path / "autos.pdf"
    caminho.write_bytes(pdf_minimo())
    storage = StorageCifrado(ArmazenamentoMemoria())
    inicio = Barrier(2)

    def enviar() -> ResultadoLacre:
        with contexto_cifra():
            inicio.wait(timeout=15)
            return lacrar_bytes(engine_teste, storage, processo, caminho)

    with ThreadPoolExecutor(max_workers=2) as grupo:
        envios = [grupo.submit(enviar) for _ in range(2)]
        resultados = [envio.result() for envio in envios]
    assert sorted(r.duplicado for r in resultados) == [False, True]
    assert len({r.hk_arquivo for r in resultados}) == 1


@pytest.mark.integracao
async def test_rollback_sobrescreve_objeto_orfao_no_proximo_envio(
    engine_teste: Engine,
    tmp_path: Path,
) -> None:
    """RF-ING-01, A3.8: falha entre objeto e commit permite repetir com o original íntegro."""
    processo = semear_processo(engine_teste)
    dados = pdf_minimo()
    recebido = await receber(_blocos(dados), "autos.pdf", 10_000_000, tmp_path)
    storage = StorageCifrado(ArmazenamentoMemoria())
    chave = chave_objeto(processo.hk_processo, recebido.sha256)
    with Session(engine_teste) as sessao:
        lacrar(
            sessao,
            storage,
            recebido,
            hk_processo=processo.hk_processo,
            enviado_por=processo.hk_usuario,
            nome_original="autos.pdf",
        )
        sessao.rollback()
    primeiro = storage.interno.ler(chave)
    with Session(engine_teste) as sessao:
        assert (
            sessao.scalar(
                select(VisaoArquivo.id).where(VisaoArquivo.hk_processo == processo.hk_processo)
            )
            is None
        )
    resultado = lacrar_bytes(engine_teste, storage, processo, recebido.caminho)
    assert not resultado.duplicado
    assert storage.interno.ler(chave) != primeiro
    assert storage.ler(chave) == dados


@pytest.mark.integracao
def test_estado_muda_sem_dek_e_sem_duplicar_a_linha_corrente(
    engine_teste: Engine, tmp_path: Path
) -> None:
    """RF-ING-06, RF-ING-07: o worker conta tentativas sem precisar abrir o nome original."""
    processo = semear_processo(engine_teste)
    caminho = tmp_path / "autos.pdf"
    caminho.write_bytes(pdf_minimo())
    resultado = lacrar_bytes(
        engine_teste, StorageCifrado(ArmazenamentoMemoria()), processo, caminho
    )
    hk = resultado.hk_arquivo
    with contexto_cifra(), Session(engine_teste) as sessao, sessao.begin():
        for _ in range(2):
            arquivo = repositorio.mudar_estado(sessao, hk, EstadoJob.RECEBIDO, tentativas=1)
            assert (arquivo.estado, arquivo.tentativas) == ("recebido", 1)
        assert (
            sessao.scalar(select(func.count()).where(sat_arquivo_ingestao.c.hk_arquivo == hk)) == 2
        )
        with pytest.raises(TransicaoInvalidaError):
            repositorio.mudar_estado(sessao, hk, EstadoJob.CONCLUIDO)
        arquivo = repositorio.mudar_estado(sessao, hk, EstadoJob.VALIDADO, total_paginas=3)
        assert (arquivo.total_paginas, arquivo.tentativas) == (3, 1)
