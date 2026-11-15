r"""Recepção e lacre: streaming com SHA-256, limite de tamanho, tipo pelo conteúdo e gravação.

O corpo chega em blocos e vai direto para um arquivo temporário, com o hash calculado no
caminho. Tipo desconhecido ou extensão `.pdf`/`.zip` incompatível com os bytes mágicos
seguem como `application/octet-stream` para a quarentena (RF-ING-02).
O lacre (A3, passos 4 a 7) cifra e grava o objeto em `processo/<hex do hk>/<sha256>` e, na
transação de quem chama, grava `hub_arquivo`, `link_processo_arquivo`, `sat_arquivo_dados` e o
estado `recebido` em `sat_arquivo_ingestao`. O mesmo conteúdo no mesmo processo não grava nada
novo: devolve o arquivo existente como duplicado (RF-ING-01). Dois envios simultâneos do mesmo
processo e seu descarte são serializados pela trava da transação sobre o processo.
"""

import hashlib
import os
import tempfile
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.enums import EstadoJob, StatusProcesso
from lupa_pipeline.dominio.gravacao import (
    chave_do_hub,
    gravar_hub,
    gravar_link,
    gravar_satelite,
    travar_processo,
)
from lupa_pipeline.dominio.tabelas import hub_arquivo, link_processo_arquivo, sat_arquivo_dados
from lupa_pipeline.dominio.visoes import VisaoArquivo, VisaoProcesso
from lupa_pipeline.ingestao import repositorio
from lupa_pipeline.ingestao.storage import ObjectStorage, chave_objeto

TAMANHO_CABECALHO = 8
ORIGEM = repositorio.ORIGEM


class TipoArquivo(StrEnum):
    """MIME para a triagem do arquivo recebido."""

    PDF = "application/pdf"
    ZIP = "application/zip"
    DESCONHECIDO = "application/octet-stream"


MAGICOS = {b"%PDF-": TipoArquivo.PDF, b"PK\x03\x04": TipoArquivo.ZIP}
EXTENSOES = {".pdf": TipoArquivo.PDF, ".zip": TipoArquivo.ZIP}


class MotivoRecusa(StrEnum):
    """Motivo de recusa na recepção."""

    TAMANHO = "tamanho"
    VAZIO = "vazio"


class RecepcaoRecusadaError(ValueError):
    """Arquivo recusado na recepção (antes de qualquer gravação)."""

    def __init__(self, motivo: MotivoRecusa) -> None:
        """Cria o erro.

        Args:
            motivo: Motivo da recusa.
        """
        super().__init__(motivo.value)
        self.motivo = motivo


class ProcessoDescartadoError(ValueError):
    """O processo foi descartado antes de o upload ser lacrado."""


@dataclass(frozen=True)
class ArquivoRecebido:
    """Arquivo recebido e conferido, ainda só no disco temporário.

    Attributes:
        caminho: Arquivo temporário (apagar depois de lacrar).
        sha256: Hash do conteúdo.
        tamanho_bytes: Tamanho.
        tipo: Tipo detectado pelo conteúdo.
    """

    caminho: Path
    sha256: str
    tamanho_bytes: int
    tipo: TipoArquivo


@dataclass(frozen=True)
class ResultadoLacre:
    """Resultado do lacre.

    Attributes:
        hk_arquivo: Arquivo (novo ou já existente).
        arquivo_id: Hex do `hk_arquivo` (D12).
        estado: Estado corrente da ingestão do arquivo.
        duplicado: Verdadeiro se o conteúdo já existia no processo.
    """

    hk_arquivo: bytes
    arquivo_id: str
    estado: str
    duplicado: bool


def detectar_tipo(cabecalho: bytes) -> TipoArquivo | None:
    """Detecta o tipo pelos primeiros bytes.

    Args:
        cabecalho: Início do arquivo.

    Returns:
        O tipo, ou None se não for PDF nem ZIP.
    """
    for magico, tipo in MAGICOS.items():
        if cabecalho.startswith(magico):
            return tipo
    return None


def extensao_confere(nome: str, tipo: TipoArquivo) -> bool:
    """Confere se a extensão, quando é `.pdf` ou `.zip`, coincide com o conteúdo.

    Args:
        nome: Nome original.
        tipo: Tipo detectado.

    Returns:
        Falso só quando a extensão conhecida contradiz o conteúdo.
    """
    esperado = EXTENSOES.get(Path(nome).suffix.lower())
    return esperado is None or esperado is tipo


