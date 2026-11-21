"""Integração de A5 com PostgreSQL, cifra e parsers isolados."""

import threading
import zipfile
from pathlib import Path
from threading import Event
from typing import Any

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from apoio_arquivos import pdf_com_senha, pdf_minimo, pdf_texto, zip_por_peca
from apoio_ingestao import SemearArquivo
from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.tabelas import sat_arquivo_lote, sat_pagina_extracao
from lupa_pipeline.dominio.visoes import VisaoArquivo, VisaoPagina, VisaoPeca
from lupa_pipeline.ingestao import paginas, processamento
from lupa_pipeline.ingestao.cache import copiar_do_cache
from lupa_pipeline.ingestao.diagnostico import NomeInternoAusenteError
from lupa_pipeline.ingestao.extracao import ResultadoTarefa, Tarefa, executar_tarefa
from lupa_pipeline.ingestao.inventario import EntradaExtraida
from lupa_pipeline.ingestao.parser_pdf import inspecionar as inspecionar_pdf
from lupa_pipeline.ingestao.processamento import processar_arquivo
from lupa_pipeline.ingestao.recepcao import TipoArquivo
from lupa_pipeline.ingestao.sandbox import LimitesSandbox
from lupa_pipeline.ingestao.storage import ObjectStorage

pytestmark = pytest.mark.integracao


