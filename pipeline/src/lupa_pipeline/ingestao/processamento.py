"""Validação, diagnóstico e extração de um arquivo da fila do PostgreSQL (A5)."""

from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from time import monotonic
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.enums import (
    EstadoJob,
    EstadoLote,
    MotivoFalha,
    MotivoQuarentena,
    StatusProcesso,
)
from lupa_pipeline.dominio.esquemas import DiagnosticoArquivo, EntradaManifesto
from lupa_pipeline.dominio.gravacao import gravar_satelite, travar_processo
from lupa_pipeline.dominio.sessao import assumir_papel_aplicacao
from lupa_pipeline.dominio.tabelas import sat_arquivo_diagnostico, sat_arquivo_lote
from lupa_pipeline.dominio.visoes import VisaoArquivo
from lupa_pipeline.ingestao import paginas
from lupa_pipeline.ingestao.cache import copiar_do_cache
from lupa_pipeline.ingestao.diagnostico import diagnosticar_pdf, diagnosticar_zip
from lupa_pipeline.ingestao.eventos.etapa import processar_eventos
from lupa_pipeline.ingestao.extracao import (
    FontePaginas,
    ResultadoTarefa,
    Tarefa,
    executar_tarefa,
    linha_pagina,
    pendentes,
    planejar,
)
from lupa_pipeline.ingestao.extrator_paginas import VERSAO_EXTRATOR
from lupa_pipeline.ingestao.indice import montar_indice, versoes
from lupa_pipeline.ingestao.inventario import (
    EntradaExtraida,
    LimitesZip,
    ZipRecusadoError,
    inventariar,
)
from lupa_pipeline.ingestao.qualidade import relatorio_qualidade
from lupa_pipeline.ingestao.quarentena import motivo_do_parser
from lupa_pipeline.ingestao.recepcao import TipoArquivo
from lupa_pipeline.ingestao.repositorio import (
    ORIGEM,
    atualizar_status_processo,
    mudar_estado,
)
from lupa_pipeline.ingestao.repositorio_pecas import gravar_indice
from lupa_pipeline.ingestao.sandbox import LimitesSandbox, inspecionar_pdfs
from lupa_pipeline.ingestao.storage import ObjectStorage, ObjetoAusenteError, chave_objeto
from lupa_pipeline.logging import get_logger

log = get_logger(__name__)


class ProcessoDescartadoError(Exception):
    """O processo foi descartado enquanto um lote estava no sandbox."""


class FalhaSandboxError(Exception):
    """O sandbox devolveu o motivo técnico para encerrar o processamento."""

    def __init__(self, motivo: MotivoFalha) -> None:
        """Preserva o motivo enumerado para o satélite de ingestão."""
        super().__init__(motivo.value)
        self.motivo = motivo


@dataclass(frozen=True)
class Trabalho:
    """Sessões e chaves de um arquivo durante uma execução."""

    fabrica: sessionmaker[Session]
    arquivo: VisaoArquivo

    @contextmanager
    def transacao(self) -> Iterator[Session]:
        """Serializa cada gravação com o descarte do processo."""
        with self.fabrica.begin() as session:
            assumir_papel_aplicacao(session)
            processo = travar_processo(session, self.arquivo.hk_processo)
            if processo is None or processo.status == StatusProcesso.DESCARTADO:
                raise ProcessoDescartadoError
            yield session

    def terminar(self, estado: EstadoJob, **campos: Any) -> None:
        """Confirma o desfecho e o status do processo juntos."""
        with self.transacao() as session:
            mudar_estado(session, self.arquivo.hk_arquivo, estado, **campos)
            atualizar_status_processo(session, self.arquivo.hk_processo)


