"""Object storage com interface própria: S3 (MinIO no piloto) e memória (testes).

A implementação é escolhida por configuração (`LUPA_STORAGE_BACKEND`). As chaves seguem
`processo/<hex do hk_processo>/<sha256>` (D14), de modo que o conteúdo é endereçado pelo hash e
gravar o mesmo arquivo duas vezes não cria um segundo objeto. Os objetos são gravados como
recebidos, sem cifra da aplicação (RF-SEG-01).
"""

import io
from pathlib import Path
from typing import Any, BinaryIO, Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from lupa_pipeline.config import Settings

CODIGOS_AUSENTE = frozenset({"404", "NoSuchKey", "NotFound"})


class ObjetoAusenteError(LookupError):
    """O objeto pedido não existe no storage."""


def chave_objeto(hk_processo: bytes, sha256: str) -> str:
    """Monta a chave do objeto de um arquivo.

    Args:
        hk_processo: Processo dono.
        sha256: Hash do conteúdo.

    Returns:
        `processo/<hex do hk_processo>/<sha256>`.
    """
    return f"{prefixo_processo(hk_processo)}{sha256}"


def prefixo_processo(hk_processo: bytes) -> str:
    """Prefixo de todos os objetos de um processo (originais e entradas de ZIP).

    Args:
        hk_processo: Processo dono.

    Returns:
        `processo/<hex do hk_processo>/`.
    """
    return f"processo/{hk_processo.hex()}/"


class ObjectStorage(Protocol):
    """Contrato do object storage usado pela ingestão."""

    def gravar(self, chave: str, origem: BinaryIO) -> None:
        """Grava o conteúdo lido de `origem` (até o fim) na chave."""

    def ler(self, chave: str) -> bytes:
        """Lê o objeto inteiro; lança `ObjetoAusenteError` se não existir."""

    def baixar_para(self, chave: str, caminho: Path) -> None:
        """Grava o objeto no arquivo `caminho`; lança `ObjetoAusenteError` se não existir."""

    def existe(self, chave: str) -> bool:
        """Diz se a chave existe."""

    def apagar(self, chave: str) -> None:
        """Apaga a chave (sem erro se não existir)."""

    def listar(self, prefixo: str) -> list[str]:
        """Lista, em ordem, as chaves que começam com o prefixo."""


class ArmazenamentoMemoria:
    """Storage em memória, para testes e desenvolvimento."""

    def __init__(self) -> None:
        """Cria o storage vazio."""
        self._objetos: dict[str, bytes] = {}

    def gravar(self, chave: str, origem: BinaryIO) -> None:
        """Grava o conteúdo.

        Args:
            chave: Chave do objeto.
            origem: Arquivo binário lido até o fim.
        """
        self._objetos[chave] = origem.read()

    def ler(self, chave: str) -> bytes:
        """Lê o objeto.

        Args:
            chave: Chave do objeto.

        Returns:
            Conteúdo.

        Raises:
            ObjetoAusenteError: Se a chave não existir.
        """
        try:
            return self._objetos[chave]
        except KeyError:
            raise ObjetoAusenteError(chave) from None

    def baixar_para(self, chave: str, caminho: Path) -> None:
        """Grava o objeto no arquivo.

        Args:
            chave: Chave do objeto.
            caminho: Arquivo de destino, criado ou sobrescrito.

        Raises:
            ObjetoAusenteError: Se a chave não existir.
        """
        caminho.write_bytes(self.ler(chave))

    def existe(self, chave: str) -> bool:
        """Diz se a chave existe.

        Args:
            chave: Chave do objeto.

        Returns:
            Verdadeiro se existir.
        """
        return chave in self._objetos

    def apagar(self, chave: str) -> None:
        """Apaga a chave.

        Args:
            chave: Chave do objeto.
        """
        self._objetos.pop(chave, None)

    def listar(self, prefixo: str) -> list[str]:
        """Lista chaves pelo prefixo.

        Args:
            prefixo: Prefixo.

        Returns:
            Chaves em ordem.
        """
        return sorted(chave for chave in self._objetos if chave.startswith(prefixo))


