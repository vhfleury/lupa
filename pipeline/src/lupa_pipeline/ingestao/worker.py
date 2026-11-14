"""Laço do worker de ingestão sobre a fila do PostgreSQL (A4; RES-07)."""

import argparse
import signal
from collections.abc import Callable, Sequence
from threading import Event

from sqlalchemy import Connection, Engine, create_engine, event, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from lupa_pipeline.config import Settings, get_settings
from lupa_pipeline.dominio.enums import EstadoJob, MotivoFalha, StatusProcesso
from lupa_pipeline.dominio.gravacao import travar_processo
from lupa_pipeline.dominio.sessao import PAPEL_APLICACAO
from lupa_pipeline.dominio.visoes import VisaoFilaIngestao
from lupa_pipeline.ingestao.repositorio import atualizar_status_processo, mudar_estado
from lupa_pipeline.ingestao.reprocessamento import reagendar_desatualizados
from lupa_pipeline.ingestao.storage import ObjectStorage, criar_storage
from lupa_pipeline.logging import configurar_logging, get_logger
from lupa_pipeline.seguranca.contexto import ativar_processo, contexto_cifra

TRAVA_WORKER = 0x4C55504146494C41
Processador = Callable[[sessionmaker[Session], Settings, ObjectStorage, bytes, Event], None]
log = get_logger(__name__)


class ConexaoDoWorkerPerdidaError(RuntimeError):
    """A conexão que mantinha a posse da fila foi perdida."""


def _processar_proximo(
    fabrica: sessionmaker[Session],
    settings: Settings,
    storage: ObjectStorage,
    parar: Event,
    processar: Processador,
) -> bool:
    with fabrica.begin() as sessao:
        consulta = (
            select(VisaoFilaIngestao)
            .order_by(VisaoFilaIngestao.criado_em, VisaoFilaIngestao.hk_arquivo)
            .limit(1)
        )
        arquivo = sessao.scalar(consulta)
        if arquivo is None:
            return False
        hk, hk_processo = arquivo.hk_arquivo, arquivo.hk_processo
        processo = travar_processo(sessao, hk_processo)
        if processo is None or processo.status == StatusProcesso.DESCARTADO:
            return True
        if arquivo.tentativas >= settings.max_tentativas:
            mudar_estado(sessao, hk, EstadoJob.FALHO, motivo_falha=MotivoFalha.ERRO_INTERNO)
            atualizar_status_processo(sessao, hk_processo)
            log.warning("tentativas_esgotadas", arquivo_id=hk.hex())
            return True
        mudar_estado(sessao, hk, EstadoJob(arquivo.estado), tentativas=arquivo.tentativas + 1)
        chave_cifrada = processo.chave_dados_cifrada
    try:
        with contexto_cifra():
            ativar_processo(hk_processo, chave_cifrada)
            processar(fabrica, settings, storage, hk, parar)
    except ConexaoDoWorkerPerdidaError:
        raise
    except Exception as erro:
        log.error("arquivo_falhou", arquivo_id=hk.hex(), erro=type(erro).__name__)
    return True


def executar_worker(
    engine: Engine, settings: Settings, storage: ObjectStorage, parar: Event, processar: Processador
) -> int:
    """Consome a fila em ordem sob um advisory lock de sessão do PostgreSQL.

    As transações de A5 usam a própria conexão do lock. Ao sair, a conexão física
    fecha e o PostgreSQL libera o lock, inclusive na interrupção do processo.

    Args:
        engine: Banco de dados da aplicação.
        settings: Intervalo de consulta, tentativas e configuração do processamento.
        storage: Armazenamento cifrado.
        parar: Sinal do processo, observado também pelos lotes de A5.
        processar: Processador de um arquivo, com sua DEK ativa.

    Returns:
        Zero no encerramento normal ou um se já existe outro worker.
    """
    with engine.connect() as conexao:
        conexao.detach()
        with conexao.begin():
            if not conexao.scalar(select(func.pg_try_advisory_lock(TRAVA_WORKER))):
                log.warning("worker_duplicado")
                return 1
            conexao.execute(text(f"SET ROLE {PAPEL_APLICACAO}"))
        fisica = conexao.connection.driver_connection

        @event.listens_for(conexao, "begin")
        def _exigir_mesma_conexao(atual: Connection) -> None:
            if atual.invalidated or atual.connection.driver_connection is not fisica:
                raise ConexaoDoWorkerPerdidaError("conexão da fila encerrada")

        fabrica = sessionmaker(conexao, expire_on_commit=False)
        reagendar_desatualizados(fabrica)
        log.info("worker_iniciado")
        while not parar.is_set():
            if not _processar_proximo(fabrica, settings, storage, parar, processar):
                parar.wait(settings.fila_intervalo_s)
    return 0


def main(argumentos: Sequence[str] | None = None) -> int:
    """Inicia o worker ou consulta o PostgreSQL para o healthcheck do contêiner."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saude", action="store_true")
    settings = get_settings()
    if parser.parse_args(argumentos).saude:
        engine = create_engine(settings.database_url.get_secret_value())
        try:
            with engine.connect() as conexao:
                conexao.execute(text("SELECT 1"))
            return 0
        except SQLAlchemyError:
            return 1
        finally:
            engine.dispose()

    from lupa_pipeline.ingestao.processamento import processar_arquivo

    configurar_logging(nivel=settings.log_level)
    engine = create_engine(settings.url_banco_aplicacao())
    storage = criar_storage(settings)
    parar = Event()
    anterior = signal.signal(signal.SIGTERM, lambda *_: parar.set())
    try:
        while not parar.is_set():
            try:
                return executar_worker(engine, settings, storage, parar, processar_arquivo)
            except (SQLAlchemyError, ConexaoDoWorkerPerdidaError) as erro:
                log.warning("fila_indisponivel", erro=type(erro).__name__)
                parar.wait(settings.fila_intervalo_s)
        return 0
    finally:
        signal.signal(signal.SIGTERM, anterior)
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