def _entradas(arquivo: VisaoArquivo, original: Path, settings: Settings) -> list[EntradaExtraida]:
    if arquivo.mime == TipoArquivo.PDF.value:
        entrada = EntradaManifesto(
            ordem=1,
            nome=arquivo.nome_original or "autos.pdf",
            tamanho_bytes=original.stat().st_size,
            sha256=arquivo.sha256,
        )
        return [EntradaExtraida(entrada, original)]
    if arquivo.mime != TipoArquivo.ZIP.value:
        raise ZipRecusadoError(MotivoQuarentena.TIPO_INVALIDO, "tipo inválido")
    limites = LimitesZip(
        settings.zip_max_entradas, settings.zip_max_razao, settings.zip_max_descomprimido_bytes
    )
    return inventariar(original, original.parent, limites)


def _inspecionar(entradas: list[EntradaExtraida], limites: LimitesSandbox) -> list[dict[str, Any]]:
    inspecoes: list[dict[str, Any]] = []
    for inicio in range(0, len(entradas), 32):
        caminhos = [e.caminho for e in entradas[inicio : inicio + 32]]
        for resultado in inspecionar_pdfs(caminhos, limites):
            if resultado.motivo_falha:
                raise FalhaSandboxError(resultado.motivo_falha)
            motivo = motivo_do_parser(resultado.dados)
            if motivo:
                raise ZipRecusadoError(motivo, "arquivo recusado na inspeção")
            inspecoes.append(resultado.dados)
    return inspecoes


def _preparar(
    trabalho: Trabalho,
    storage: ObjectStorage,
    diretorio: Path,
    settings: Settings,
    limites: LimitesSandbox,
) -> tuple[list[FontePaginas], DiagnosticoArquivo]:
    arquivo = trabalho.arquivo
    if not arquivo.chave_storage:
        raise ObjetoAusenteError("objeto indisponível")
    if arquivo.estado == EstadoJob.EM_EXTRACAO and arquivo.cenario and arquivo.manifesto:
        fontes = []
        total = 0
        for item in arquivo.manifesto:
            caminho = diretorio / f"fonte-{item['ordem']}.pdf"
            chave = chave_objeto(arquivo.hk_processo, item["sha256"])
            caminho.touch(mode=0o600, exist_ok=False)
            caminho.write_bytes(storage.ler(chave))
            fontes.append(FontePaginas(caminho, item["nome"], item["paginas"], total))
            total += item["paginas"]
        return fontes, DiagnosticoArquivo.model_validate(
            {
                "arquivo_id": arquivo.id,
                "cenario": arquivo.cenario,
                "total_paginas": total,
                "tem_indice": arquivo.tem_indice,
                "sinais": arquivo.sinais,
                "fronteiras_origem": arquivo.fronteiras_origem,
                "metadados_descartados": arquivo.metadados_descartados,
            }
        )
    original = diretorio / "original"
    original.touch(mode=0o600, exist_ok=False)
    original.write_bytes(storage.ler(arquivo.chave_storage))
    entradas = _entradas(arquivo, original, settings)
    inspecoes = _inspecionar(entradas, limites)
    fontes = []
    manifesto = []
    total = 0
    for entrada, dados in zip(entradas, inspecoes, strict=True):
        item = entrada.manifesto
        quantidade = int(dados["paginas"])
        nome = f"entrada-{item.ordem}.pdf"
        fontes.append(FontePaginas(entrada.caminho, nome, quantidade, total))
        manifesto.append(item.model_dump() | {"nome": nome, "paginas": quantidade})
        total += quantidade
    if arquivo.mime == TipoArquivo.ZIP.value:
        diagnostico = diagnosticar_zip(
            arquivo.id, [(e.manifesto.nome, i) for e, i in zip(entradas, inspecoes, strict=True)]
        )
    else:
        diagnostico = diagnosticar_pdf(arquivo.id, entradas[0].manifesto.nome, inspecoes[0])
    nomes = {e.manifesto.nome: f.nome for e, f in zip(entradas, fontes, strict=True)}
    diagnostico = diagnostico.model_copy(
        update={
            "fronteiras_origem": [
                {k: v for k, v in f.items() if k not in {"arquivo", "titulo"}}
                | {"arquivo": nomes.get(f.get("arquivo", ""), "entrada-1.pdf")}
                for f in diagnostico.fronteiras_origem
            ],
            "metadados_descartados": [
                m | {"entrada": nomes.get(m.get("entrada", ""), "entrada-1.pdf")}
                for m in diagnostico.metadados_descartados
            ],
        }
    )
    if arquivo.estado == EstadoJob.RECEBIDO:
        with trabalho.transacao() as session:
            if arquivo.mime == TipoArquivo.ZIP.value:
                for entrada in entradas:
                    chave = chave_objeto(arquivo.hk_processo, entrada.manifesto.sha256)
                    with entrada.caminho.open("rb") as origem:
                        storage.gravar(chave, origem)
            mudar_estado(
                session,
                arquivo.hk_arquivo,
                EstadoJob.VALIDADO,
                manifesto=manifesto,
                total_paginas=total,
            )
    with trabalho.transacao() as session:
        gravar_satelite(
            session,
            sat_arquivo_diagnostico,
            arquivo.hk_arquivo,
            diagnostico.model_dump(mode="json", exclude={"arquivo_id"}),
            ORIGEM,
        )
        mudar_estado(
            session, arquivo.hk_arquivo, EstadoJob.EM_EXTRACAO, versao_extrator=VERSAO_EXTRATOR
        )
        atualizar_status_processo(session, arquivo.hk_processo)
    return fontes, diagnostico


