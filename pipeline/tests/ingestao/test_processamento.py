"""Integração de A5 com PostgreSQL, cifra e parsers isolados."""

import zipfile
from pathlib import Path
from threading import Event
from typing import Any

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from apoio_arquivos import pdf_com_senha, pdf_minimo, pdf_texto, zip_por_peca
from apoio_ingestao import SemearArquivo
from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.tabelas import sat_arquivo_lote, sat_pagina_extracao
from lupa_pipeline.dominio.visoes import VisaoArquivo, VisaoPagina, VisaoPeca, VisaoProcesso
from lupa_pipeline.ingestao import processamento
from lupa_pipeline.ingestao.cache import copiar_do_cache
from lupa_pipeline.ingestao.extracao import ResultadoTarefa, Tarefa, executar_tarefa
from lupa_pipeline.ingestao.inventario import EntradaExtraida
from lupa_pipeline.ingestao.processamento import processar_arquivo
from lupa_pipeline.ingestao.sandbox import LimitesSandbox
from lupa_pipeline.ingestao.storage import StorageCifrado
from lupa_pipeline.seguranca.contexto import ativar_processo, contexto_cifra

pytestmark = pytest.mark.integracao


def test_pdf_com_senha_vai_a_quarentena_sem_paginas(
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
    semear_arquivo: SemearArquivo,
    storage_memoria: StorageCifrado,
) -> None:
    """RF-ING-02: um PDF protegido termina em quarentena com o motivo senha."""
    hk = semear_arquivo(pdf_com_senha()).hk_arquivo
    processar_arquivo(fabrica_sessao, settings_ficticias, storage_memoria, hk, Event())
    with fabrica_sessao() as sessao:
        arquivo = sessao.get_one(VisaoArquivo, hk)
        assert (arquivo.estado, arquivo.motivo_quarentena) == ("quarentena", "senha")
        assert sessao.scalar(select(VisaoPagina.id).where(VisaoPagina.hk_arquivo == hk)) is None


@pytest.mark.parametrize(
    ("dados", "nome"),
    [(pdf_minimo(2), "peca.pdf"), (zip_por_peca(2), "autos.zip")],
    ids=["pdf", "zip"],
)
def test_extrai_paginas_pecas_e_diagnostico(
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
    semear_arquivo: SemearArquivo,
    storage_memoria: StorageCifrado,
    dados: bytes,
    nome: str,
) -> None:
    """RF-ING-03, RF-ING-06: PDF e ZIP publicam páginas, peças, lotes e diagnóstico."""
    hk = semear_arquivo(dados, nome).hk_arquivo
    processar_arquivo(fabrica_sessao, settings_ficticias, storage_memoria, hk, Event())
    with fabrica_sessao() as sessao:
        arquivo = sessao.get_one(VisaoArquivo, hk)
        assert arquivo.estado == "concluido"
        assert arquivo.total_paginas_diagnostico == 2
        bruto = sessao.scalars(
            text(
                "SELECT fronteira.sinais_fronteira::text FROM sat_pagina_fronteira fronteira "
                "JOIN link_arquivo_pagina USING (hk_pagina) WHERE hk_arquivo = :arquivo"
            ),
            {"arquivo": hk},
        )
        assert all("sentinela" not in linha.lower() for linha in bruto)
        assert arquivo.relatorio["paginas_faltando_lista"] == []
        paginas = list(
            sessao.scalars(
                select(VisaoPagina).where(VisaoPagina.hk_arquivo == hk).order_by(VisaoPagina.numero)
            )
        )
        assert [p.numero for p in paginas] == [1, 2]
        assert all(p.texto and p.coordenadas and p.sinais_fronteira for p in paginas)
        assert sessao.scalar(
            select(VisaoPeca.id).where(VisaoPeca.hk_arquivo == hk, VisaoPeca.vigente.is_(True))
        )
        lotes = sessao.scalars(
            select(sat_arquivo_lote.c.estado).where(sat_arquivo_lote.c.hk_arquivo == hk)
        )
        assert set(lotes) == {"concluido"}