class ArmazenamentoS3:
    """Storage S3 via boto3; no piloto aponta para o MinIO (troca de endpoint para a AWS)."""

    def __init__(self, cliente: Any, bucket: str) -> None:
        """Cria o adaptador.

        Args:
            cliente: Cliente `boto3` de S3.
            bucket: Bucket dos autos.
        """
        self._cliente = cliente
        self._bucket = bucket

    def gravar(self, chave: str, origem: BinaryIO) -> None:
        """Grava o conteúdo em streaming (multipart quando grande).

        Args:
            chave: Chave do objeto.
            origem: Arquivo binário lido até o fim.
        """
        self._cliente.upload_fileobj(origem, self._bucket, chave)

    def ler(self, chave: str) -> bytes:
        """Lê o objeto.

        Args:
            chave: Chave do objeto.

        Returns:
            Conteúdo.

        Raises:
            ObjetoAusenteError: Se a chave não existir.
        """
        destino = io.BytesIO()
        try:
            self._cliente.download_fileobj(self._bucket, chave, destino)
        except ClientError as erro:
            if _ausente(erro):
                raise ObjetoAusenteError(chave) from None
            raise
        return destino.getvalue()

    def baixar_para(self, chave: str, caminho: Path) -> None:
        """Grava o objeto no arquivo em streaming, sem passar o conteúdo inteiro pela memória.

        Args:
            chave: Chave do objeto.
            caminho: Arquivo de destino, criado ou sobrescrito.

        Raises:
            ObjetoAusenteError: Se a chave não existir.
        """
        with caminho.open("wb") as destino:
            try:
                self._cliente.download_fileobj(self._bucket, chave, destino)
            except ClientError as erro:
                if _ausente(erro):
                    raise ObjetoAusenteError(chave) from None
                raise

    def existe(self, chave: str) -> bool:
        """Diz se a chave existe.

        Args:
            chave: Chave do objeto.

        Returns:
            Verdadeiro se existir.
        """
        try:
            self._cliente.head_object(Bucket=self._bucket, Key=chave)
        except ClientError as erro:
            if _ausente(erro):
                return False
            raise
        return True

    def apagar(self, chave: str) -> None:
        """Apaga a chave.

        Args:
            chave: Chave do objeto.
        """
        self._cliente.delete_object(Bucket=self._bucket, Key=chave)

    def listar(self, prefixo: str) -> list[str]:
        """Lista chaves pelo prefixo, percorrendo todas as páginas.

        Args:
            prefixo: Prefixo.

        Returns:
            Chaves em ordem.
        """
        paginador = self._cliente.get_paginator("list_objects_v2")
        chaves = [
            objeto["Key"]
            for pagina in paginador.paginate(Bucket=self._bucket, Prefix=prefixo)
            for objeto in pagina.get("Contents", [])
        ]
        return sorted(chaves)


def _ausente(erro: ClientError) -> bool:
    return str(erro.response.get("Error", {}).get("Code")) in CODIGOS_AUSENTE


def criar_cliente_s3(settings: Settings) -> Any:
    """Cria o cliente boto3 para o endpoint configurado.

    Args:
        settings: Configuração (endpoint, chaves, TLS).

    Returns:
        Cliente S3.
    """
    esquema = "https" if settings.minio_secure else "http"
    return boto3.client(
        "s3",
        endpoint_url=f"{esquema}://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key.get_secret_value(),
        aws_secret_access_key=settings.minio_secret_key.get_secret_value(),
        region_name=settings.storage_regiao,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def criar_storage(settings: Settings) -> ObjectStorage:
    """Escolhe a implementação pelo `storage_backend` da configuração.

    Args:
        settings: Configuração.

    Returns:
        Storage S3 ou em memória.
    """
    if settings.storage_backend == "memoria":
        return ArmazenamentoMemoria()
    return ArmazenamentoS3(criar_cliente_s3(settings), settings.minio_bucket)