async def receber(
    blocos: AsyncIterator[bytes], nome: str, limite_bytes: int, diretorio: Path | None
) -> ArquivoRecebido:
    """Grava o corpo em arquivo temporário calculando hash, tamanho e tipo.

    Args:
        blocos: Corpo da requisição em blocos.
        nome: Nome original (só para conferir a extensão).
        limite_bytes: Tamanho máximo aceito.
        diretorio: Diretório dos temporários (None = padrão do sistema).

    Returns:
        O arquivo recebido.

    Raises:
        RecepcaoRecusadaError: Vazio ou acima do limite (o temporário é apagado).
    """
    resumo = hashlib.sha256()
    tamanho = 0
    cabecalho = b""
    descritor, nome_temporario = tempfile.mkstemp(prefix="lupa-upload-", dir=diretorio)
    destino = Path(nome_temporario)
    try:
        with os.fdopen(descritor, "wb") as saida:
            async for bloco in blocos:
                tamanho += len(bloco)
                if tamanho > limite_bytes:
                    raise RecepcaoRecusadaError(MotivoRecusa.TAMANHO)
                if len(cabecalho) < TAMANHO_CABECALHO:
                    cabecalho += bloco[: TAMANHO_CABECALHO - len(cabecalho)]
                resumo.update(bloco)
                saida.write(bloco)
        return _conferir(destino, resumo.hexdigest(), tamanho, cabecalho, nome)
    except BaseException:
        destino.unlink(missing_ok=True)
        raise


def _conferir(
    caminho: Path, sha256: str, tamanho: int, cabecalho: bytes, nome: str
) -> ArquivoRecebido:
    if tamanho == 0:
        raise RecepcaoRecusadaError(MotivoRecusa.VAZIO)
    tipo = detectar_tipo(cabecalho)
    if tipo is None or not extensao_confere(nome, tipo):
        tipo = TipoArquivo.DESCONHECIDO
    return ArquivoRecebido(caminho, sha256, tamanho, tipo)


def _existente(session: Session, hk_arquivo: bytes) -> ResultadoLacre | None:
    consulta = select(VisaoArquivo.estado).where(VisaoArquivo.hk_arquivo == hk_arquivo)
    estado = session.scalar(consulta)
    if estado is None:
        return None
    return ResultadoLacre(hk_arquivo, hk_arquivo.hex(), estado, duplicado=True)


def _gravar_objeto(storage: ObjectStorage, chave: str, recebido: ArquivoRecebido) -> None:
    with recebido.caminho.open("rb") as origem:
        storage.gravar(chave, origem)


def _gravar_arquivo(
    session: Session,
    processo: VisaoProcesso,
    recebido: ArquivoRecebido,
    chave_storage: str,
    enviado_por: bytes,
    nome_original: str,
) -> bytes:
    chave = {"numero_cnj": processo.numero_cnj, "sha256": recebido.sha256}
    hk_arquivo = gravar_hub(session, hub_arquivo, chave, ORIGEM)
    ligacao = {"hk_processo": processo.hk_processo, "hk_arquivo": hk_arquivo}
    gravar_link(session, link_processo_arquivo, ligacao, ORIGEM)
    dados = {
        "tamanho_bytes": recebido.tamanho_bytes,
        "nome_original": nome_original,
        "mime": recebido.tipo.value,
        "chave_storage": chave_storage,
        "hk_usuario": enviado_por,
    }
    gravar_satelite(session, sat_arquivo_dados, hk_arquivo, dados, ORIGEM)
    repositorio.registrar_recebido(session, hk_arquivo)
    return hk_arquivo


def lacrar(
    session: Session,
    storage: ObjectStorage,
    recebido: ArquivoRecebido,
    *,
    hk_processo: bytes,
    enviado_por: bytes,
    nome_original: str,
) -> ResultadoLacre:
    """Grava o objeto cifrado e registra o arquivo em `recebido` (A3, passos 4 a 7).

    A DEK do processo precisa estar ativa no contexto de cifra (`ativar_processo`), porque o
    objeto e `nome_original` são cifrados com ela. Um objeto gravado por uma transação que
    depois desfez fica órfão e é sobrescrito no próximo envio do mesmo arquivo (A3, passo 8).

    Args:
        session: Sessão da requisição, sob `lupa_app`.
        storage: Object storage (cifrado).
        recebido: Arquivo conferido.
        hk_processo: Processo.
        enviado_por: `hk_usuario` de quem enviou.
        nome_original: Nome informado pelo cliente.

    Returns:
        O arquivo novo, ou o existente como duplicado quando o conteúdo é repetido.

    Raises:
        ArquivoNaoEncontradoError: Processo inexistente (o arquivo não tem onde entrar).
    """
    processo = travar_processo(session, hk_processo)
    if processo is None:
        raise repositorio.ArquivoNaoEncontradoError(hk_processo.hex())
    if processo.status == StatusProcesso.DESCARTADO.value:
        raise ProcessoDescartadoError("processo descartado")
    chave = {"numero_cnj": processo.numero_cnj, "sha256": recebido.sha256}
    hk_arquivo = chave_do_hub(hub_arquivo, chave)
    existente = _existente(session, hk_arquivo)
    if existente is not None:
        return existente
    chave_storage = chave_objeto(hk_processo, recebido.sha256)
    _gravar_objeto(storage, chave_storage, recebido)
    _gravar_arquivo(session, processo, recebido, chave_storage, enviado_por, nome_original)
    return ResultadoLacre(hk_arquivo, hk_arquivo.hex(), EstadoJob.RECEBIDO.value, duplicado=False)
