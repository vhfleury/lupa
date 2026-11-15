"""Laço do worker e exclusão entre conexões PostgreSQL (A4)."""

from collections.abc import Iterator
from pathlib import Path
from threading import Event

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from apoio_arquivos import TEXTO_SENTINELA, pdf_minimo
from apoio_comum import banco_vazio, migrar
from apoio_ingestao import PararAoEsvaziar, lacrar_bytes, semear_processo
from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.enums import EstadoJob, MotivoFalha
from lupa_pipeline.dominio.visoes import VisaoArquivo
from lupa_pipeline.ingestao.repositorio import mudar_estado
from lupa_pipeline.ingestao.storage import ObjectStorage
from lupa_pipeline.ingestao.worker import executar_worker

pytestmark = pytest.mark.integracao


@pytest.fixture
def banco_fila() -> Iterator[Engine]:
    """A fila vê todos os arquivos; cada cenário usa um banco próprio."""
    with banco_vazio("fila") as engine:
        migrar(engine, "head")
        yield engine


def _receber(engine: Engine, storage: ObjectStorage, tmp_path: Path) -> tuple[bytes, bytes]:
    processo = semear_processo(engine)
    caminho = tmp_path / "autos.pdf"
    caminho.write_bytes(pdf_minimo())
    recebido = lacrar_bytes(engine, storage, processo, caminho)
    return recebido.hk_arquivo, processo.hk_processo


def test_processa_em_ordem_e_segundo_worker_encerra_entre_commits(
    banco_fila: Engine,
    settings_ficticias: Settings,
    storage_memoria: ObjectStorage,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """RES-07: uma conexão mantém o lock durante A5, entre commits e até o fim do laço."""
    arquivos = [_receber(banco_fila, storage_memoria, tmp_path) for _ in range(2)]
    chamados: list[bytes] = []
    concorrentes: list[int] = []
    contagens: list[int | None] = []
    papeis: list[str | None] = []
    parar = PararAoEsvaziar()

    def processar(
        fabrica: sessionmaker[Session],
        settings: Settings,
        storage: ObjectStorage,
        hk: bytes,
        sinal: Event,
    ) -> None:
        chamados.append(hk)
        consulta = select(VisaoArquivo.tentativas).where(VisaoArquivo.hk_arquivo == hk)
        with Session(banco_fila) as observador:
            contagens.append(observador.scalar(consulta))
        with fabrica.begin() as sessao:
            papeis.append(sessao.scalar(text("SELECT current_user")))
            mudar_estado(sessao, hk, EstadoJob.VALIDADO)
        concorrentes.append(
            executar_worker(banco_fila, settings, storage, PararAoEsvaziar(), negar)
        )
        with fabrica.begin() as sessao:
            mudar_estado(sessao, hk, EstadoJob.EM_EXTRACAO)
            mudar_estado(sessao, hk, EstadoJob.CONCLUIDO)

    def negar(
        fabrica: sessionmaker[Session],
        settings: Settings,
        storage: ObjectStorage,
        hk: bytes,
        sinal: Event,
    ) -> None:
        pytest.fail("o segundo worker entrou no processador")

    assert executar_worker(banco_fila, settings_ficticias, storage_memoria, parar, processar) == 0
    assert chamados == [hk_arquivo for hk_arquivo, _ in arquivos]
    assert concorrentes == [1, 1]
    assert contagens == [1, 1]
    assert papeis == ["lupa_app", "lupa_app"]
    assert parar.esperas == [2]
    assert "worker_duplicado" in capsys.readouterr().out
    sucessor = PararAoEsvaziar()
    assert executar_worker(banco_fila, settings_ficticias, storage_memoria, sucessor, negar) == 0
    assert sucessor.esperas == [2]


def test_erro_no_processamento_reentra_ate_o_teto_sem_expor_conteudo(
    banco_fila: Engine,
    settings_ficticias: Settings,
    storage_memoria: ObjectStorage,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """RF-ING-07, RF-AUD-02: retoma validado com tentativa persistida e registra só metadados."""
    hk, _ = _receber(banco_fila, storage_memoria, tmp_path)
    tentativas: list[tuple[str | None, int | None]] = []
    settings = settings_ficticias.model_copy(update={"max_tentativas": 2})

    def falhar(
        fabrica: sessionmaker[Session],
        settings: Settings,
        storage: ObjectStorage,
        arquivo: bytes,
        sinal: Event,
    ) -> None:
        with fabrica.begin() as sessao:
            consulta = select(VisaoArquivo.estado, VisaoArquivo.tentativas).where(
                VisaoArquivo.hk_arquivo == arquivo
            )
            estado, tentativa = sessao.execute(consulta).one()
            tentativas.append((estado, tentativa))
            mudar_estado(sessao, arquivo, EstadoJob.VALIDADO)
        raise ValueError(TEXTO_SENTINELA)

    assert executar_worker(banco_fila, settings, storage_memoria, PararAoEsvaziar(), falhar) == 0
    assert tentativas == [("recebido", 1), ("validado", 2)]
    with Session(banco_fila) as sessao:
        consulta = select(VisaoArquivo.estado, VisaoArquivo.tentativas, VisaoArquivo.motivo_falha)
        assert sessao.execute(consulta.where(VisaoArquivo.hk_arquivo == hk)).one() == (
            "falho",
            2,
            MotivoFalha.ERRO_INTERNO.value,
        )
    saida = capsys.readouterr()
    assert TEXTO_SENTINELA not in saida.out + saida.err
    assert "arquivo_falhou" in saida.out