def _extrair_lote(tarefa: Tarefa, limites: LimitesSandbox, retentativas: int) -> ResultadoTarefa:
    for tentativa in range(retentativas + 1):
        resultado = executar_tarefa(tarefa, limites)
        if (
            resultado.motivo_falha not in (MotivoFalha.TEMPO_ESGOTADO, MotivoFalha.ERRO_PARSER)
            or tentativa == retentativas
        ):
            return resultado
    raise ValueError("quantidade inválida de retentativas")


def _processar_lotes(
    trabalho: Trabalho,
    fontes: list[FontePaginas],
    settings: Settings,
    limites: LimitesSandbox,
    parar: Event,
) -> Counter[str]:
    hk = trabalho.arquivo.hk_arquivo
    with trabalho.transacao() as session:
        prontas = paginas.prontas(session, hk, VERSAO_EXTRATOR)
    falhas: Counter[str] = Counter()
    for numero, lote in enumerate(planejar(fontes, settings.extracao_paginas_por_lote), 1):
        if parar.is_set():
            break
        faltam = set(lote.numeros) - prontas
        if faltam:
            with trabalho.transacao() as session:
                prontas.update(
                    copiar_do_cache(
                        session,
                        trabalho.arquivo,
                        VERSAO_EXTRATOR,
                        sum(f.paginas for f in fontes),
                        faltam,
                    )
                )
        restantes = pendentes([lote], prontas)
        if not restantes:
            with trabalho.transacao() as session:
                gravar_satelite(
                    session,
                    sat_arquivo_lote,
                    hk,
                    {
                        "numero": numero,
                        "estado": "concluido",
                        "resultado": {
                            "paginas": list(lote.numeros),
                            "faltantes": [],
                            "motivo": None,
                        },
                    },
                    ORIGEM,
                )
            log.info("lote_gravado", arquivo_id=hk.hex(), lote=numero, faltantes=0)
            continue
        faltam = set(lote.numeros) - prontas
        motivo = None
        extraidas: list[dict[str, Any]] = []
        for tarefa in restantes:
            resultado = _extrair_lote(tarefa, limites, settings.max_retentativas)
            motivo = resultado.motivo_falha
            if motivo in (MotivoFalha.LIMITE_MEMORIA, MotivoFalha.LIMITE_CPU):
                raise FalhaSandboxError(motivo)
            extraidas.extend(
                p for p in resultado.paginas if "erro" not in p and p["numero"] in faltam
            )
        with trabalho.transacao() as session:
            for pagina in extraidas:
                paginas.gravar_pagina(
                    session, trabalho.arquivo, linha_pagina(pagina, VERSAO_EXTRATOR)
                )
                faltam.discard(int(pagina["numero"]))
            if faltam:
                falhas[(motivo or MotivoFalha.ERRO_PARSER).value] += len(faltam)
            atributos = {
                "numero": numero,
                "estado": EstadoLote.FALHO.value if faltam else EstadoLote.CONCLUIDO.value,
                "resultado": {
                    "paginas": list(lote.numeros),
                    "faltantes": sorted(faltam),
                    "motivo": motivo.value if motivo else None,
                },
            }
            gravar_satelite(session, sat_arquivo_lote, hk, atributos, ORIGEM)
        log.info("lote_gravado", arquivo_id=hk.hex(), lote=numero, faltantes=len(faltam))
    return falhas