def test_pdf_com_senha_vai_a_quarentena_sem_paginas(
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
    semear_arquivo: SemearArquivo,
    storage_memoria: ObjectStorage,
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
    storage_memoria: ObjectStorage,
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
    storage_memoria: ObjectStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RF-ING-07: ao parar após o primeiro lote, a segunda execução só extrai o segundo."""
    hk = semear_arquivo(pdf_texto(["retomada um", "retomada dois"])).hk_arquivo
    settings = settings_ficticias.model_copy(
        update={"extracao_paginas_por_lote": 1, "extracao_lotes_por_job": 1}
    )
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


def test_cache_copia_as_paginas_para_o_destino_e_exige_a_mesma_versao(
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
    semear_arquivo: SemearArquivo,
    storage_memoria: ObjectStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RF-ING-08. Um segundo envio idêntico recebe as páginas do cache, sem reextrair."""
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
    with fabrica_sessao() as s:
        p = s.scalars(select(VisaoPagina).where(VisaoPagina.hk_arquivo == destino.hk_arquivo)).one()
        assert p.texto and "SENTINELA-CACHE" in p.texto
        assert s.get_one(VisaoArquivo, destino.hk_arquivo).estado == "concluido"
        consulta = text(
            "SELECT e.texto FROM sat_pagina_extracao e JOIN link_arquivo_pagina l "
            "USING (hk_pagina) WHERE l.hk_arquivo=:hk"
        )
        brutos = [s.execute(consulta, {"hk": a.hk_arquivo}).scalar_one() for a in (fonte, destino)]
        assert brutos[0] == brutos[1]
        assert all("SENTINELA-CACHE" in str(b) for b in brutos)


def test_abertura_de_zip_so_no_filho_e_membros_temporarios_opacos(
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
    semear_arquivo: SemearArquivo,
    storage_memoria: ObjectStorage,
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


@pytest.mark.parametrize(
    ("primeira", "esperadas"),
    [
        ("paginas", ("paginas", "pecas", "fatos", "catalogo")),
        ("pecas", ("pecas", "fatos", "catalogo")),
        ("fatos", ("fatos", "catalogo")),
        ("catalogo", ("catalogo",)),
    ],
)
def test_etapas_executam_a_partir_da_primeira_agendada(
    primeira: str, esperadas: tuple[str, ...]
) -> None:
    """RF-ING-08: a execução segue a ordem de `ETAPAS` a partir da primeira etapa agendada."""
    assert tuple(nome for nome, _ in processamento.ETAPAS) == (
        "paginas",
        "pecas",
        "fatos",
        "catalogo",
    )
    assert tuple(nome for nome, _ in processamento.etapas_desde(primeira)) == esperadas


def test_diagnostico_de_zip_ja_sai_com_os_nomes_internos() -> None:
    """RF-ING-07: o formato ZIP diagnostica com os nomes internos, sem remapeamento posterior."""
    nomes_originais = ["02-peca.pdf", "01-peca.pdf"]
    entradas = [(nome, inspecionar_pdf(pdf_texto([nome]))) for nome in nomes_originais]
    nomes = {nome: f"entrada-{ordem}.pdf" for ordem, nome in enumerate(nomes_originais, 1)}
    formato = processamento.FORMATOS[TipoArquivo.ZIP.value]
    diagnostico = formato.diagnosticar("0" * 64, entradas, nomes)
    fronteiras = diagnostico.fronteiras_origem
    assert [f["arquivo"] for f in fronteiras] == ["entrada-1.pdf", "entrada-2.pdf"]
    assert all("titulo" not in f for f in fronteiras)
    assert [f["pagina_continua"] for f in fronteiras] == [1, 2]


def test_nome_sem_entrada_interna_e_erro_de_integridade() -> None:
    """RF-ING-07: nome de entrada fora do mapa de nomes internos é erro, sem padrão fixo."""
    entradas = [("autos.pdf", inspecionar_pdf(pdf_texto(["DENÚNCIA"])))]
    formato = processamento.FORMATOS[TipoArquivo.PDF.value]
    with pytest.raises(NomeInternoAusenteError):
        formato.diagnosticar("0" * 64, entradas, {})


class FalhaDeGravacaoError(Exception):
    """Falha simulada na gravação de uma página."""


def _registrar_gravacoes(
    monkeypatch: pytest.MonkeyPatch, falhar_em: int | None = None
) -> list[tuple[int, int, int]]:
    gravacoes: list[tuple[int, int, int]] = []
    original = paginas.gravar_paginas

    def gravar(
        session: Session, arquivo: VisaoArquivo, linhas: list[dict[str, Any]]
    ) -> list[bytes]:
        numeros = [int(linha["numero"]) for linha in linhas]
        ja_falhou = any(gravada == falhar_em for gravada, _, _ in gravacoes)
        if falhar_em in numeros and not ja_falhou:
            gravacoes.append((falhar_em, threading.get_ident(), 0))
            raise FalhaDeGravacaoError
        pid = int(session.scalar(select(func.pg_backend_pid())) or 0)
        gravacoes.extend((numero, threading.get_ident(), pid) for numero in numeros)
        return original(session, arquivo, linhas)

    monkeypatch.setattr(paginas, "gravar_paginas", gravar)
    return gravacoes


def _extracao_em_par(monkeypatch: pytest.MonkeyPatch, emparelhadas: set[int]) -> list[int]:
    chamadas: list[int] = []
    encontro = threading.Barrier(2, timeout=10)

    def executar(tarefa: Tarefa, limites: LimitesSandbox) -> ResultadoTarefa:
        chamadas.append(tarefa.inicio)
        if tarefa.inicio in emparelhadas:
            encontro.wait()
        return executar_tarefa(tarefa, limites)

    monkeypatch.setattr(processamento, "executar_tarefa", executar)
    return chamadas


def test_lotes_em_paralelo_gravam_na_conexao_do_lock(
    engine_teste: Engine,
    settings_ficticias: Settings,
    semear_arquivo: SemearArquivo,
    storage_memoria: ObjectStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RF-ING-04: dois filhos rodam juntos e toda página é gravada na thread e conexão do lock."""
    hk = semear_arquivo(pdf_texto([f"paralelo {n}" for n in range(4)])).hk_arquivo
    settings = settings_ficticias.model_copy(
        update={"extracao_paginas_por_lote": 1, "extracao_lotes_por_job": 2}
    )
    _extracao_em_par(monkeypatch, {1, 2, 3, 4})
    gravacoes = _registrar_gravacoes(monkeypatch)
    with engine_teste.connect() as conexao:
        pid_do_lock = conexao.scalar(select(func.pg_backend_pid()))
        conexao.commit()
        fabrica = sessionmaker(conexao, expire_on_commit=False)
        processar_arquivo(fabrica, settings, storage_memoria, hk, Event())
    assert sorted(numero for numero, _, _ in gravacoes) == [1, 2, 3, 4]
    assert {(thread, pid) for _, thread, pid in gravacoes} == {(threading.get_ident(), pid_do_lock)}
    with Session(engine_teste) as sessao:
        assert sessao.get_one(VisaoArquivo, hk).estado == "concluido"


def test_falha_de_gravacao_cancela_lotes_e_retoma_so_os_faltantes(
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
    semear_arquivo: SemearArquivo,
    storage_memoria: ObjectStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RF-ING-04, RF-ING-07: erro ao gravar um lote para a extração; a retomada faz o resto."""
    total = 6
    hk = semear_arquivo(pdf_texto([f"retomada {n}" for n in range(total)])).hk_arquivo
    settings = settings_ficticias.model_copy(
        update={"extracao_paginas_por_lote": 1, "extracao_lotes_por_job": 2}
    )
    primeira = _extracao_em_par(monkeypatch, {1, 2})
    gravacoes = _registrar_gravacoes(monkeypatch, falhar_em=2)
    with pytest.raises(FalhaDeGravacaoError):
        processar_arquivo(fabrica_sessao, settings, storage_memoria, hk, Event())
    assert len(primeira) < total
    with fabrica_sessao() as sessao:
        gravadas = set(
            sessao.scalars(select(VisaoPagina.numero).where(VisaoPagina.hk_arquivo == hk))
        )
        lotes = set(
            sessao.scalars(
                select(sat_arquivo_lote.c.numero).where(sat_arquivo_lote.c.hk_arquivo == hk)
            )
        )
    assert 2 not in gravadas
    assert lotes == gravadas
    segunda = _extracao_em_par(monkeypatch, set())
    processar_arquivo(fabrica_sessao, settings, storage_memoria, hk, Event())
    assert sorted(segunda) == sorted(set(range(1, total + 1)) - gravadas)
    assert sorted({numero for numero, _, pid in gravacoes if pid}) == list(range(1, total + 1))
    with fabrica_sessao() as sessao:
        assert sessao.get_one(VisaoArquivo, hk).estado == "concluido"
