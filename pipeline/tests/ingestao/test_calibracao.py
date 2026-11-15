"""Execução local e relatório de calibração (4F.10) sobre um processo sintético."""

import importlib.util
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from time import monotonic, sleep

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import sessionmaker

from apoio_ingestao import AutosSinteticos
from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.cnj import validar_numero_cnj
from lupa_pipeline.dominio.enums import ClasseProcessual, EstadoJob, MotivoFalha
from lupa_pipeline.dominio.gravacao import chave_do_hub
from lupa_pipeline.dominio.tabelas import hub_processo
from lupa_pipeline.dominio.visoes import VisaoFilaIngestao
from lupa_pipeline.ingestao.calibracao import (
    coletar,
    enviar_e_processar,
    numero_cnj,
    para_markdown,
    semear_assessor,
)
from lupa_pipeline.ingestao.repositorio import mudar_estado
from lupa_pipeline.ingestao.storage import ObjectStorage
from lupa_pipeline.ingestao.worker import TRAVA_WORKER
from lupa_pipeline.sinteticos.gabarito import Cenario, Composicao
from lupa_pipeline.sinteticos.referencia import gerar_processo
from lupa_pipeline.sinteticos.roteiro import Configuracao

pytestmark = pytest.mark.integracao


def test_numero_cnj_sintetico_e_valido() -> None:
    """O número gerado passa na validação do domínio."""
    for sequencial in (1, 42, 10**12 + 7):
        assert validar_numero_cnj(numero_cnj(sequencial)) == numero_cnj(sequencial)


def test_calibracao_de_processo_sintetico_gera_relatorio_para_conferencia(
    engine_teste: Engine,
    settings_ficticias: Settings,
    storage_memoria: ObjectStorage,
    autos_sinteticos: AutosSinteticos,
) -> None:
    """Pipeline até achados e relatório com diagnóstico, peças, eventos com trecho e achados."""
    dono = sessionmaker(engine_teste)
    with dono.begin() as session:
        usuario = semear_assessor(session, "scripts.calibrar")
    caminho = autos_sinteticos.arquivos[Cenario.PDF_INDICE]
    gabarito = autos_sinteticos.gabaritos[Cenario.PDF_INDICE]
    execucao = enviar_e_processar(
        dono,
        settings_ficticias,
        storage_memoria,
        usuario,
        caminho,
        gabarito.processo.classe,
        "scripts.calibrar",
    )
    assert execucao.estado is EstadoJob.CONCLUIDO
    with dono() as session:
        dados = coletar(session, execucao.processo_id, execucao.arquivo_id)
    assert dados["diagnostico"]["cenario"] == "pdf_com_bookmarks_e_indice"
    assert {p["nome"] for p in dados["partes"]} == {p.nome for p in gabarito.partes}
    assert dados["fatos"] and all(f["trecho"] for f in dados["fatos"])
    assert [(a["validacao"], a["resultado"]) for a in dados["achados"]] == sorted(
        (a.validacao, a.resultado.value) for a in gabarito.resultado_esperado
    )
    texto = para_markdown(dados, "sintético")
    for secao in ("## 1. Diagnóstico", "## 2. Peças", "## 3. Eventos", "## 4. Achados"):
        assert secao in texto
    assert texto.count("| |") >= len(dados["indice"]) + len(dados["fatos"])


def test_semear_assessor_e_arquivo_que_nao_e_pdf_nem_zip(
    engine_teste: Engine,
    settings_ficticias: Settings,
    storage_memoria: ObjectStorage,
    tmp_path: Path,
) -> None:
    """Assessor local criado; arquivo de outro tipo é recusado antes de lacrar."""
    dono = sessionmaker(engine_teste)
    with dono() as session, session.begin():
        usuario = semear_assessor(session, "scripts.calibrar")
    texto = tmp_path / "nota.txt"
    texto.write_text("não é PDF", encoding="utf-8")
    with pytest.raises(ValueError, match="PDF nem ZIP"):
        enviar_e_processar(
            dono,
            settings_ficticias,
            storage_memoria,
            usuario,
            texto,
            ClasseProcessual.APELACAO_CIVEL,
            "scripts.calibrar",
        )


