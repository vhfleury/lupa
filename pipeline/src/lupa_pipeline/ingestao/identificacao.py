"""Identificação do processo nas primeiras páginas dos autos (A1 e A2)."""

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic

from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.chaves import normalizar_cnj
from lupa_pipeline.dominio.cnj import (
    NumeroCnjInvalidoError,
    formatar_numero_cnj,
    validar_numero_cnj,
)
from lupa_pipeline.dominio.enums import ClasseProcessual, MotivoFalha, MotivoQuarentena
from lupa_pipeline.ingestao.eventos.padroes import campo_capa, padroes, rotulos_capa
from lupa_pipeline.ingestao.extracao import Executor, FontePaginas, Tarefa, executar_tarefa
from lupa_pipeline.ingestao.inventario import LimitesZip, ZipRecusadoError
from lupa_pipeline.ingestao.quarentena import motivo_do_parser
from lupa_pipeline.ingestao.recepcao import ArquivoRecebido, TipoArquivo
from lupa_pipeline.ingestao.sandbox import (
    FalhaSandboxError,
    LimitesSandbox,
    executar,
    inspecionar_pdf,
    inventariar_zip,
)
from lupa_pipeline.ingestao.texto import dobrar
from lupa_pipeline.logging import get_logger

NUMERO = re.compile(
    r"(?<!\d)(?:[0-9]{7}-[0-9]{2}\.[0-9]{4}\.[0-9]\.[0-9]{2}\.[0-9]{4}|[0-9]{20})(?!\d)"
)
ROTULO_NUMERO = re.compile(
    rf"(?<!\w)(?:{rotulos_capa('numero')})(?=[\s:]|$)[ \t]*:?[ \t]*(?:\r?\n[ \t]*)?"
)


@dataclass(frozen=True)
class Leitura:
    """Textos normalizados em ordem, conservando a posição de cada página."""

    paginas: tuple[str, ...]


@dataclass(frozen=True)
class LeituraRecusada:
    """Defeito estrutural que impede o cadastro mesmo com dados informados."""

    motivo: MotivoQuarentena


@dataclass(frozen=True)
class Identificacao:
    """Número e candidatos em dígitos, classe reconhecida na capa."""

    numero_cnj: str | None
    classe: ClasseProcessual | None
    numeros_encontrados: tuple[str, ...]


def ler_capa(
    recebido: ArquivoRecebido, settings: Settings, *, executor: Executor = executar
) -> Leitura | LeituraRecusada:
    """Inspeciona o arquivo e lê as primeiras páginas no sandbox."""
    if recebido.tipo == TipoArquivo.DESCONHECIDO:
        return LeituraRecusada(MotivoQuarentena.TIPO_INVALIDO)
    prazo = monotonic() + settings.identificacao_tempo_segundos

    def limites() -> LimitesSandbox:
        restante = prazo - monotonic()
        if restante <= 0:
            raise FalhaSandboxError(MotivoFalha.TEMPO_ESGOTADO)
        return LimitesSandbox(settings.sandbox_memoria_mb, settings.sandbox_cpu_segundos, restante)

    try:
        with TemporaryDirectory(prefix="lupa-capa-", dir=settings.ingestao_dir_temporario) as pasta:
            caminho = recebido.caminho
            if recebido.tipo == TipoArquivo.ZIP:
                zip_limites = LimitesZip(
                    settings.zip_max_entradas,
                    settings.zip_max_razao,
                    settings.zip_max_descomprimido_bytes,
                )
                caminho = inventariar_zip(caminho, Path(pasta), zip_limites, limites())[0].caminho
            inspecao = inspecionar_pdf(caminho, limites())
            if inspecao.motivo_falha:
                raise FalhaSandboxError(inspecao.motivo_falha)
            if motivo := motivo_do_parser(inspecao.dados):
                return LeituraRecusada(motivo)
            fonte = FontePaginas(caminho, "", int(inspecao.dados["paginas"]), 0)
            tarefa = Tarefa(fonte, 1, min(fonte.paginas, settings.identificacao_paginas))
            lote = executar_tarefa(tarefa, limites(), executor)
            if lote.motivo_falha:
                raise FalhaSandboxError(lote.motivo_falha)
            return Leitura(tuple(str(p.get("texto_normalizado") or "") for p in lote.paginas))
    except ZipRecusadoError as erro:
        return LeituraRecusada(erro.motivo)
    except FalhaSandboxError as falha:
        get_logger(__name__).warning(
            "falha_leitura_capa", motivo=falha.motivo.value, sha256=recebido.sha256
        )
        return Leitura(())


def _validos(ocorrencias: Iterator[re.Match[str]]) -> Iterator[str]:
    for ocorrencia in ocorrencias:
        try:
            yield normalizar_cnj(validar_numero_cnj(formatar_numero_cnj(ocorrencia[0])))
        except NumeroCnjInvalidoError:
            continue


def _classe(paginas: Sequence[str]) -> ClasseProcessual | None:
    classes = {
        dobrar(variante): ClasseProcessual(classe)
        for classe, variantes in padroes()["capa"]["classes"].items()
        for variante in variantes
    }
    for pagina in paginas:
        for campo in campo_capa("classe").finditer(dobrar(pagina)):
            if classe := classes.get(" ".join(campo["valor"].split())):
                return classe
    return None


def identificar(paginas: Sequence[str]) -> Identificacao:
    """Lê o CNJ e a classe das páginas normalizadas, na ordem de leitura."""
    numeros = tuple(
        dict.fromkeys(n for pagina in paginas for n in _validos(NUMERO.finditer(pagina)))
    )
    primeira = dobrar(paginas[0]) if paginas else ""
    rotulos = list(ROTULO_NUMERO.finditer(primeira))
    numero = numeros[0] if len(numeros) == 1 else None
    if rotulos:
        rotulados = (m for rotulo in rotulos if (m := NUMERO.match(primeira, rotulo.end())))
        numero = next(_validos(rotulados), None)
    return Identificacao(numero, _classe(paginas), numeros)
