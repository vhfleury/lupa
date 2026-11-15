"""Fixtures comuns da ingestão: processo semeado, storage em memória e arquivo lacrado.

Fase 3 (D23): as dependências do worker e a extração da sessão voltam com o worker novo
(T3.8 e T3.9).
"""

from __future__ import annotations

import hashlib
import io
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from apoio_comum import criar_processo
from lupa_pipeline.dominio.enums import ClasseProcessual
from lupa_pipeline.dominio.visoes import VisaoProcesso
from lupa_pipeline.ingestao.recepcao import (
    ArquivoRecebido,
    ResultadoLacre,
    TipoArquivo,
    detectar_tipo,
    lacrar,
)
from lupa_pipeline.ingestao.storage import ArmazenamentoMemoria, ObjectStorage

if TYPE_CHECKING:
    from lupa_pipeline.sinteticos.gabarito import Cenario, Gabarito


@dataclass(frozen=True)
class ProcessoSemeado:
    """Processo sintético gravado com commit.

    Attributes:
        hk_processo: Processo.
        hk_usuario: Criador (assessor sintético).
        numero_cnj: Número só com dígitos, como no hub.
    """

    hk_processo: bytes
    hk_usuario: bytes
    numero_cnj: str


@dataclass(frozen=True)
class ArquivoSemeado:
    """Arquivo lacrado por `lacrar` num processo sintético.

    Attributes:
        processo: Processo dono.
        hk_arquivo: Arquivo.
    """

    processo: ProcessoSemeado
    hk_arquivo: bytes


class Relogio:
    """Relógio controlável."""

    def __init__(self) -> None:
        """Começa no instante atual."""
        self.agora = datetime.now(UTC)

    def __call__(self) -> datetime:
        """Instante corrente."""
        return self.agora

    def avancar(self, segundos: float) -> None:
        """Avança o relógio.

        Args:
            segundos: Quanto avançar.
        """
        self.agora += timedelta(seconds=segundos)


class PararAoEsvaziar(Event):
    """Encerra o worker na primeira espera, sem usar o relógio real."""

    def __init__(self) -> None:
        """Guarda os intervalos solicitados pelo worker."""
        super().__init__()
        self.esperas: list[float | None] = []

    def wait(self, timeout: float | None = None) -> bool:
        """Registra o intervalo e simula a chegada de SIGTERM."""
        self.esperas.append(timeout)
        self.set()
        return True


def semear_processo(
    engine: Engine, *, classe: ClasseProcessual = ClasseProcessual.APELACAO_CIVEL
) -> ProcessoSemeado:
    """Grava, com commit, um processo sintético com criador assessor.

    Args:
        engine: Engine do banco de teste.
        classe: Classe processual.

    Returns:
        Chaves do processo e do criador.
    """
    with Session(engine) as session, session.begin():
        hk = criar_processo(session, classe=classe)
        processo = session.scalars(
            select(VisaoProcesso).where(VisaoProcesso.hk_processo == hk)
        ).one()
        assert processo.hk_criador is not None
        return ProcessoSemeado(hk, processo.hk_criador, processo.numero_cnj)


def lacrar_bytes(
    engine: Engine,
    storage: ObjectStorage,
    processo: ProcessoSemeado,
    caminho: Path,
    nome: str = "autos.pdf",
) -> ResultadoLacre:
    """Lacra, com commit, o arquivo do disco no processo.

    Args:
        engine: Engine do banco de teste.
        storage: Storage de objetos.
        processo: Processo dono.
        caminho: Arquivo com os bytes.
        nome: Nome original.

    Returns:
        O resultado do lacre.
    """
    dados = caminho.read_bytes()
    tipo = detectar_tipo(dados) or TipoArquivo.DESCONHECIDO
    recebido = ArquivoRecebido(caminho, calcular_hash_bytes(dados), len(dados), tipo)
    with Session(engine) as session, session.begin():
        return lacrar(
            session,
            storage,
            recebido,
            hk_processo=processo.hk_processo,
            enviado_por=processo.hk_usuario,
            nome_original=nome,
        )


@pytest.fixture
def relogio() -> Relogio:
    """Relógio controlável."""
    return Relogio()


@pytest.fixture
def storage_memoria() -> ArmazenamentoMemoria:
    """Storage em memória, no lugar do MinIO."""
    return ArmazenamentoMemoria()


SemearArquivo = Callable[..., ArquivoSemeado]


@pytest.fixture
def semear_arquivo(
    engine_teste: Engine, storage_memoria: ObjectStorage, tmp_path: Path
) -> SemearArquivo:
    """Fábrica: processo novo e arquivo lacrado nele, em `recebido`."""

    def _semear(dados: bytes, nome: str = "autos.pdf") -> ArquivoSemeado:
        processo = semear_processo(engine_teste)
        caminho = tmp_path / uuid4().hex
        caminho.write_bytes(dados)
        lacre = lacrar_bytes(engine_teste, storage_memoria, processo, caminho, nome)
        return ArquivoSemeado(processo, lacre.hk_arquivo)

    return _semear


def calcular_hash_bytes(dados: bytes) -> str:
    """SHA-256 hexadecimal de bytes.

    Args:
        dados: Conteúdo.

    Returns:
        Hash.
    """
    return hashlib.sha256(dados).hexdigest()


def fluxo(dados: bytes) -> io.BytesIO:
    """Envolve bytes num arquivo binário em memória.

    Args:
        dados: Conteúdo.

    Returns:
        Arquivo em memória.
    """
    return io.BytesIO(dados)


@dataclass(frozen=True)
class AutosSinteticos:
    """Processo sintético pequeno gerado nos três cenários (Etapa 4B), para a Etapa 4C.

    Attributes:
        arquivos: Arquivo de autos por cenário.
        gabaritos: Gabarito por cenário.
    """

    arquivos: dict[Cenario, Path]
    gabaritos: dict[Cenario, Gabarito]


@pytest.fixture(scope="session")
def autos_sinteticos(tmp_path_factory: pytest.TempPathFactory) -> AutosSinteticos:
    """Processo de ~45 folhas com todas as composições de página e todas as injeções."""
    from lupa_pipeline.sinteticos.empacotamento import exportar
    from lupa_pipeline.sinteticos.gabarito import TODOS_VETORES, Composicao, Gabarito
    from lupa_pipeline.sinteticos.gerador import gerar_conteudo
    from lupa_pipeline.sinteticos.roteiro import Configuracao

    mistura = {
        Composicao.NATIVA: 0.4,
        Composicao.DIGITALIZADA: 0.3,
        Composicao.HIBRIDA_CORPO: 0.15,
        Composicao.HIBRIDA_ASSINATURA: 0.15,
    }
    config = Configuracao(
        semente=7, paginas_alvo=45, mistura=mistura, injecoes=TODOS_VETORES,
        proporcao_vazias=0.3,
    )  # fmt: skip
    destino = tmp_path_factory.mktemp("autos-4c")
    gerados = exportar(gerar_conteudo(config), destino)
    return AutosSinteticos(
        arquivos={a.cenario: a.caminho for a in gerados},
        gabaritos={
            a.cenario: Gabarito.model_validate_json(a.gabarito.read_text(encoding="utf-8"))
            for a in gerados
        },
    )