def test_calibracao_aguarda_o_worker_que_ja_possui_a_fila(
    engine_teste: Engine,
    settings_ficticias: Settings,
    storage_memoria: ObjectStorage,
    tmp_path: Path,
) -> None:
    """Com worker presente o script observa o desfecho e evita processar o mesmo PDF em paralelo."""
    fabrica = sessionmaker(engine_teste)
    origem = "scripts.calibrar"
    with fabrica.begin() as session:
        usuario = semear_assessor(session, origem)
    caminho = tmp_path / "autos.pdf"
    caminho.write_bytes(b"%PDF-sintetico")
    settings = settings_ficticias.model_copy(update={"fila_intervalo_s": 0.01})
    pronto = Event()
    numero = numero_cnj(333)
    processo = chave_do_hub(hub_processo, {"numero_cnj": numero})

    def worker() -> None:
        with fabrica.begin() as possuidor:
            possuidor.execute(select(func.pg_advisory_xact_lock(TRAVA_WORKER)))
            pronto.set()
            limite = monotonic() + 4
            while monotonic() < limite:
                with fabrica.begin() as sessao:
                    hk = sessao.scalar(
                        select(VisaoFilaIngestao.hk_arquivo).where(
                            VisaoFilaIngestao.hk_processo == processo
                        )
                    )
                    if hk is not None:
                        sleep(0.2)
                        mudar_estado(
                            sessao, hk, EstadoJob.FALHO, motivo_falha=MotivoFalha.ERRO_INTERNO
                        )
                        return
                sleep(0.01)
            pytest.fail("o worker não observou o arquivo na fila")

    with ThreadPoolExecutor(max_workers=1) as executor:
        futuro = executor.submit(worker)
        assert pronto.wait(2)
        execucao = enviar_e_processar(
            fabrica,
            settings,
            storage_memoria,
            usuario,
            caminho,
            ClasseProcessual.APELACAO_CIVEL,
            origem,
            numero=numero,
        )
        futuro.result()
    assert execucao.estado is EstadoJob.FALHO


@pytest.mark.parametrize("cenario", list(Cenario))
def test_medicao_ponta_a_ponta_confronta_dados_do_banco_com_o_gabarito(
    engine_teste: Engine,
    settings_ficticias: Settings,
    storage_memoria: ObjectStorage,
    tmp_path: Path,
    cenario: Cenario,
) -> None:
    """O relatório confere valores, fontes e cadeia de representação de cada parte."""
    caminho = Path(__file__).resolve().parents[2] / "scripts" / "ponta_a_ponta.py"
    spec = importlib.util.spec_from_file_location("ponta_a_ponta", caminho)
    assert spec is not None and spec.loader is not None
    roteiro = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(roteiro)
    nome = "referencia"
    gerar_processo(
        nome,
        Configuracao(
            semente=88, paginas_alvo=20, mistura={Composicao.NATIVA: 1.0}, proporcao_vazias=0
        ),
        tmp_path,
        (cenario,),
    )
    fabrica = sessionmaker(engine_teste)
    with fabrica.begin() as sessao:
        usuario = semear_assessor(sessao, "scripts.ponta_a_ponta")
    linha = roteiro._rodar(
        fabrica,
        settings_ficticias,
        storage_memoria,
        usuario,
        tmp_path / nome / cenario.value,
        cenario,
    )
    assert linha["estado"] == "concluido" and linha["evidencias_nao_literais"] == 0
    assert linha["fronteira"]["recall"] == 1.0 and linha["eventos"]["recall"] == 1.0, linha
    assert linha["achados_iguais"] == len(linha["achados"]) == 3, linha["achados"]