def _processar(
    trabalho: Trabalho, settings: Settings, storage: ObjectStorage, parar: Event
) -> None:
    limites = LimitesSandbox(
        settings.sandbox_memoria_mb, settings.sandbox_cpu_segundos, settings.sandbox_tempo_segundos
    )
    inicio = monotonic()
    with TemporaryDirectory(
        prefix="lupa-extracao-", dir=settings.ingestao_dir_temporario
    ) as diretorio:
        fontes, diagnostico = _preparar(trabalho, storage, Path(diretorio), settings, limites)
        falhas = _processar_lotes(trabalho, fontes, settings, limites, parar)
    if parar.is_set():
        return
    with trabalho.transacao() as session:
        arquivo = trabalho.arquivo
        linhas = paginas.paginas_para_indice(session, arquivo.hk_arquivo, VERSAO_EXTRATOR)
        relatorio = relatorio_qualidade(
            linhas,
            total_paginas=diagnostico.total_paginas,
            tempo_parede_segundos=monotonic() - inicio,
            falhas=falhas,
            versao_extrator=VERSAO_EXTRATOR,
            metadados=diagnostico.metadados_descartados,
        )
        resultado = montar_indice(linhas, diagnostico.model_dump(mode="json"))
        gravar_indice(session, arquivo, linhas, resultado)
    with trabalho.transacao() as session:
        relatorio["eventos"] = processar_eventos(
            session, arquivo.hk_processo, datetime.now(UTC).date()
        )
        relatorio["indice"] = {
            "fonte": resultado.fonte,
            "pecas": len(resultado.pecas),
            "versoes": versoes(),
        }
        relatorio["divergencias_fronteira"] = resultado.divergencias
        estado = EstadoJob.PARCIAL if relatorio["paginas_faltando"] else EstadoJob.CONCLUIDO
        mudar_estado(session, arquivo.hk_arquivo, estado, relatorio=relatorio)
        atualizar_status_processo(session, arquivo.hk_processo)
    log.info("arquivo_finalizado", arquivo_id=arquivo.id, estado=estado.value)


def processar_arquivo(
    fabrica: sessionmaker[Session],
    settings: Settings,
    storage: ObjectStorage,
    hk_arquivo: bytes,
    parar: Event,
) -> None:
    """Valida, extrai e indexa o arquivo com a DEK ativada pelo worker."""
    with fabrica() as session:
        assumir_papel_aplicacao(session)
        arquivo = session.get_one(VisaoArquivo, hk_arquivo)
        session.expunge(arquivo)
    trabalho = Trabalho(fabrica, arquivo)
    try:
        try:
            _processar(trabalho, settings, storage, parar)
        except ZipRecusadoError as erro:
            trabalho.terminar(EstadoJob.QUARENTENA, motivo_quarentena=erro.motivo)
        except FalhaSandboxError as erro:
            trabalho.terminar(EstadoJob.FALHO, motivo_falha=erro.motivo)
        except ObjetoAusenteError:
            trabalho.terminar(EstadoJob.FALHO, motivo_falha=MotivoFalha.ARQUIVO_AUSENTE)
    except ProcessoDescartadoError:
        return