def test_interrupcao_retoma_sem_reextrair_pagina_gravada(
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
    semear_arquivo: SemearArquivo,
    storage_memoria: StorageCifrado,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RF-ING-07: ao parar após o primeiro lote, a segunda execução só extrai o segundo."""
    hk = semear_arquivo(pdf_texto(["retomada um", "retomada dois"])).hk_arquivo
    settings = settings_ficticias.model_copy(update={"extracao_paginas_por_lote": 1})
    parada = Event()
    chamadas: list[int] = []
    original = executar_tarefa

    def executar(tarefa: Tarefa, limites: LimitesSandbox) -> ResultadoTarefa:
        chamadas.append(tarefa.inicio)
        if len(chamadas) == 1:
            parada.set()
        return original(tarefa, limites)

    monkeypatch.setattr(processamento, "executar_tarefa", executar)
    processar_arquivo(fabrica_sessao, settings, storage_memoria, hk, parada)
    with fabrica_sessao() as sessao:
        assert sessao.get_one(VisaoArquivo, hk).estado == "em_extracao"
    processar_arquivo(fabrica_sessao, settings, storage_memoria, hk, Event())
    assert chamadas == [1, 2]
    with fabrica_sessao() as sessao:
        assert sessao.get_one(VisaoArquivo, hk).estado == "concluido"
        paginas = select(VisaoPagina.hk_pagina).where(VisaoPagina.hk_arquivo == hk)
        assert (
            sessao.scalar(
                select(func.count())
                .select_from(sat_pagina_extracao)
                .where(sat_pagina_extracao.c.hk_pagina.in_(paginas))
            )
            == 2
        )


def test_cache_recifra_para_a_chave_do_destino_e_exige_a_mesma_versao(
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
    semear_arquivo: SemearArquivo,
    storage_memoria: StorageCifrado,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RF-ING-08 e RF-SEG-01. Um segundo envio idêntico lê páginas sob a sua própria DEK."""
    conteudo = pdf_texto(["SENTINELA-CACHE-0.2"])
    fonte = semear_arquivo(conteudo)
    processar_arquivo(
        fabrica_sessao, settings_ficticias, storage_memoria, fonte.hk_arquivo, Event()
    )
    destino = semear_arquivo(conteudo)
    with fabrica_sessao.begin() as s:
        assert not copiar_do_cache(
            s, s.get_one(VisaoArquivo, destino.hk_arquivo), "obsoleta", 1, {1}
        )

    def sem_parser(tarefa: Tarefa, limites: LimitesSandbox) -> ResultadoTarefa:
        pytest.fail("o original idêntico e completo já foi extraído nesta versão")

    monkeypatch.setattr(processamento, "executar_tarefa", sem_parser)
    processar_arquivo(
        fabrica_sessao, settings_ficticias, storage_memoria, destino.hk_arquivo, Event()
    )
    with contexto_cifra(), fabrica_sessao() as s:
        hk = destino.processo.hk_processo
        ativar_processo(hk, s.get_one(VisaoProcesso, hk).chave_dados_cifrada)
        p = s.scalars(select(VisaoPagina).where(VisaoPagina.hk_arquivo == destino.hk_arquivo)).one()
        assert p.texto and "SENTINELA-CACHE" in p.texto
        assert s.get_one(VisaoArquivo, destino.hk_arquivo).estado == "concluido"
        consulta = text(
            "SELECT e.texto FROM sat_pagina_extracao e JOIN link_arquivo_pagina l "
            "USING (hk_pagina) WHERE l.hk_arquivo=:hk"
        )
        brutos = [s.execute(consulta, {"hk": a.hk_arquivo}).scalar_one() for a in (fonte, destino)]
        assert brutos[0] != brutos[1]
        assert all("SENTINELA" not in str(b) for b in brutos)


def test_abertura_de_zip_so_no_filho_e_membros_temporarios_opacos(
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
    semear_arquivo: SemearArquivo,
    storage_memoria: StorageCifrado,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A5 confere o ZIP num filho e expõe ao worker somente arquivos opacos com modo 0600."""
    hk = semear_arquivo(zip_por_peca(2), "autos.zip").hk_arquivo
    inspecionar = processamento._inspecionar
    vistos: list[Path] = []

    def proibido(*args: object, **kwargs: object) -> None:
        pytest.fail("o processo worker abriu o ZIP")

    def inspecao(entradas: list[EntradaExtraida], limites: LimitesSandbox) -> list[dict[str, Any]]:
        for indice, entrada in enumerate(entradas, start=1):
            assert entrada.caminho.name == f"entrada-{indice:05d}"
            assert entrada.caminho.parent.parent == tmp_path
            assert entrada.caminho.stat().st_mode & 0o777 == 0o600
            assert entrada.caminho.stat().st_size == entrada.manifesto.tamanho_bytes
            vistos.append(entrada.caminho)
        return inspecionar(entradas, limites)

    monkeypatch.setattr(zipfile, "ZipFile", proibido)
    monkeypatch.setattr(processamento, "_inspecionar", inspecao)
    settings = settings_ficticias.model_copy(update={"ingestao_dir_temporario": tmp_path})
    processar_arquivo(fabrica_sessao, settings, storage_memoria, hk, Event())
    assert len(vistos) == 2 and all(not p.exists() for p in vistos)
    with fabrica_sessao() as sessao:
        assert sessao.get_one(VisaoArquivo, hk).estado == "concluido"
