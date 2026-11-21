"""Validação, diagnóstico e extração de um arquivo da fila do PostgreSQL (A5)."""

from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
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
from lupa_pipeline.ingestao import paginas, reprocessamento
from lupa_pipeline.ingestao.cache import copiar_do_cache
from lupa_pipeline.ingestao.diagnostico import diagnosticar_pdf, diagnosticar_zip
from lupa_pipeline.ingestao.eventos.etapa import atualizar_achados, processar_eventos
from lupa_pipeline.ingestao.extracao import (
    FontePaginas,
    ResultadoTarefa,
    Tarefa,
    executar_em_paralelo,
    executar_tarefa,
    linha_pagina,
    pendentes,
    planejar,
)
from lupa_pipeline.ingestao.indice import montar_indice
from lupa_pipeline.ingestao.inventario import EntradaExtraida, LimitesZip, ZipRecusadoError
from lupa_pipeline.ingestao.qualidade import relatorio_qualidade
from lupa_pipeline.ingestao.quarentena import motivo_do_parser
from lupa_pipeline.ingestao.recepcao import TipoArquivo
from lupa_pipeline.ingestao.repositorio import (
    ORIGEM,
    atualizar_status_processo,
    mudar_estado,
)
from lupa_pipeline.ingestao.repositorio_pecas import gravar_indice
from lupa_pipeline.ingestao.sandbox import (
    FalhaSandboxError,
    LimitesSandbox,
    inspecionar_pdfs,
    inventariar_zip,
)
from lupa_pipeline.ingestao.storage import ObjectStorage, ObjetoAusenteError, chave_objeto
from lupa_pipeline.logging import get_logger

log = get_logger(__name__)


class ProcessoDescartadoError(Exception):
    """O processo foi descartado enquanto um lote estava no sandbox."""


@dataclass(frozen=True)
class Trabalho:
    """Sessões e chaves de um arquivo durante uma execução."""

    fabrica: sessionmaker[Session]
    arquivo: VisaoArquivo
    versoes: dict[str, Any]

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


Inventariar = Callable[[VisaoArquivo, Path, Settings, LimitesSandbox], list[EntradaExtraida]]
Diagnosticar = Callable[
    [str, Sequence[tuple[str, dict[str, Any]]], Mapping[str, str]], DiagnosticoArquivo
]
Persistir = Callable[[ObjectStorage, bytes, Sequence[EntradaExtraida]], None]


@dataclass(frozen=True)
class Formato:
    """Como cada tipo de arquivo lacrado é inventariado, diagnosticado e persistido.

    Attributes:
        inventariar: Entradas do arquivo baixado (um PDF é uma entrada).
        diagnosticar: Diagnóstico das entradas inspecionadas, com os nomes internos.
        persistir: Grava no storage as entradas que ainda não estão lá.
    """

    inventariar: Inventariar
    diagnosticar: Diagnosticar
    persistir: Persistir


def _inventariar_pdf(
    arquivo: VisaoArquivo, original: Path, settings: Settings, sandbox: LimitesSandbox
) -> list[EntradaExtraida]:
    entrada = EntradaManifesto(
        ordem=1,
        nome=arquivo.nome_original or "autos.pdf",
        tamanho_bytes=original.stat().st_size,
        sha256=arquivo.sha256,
    )
    return [EntradaExtraida(entrada, original)]


def _inventariar_zip(
    arquivo: VisaoArquivo, original: Path, settings: Settings, sandbox: LimitesSandbox
) -> list[EntradaExtraida]:
    limites = LimitesZip(
        settings.zip_max_entradas, settings.zip_max_razao, settings.zip_max_descomprimido_bytes
    )
    return inventariar_zip(original, original.parent, limites, sandbox)


def _diagnosticar_pdf(
    arquivo_id: str, entradas: Sequence[tuple[str, dict[str, Any]]], nomes: Mapping[str, str]
) -> DiagnosticoArquivo:
    nome, inspecao = entradas[0]
    return diagnosticar_pdf(arquivo_id, nome, inspecao, nomes)


def _persistir_nada(
    storage: ObjectStorage, hk_processo: bytes, entradas: Sequence[EntradaExtraida]
) -> None:
    return None


def _persistir_entradas(
    storage: ObjectStorage, hk_processo: bytes, entradas: Sequence[EntradaExtraida]
) -> None:
    for entrada in entradas:
        chave = chave_objeto(hk_processo, entrada.manifesto.sha256)
        with entrada.caminho.open("rb") as origem:
            storage.gravar(chave, origem)


FORMATOS: dict[str, Formato] = {
    TipoArquivo.PDF.value: Formato(_inventariar_pdf, _diagnosticar_pdf, _persistir_nada),
    TipoArquivo.ZIP.value: Formato(_inventariar_zip, diagnosticar_zip, _persistir_entradas),
}


def _formato(arquivo: VisaoArquivo) -> Formato:
    formato = FORMATOS.get(arquivo.mime or "")
    if formato is None:
        raise ZipRecusadoError(MotivoQuarentena.TIPO_INVALIDO, "tipo inválido")
    return formato


def _fontes_do_manifesto(
    arquivo: VisaoArquivo, storage: ObjectStorage, diretorio: Path
) -> tuple[list[FontePaginas], DiagnosticoArquivo]:
    fontes = []
    total = 0
    for item in arquivo.manifesto or []:
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


def _fontes_do_original(
    trabalho: Trabalho,
    storage: ObjectStorage,
    diretorio: Path,
    settings: Settings,
    limites: LimitesSandbox,
) -> tuple[list[FontePaginas], DiagnosticoArquivo]:
    arquivo = trabalho.arquivo
    formato = _formato(arquivo)
    original = diretorio / "original"
    original.touch(mode=0o600, exist_ok=False)
    original.write_bytes(storage.ler(arquivo.chave_storage or ""))
    entradas = formato.inventariar(arquivo, original, settings, limites)
    inspecoes = _inspecionar(entradas, limites)
    fontes = []
    manifesto = []
    nomes: dict[str, str] = {}
    total = 0
    for entrada, dados in zip(entradas, inspecoes, strict=True):
        item = entrada.manifesto
        quantidade = int(dados["paginas"])
        nome = f"entrada-{item.ordem}.pdf"
        nomes[item.nome] = nome
        fontes.append(FontePaginas(entrada.caminho, nome, quantidade, total))
        manifesto.append(item.model_dump() | {"nome": nome, "paginas": quantidade})
        total += quantidade
    diagnostico = formato.diagnosticar(
        arquivo.id, [(e.manifesto.nome, i) for e, i in zip(entradas, inspecoes, strict=True)], nomes
    )
    if arquivo.estado == EstadoJob.RECEBIDO:
        with trabalho.transacao() as session:
            formato.persistir(storage, arquivo.hk_processo, entradas)
            mudar_estado(
                session,
                arquivo.hk_arquivo,
                EstadoJob.VALIDADO,
                manifesto=manifesto,
                total_paginas=total,
            )
    return fontes, diagnostico


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
        return _fontes_do_manifesto(arquivo, storage, diretorio)
    fontes, diagnostico = _fontes_do_original(trabalho, storage, diretorio, settings, limites)
    with trabalho.transacao() as session:
        gravar_satelite(
            session,
            sat_arquivo_diagnostico,
            arquivo.hk_arquivo,
            diagnostico.model_dump(mode="json", exclude={"arquivo_id"}),
            ORIGEM,
        )
        mudar_estado(
            session,
            arquivo.hk_arquivo,
            EstadoJob.EM_EXTRACAO,
            versao_extrator=trabalho.versoes["paginas"],
        )
        atualizar_status_processo(session, arquivo.hk_processo)
    return fontes, diagnostico


RETENTAVEIS = (MotivoFalha.TEMPO_ESGOTADO, MotivoFalha.ERRO_PARSER)
LIMITES_DUROS = (MotivoFalha.LIMITE_MEMORIA, MotivoFalha.LIMITE_CPU)


@dataclass(frozen=True)
class LotePlanejado:
    """Lote do plano com os intervalos que ainda exigem extração."""

    numero: int
    tarefa: Tarefa
    restantes: list[Tarefa]


def _extrair_lote(tarefa: Tarefa, limites: LimitesSandbox, retentativas: int) -> ResultadoTarefa:
    for _ in range(retentativas):
        resultado = executar_tarefa(tarefa, limites)
        if resultado.motivo_falha not in RETENTAVEIS:
            return resultado
    return executar_tarefa(tarefa, limites)


def _extrair_restantes(
    lote: LotePlanejado, limites: LimitesSandbox, retentativas: int
) -> tuple[LotePlanejado, list[ResultadoTarefa]]:
    resultados = []
    for tarefa in lote.restantes:
        resultados.append(_extrair_lote(tarefa, limites, retentativas))
        if resultados[-1].motivo_falha in LIMITES_DUROS:
            break
    return lote, resultados


def _gravar_lote(
    trabalho: Trabalho,
    lote: LotePlanejado,
    resultados: list[ResultadoTarefa],
    prontas: set[int],
    falhas: Counter[str],
) -> None:
    faltam = set(lote.tarefa.numeros) - prontas
    motivo = resultados[-1].motivo_falha if resultados else None
    linhas = []
    for resultado in resultados:
        for pagina in resultado.paginas:
            if "erro" in pagina or pagina["numero"] not in faltam:
                continue
            linhas.append(linha_pagina(pagina, trabalho.versoes["paginas"]))
            faltam.discard(int(pagina["numero"]))
    with trabalho.transacao() as session:
        paginas.gravar_paginas(session, trabalho.arquivo, linhas)
        if faltam:
            falhas[(motivo or MotivoFalha.ERRO_PARSER).value] += len(faltam)
        atributos = {
            "numero": lote.numero,
            "estado": EstadoLote.FALHO.value if faltam else EstadoLote.CONCLUIDO.value,
            "resultado": {
                "paginas": list(lote.tarefa.numeros),
                "faltantes": sorted(faltam),
                "motivo": motivo.value if motivo else None,
            },
        }
        gravar_satelite(session, sat_arquivo_lote, trabalho.arquivo.hk_arquivo, atributos, ORIGEM)
    log.info(
        "lote_gravado",
        arquivo_id=trabalho.arquivo.hk_arquivo.hex(),
        lote=lote.numero,
        faltantes=len(faltam),
    )


def _planejar_lotes(
    trabalho: Trabalho, fontes: list[FontePaginas], paginas_por_lote: int
) -> tuple[list[LotePlanejado], set[int]]:
    versao = trabalho.versoes["paginas"]
    total = sum(fonte.paginas for fonte in fontes)
    with trabalho.transacao() as session:
        prontas = paginas.prontas(session, trabalho.arquivo.hk_arquivo, versao)
        faltantes = set(range(1, total + 1)) - prontas
        prontas |= copiar_do_cache(session, trabalho.arquivo, versao, total, faltantes)
    lotes = [
        LotePlanejado(numero, tarefa, pendentes([tarefa], prontas))
        for numero, tarefa in enumerate(planejar(fontes, paginas_por_lote), 1)
    ]
    return lotes, prontas


def _processar_lotes(
    trabalho: Trabalho,
    fontes: list[FontePaginas],
    settings: Settings,
    limites: LimitesSandbox,
    parar: Event,
) -> Counter[str]:
    lotes, prontas = _planejar_lotes(trabalho, fontes, settings.extracao_paginas_por_lote)
    falhas: Counter[str] = Counter()
    for lote in lotes:
        if not lote.restantes:
            _gravar_lote(trabalho, lote, [], prontas, falhas)
    a_extrair = [lote for lote in lotes if lote.restantes]
    extracoes = executar_em_paralelo(
        a_extrair,
        partial(_extrair_restantes, limites=limites, retentativas=settings.max_retentativas),
        settings.extracao_lotes_por_job,
        parar,
    )
    with closing(extracoes):
        for lote, resultados in extracoes:
            motivo = resultados[-1].motivo_falha
            if motivo is not None and motivo in LIMITES_DUROS:
                raise FalhaSandboxError(motivo)
            _gravar_lote(trabalho, lote, resultados, prontas, falhas)
    return falhas


@dataclass(frozen=True)
class Extracao:
    """Resultado da extração de páginas que a indexação consome."""

    inicio: float
    falhas: Counter[str]
    diagnostico: DiagnosticoArquivo


@dataclass
class Execucao:
    """Estado compartilhado pelas etapas de uma execução do arquivo."""

    trabalho: Trabalho
    settings: Settings
    storage: ObjectStorage
    parar: Event
    relatorio: dict[str, Any]
    extracao: Extracao | None = None
    eventos_recalculados: bool = False


def _etapa_paginas(execucao: Execucao, session: Session | None) -> bool:
    trabalho, settings = execucao.trabalho, execucao.settings
    limites = LimitesSandbox(
        settings.sandbox_memoria_mb, settings.sandbox_cpu_segundos, settings.sandbox_tempo_segundos
    )
    inicio = monotonic()
    with TemporaryDirectory(
        prefix="lupa-extracao-", dir=settings.ingestao_dir_temporario
    ) as diretorio:
        fontes, diagnostico = _preparar(
            trabalho, execucao.storage, Path(diretorio), settings, limites
        )
        falhas = _processar_lotes(trabalho, fontes, settings, limites, execucao.parar)
    if execucao.parar.is_set():
        return False
    execucao.extracao = Extracao(inicio, falhas, diagnostico)
    return True


def _etapa_pecas(execucao: Execucao, session: Session | None) -> bool:
    trabalho = execucao.trabalho
    versao = trabalho.versoes["paginas"]
    with trabalho.transacao() as transacao:
        linhas = paginas.paginas_para_indice(transacao, trabalho.arquivo.hk_arquivo, versao)
        extracao = execucao.extracao
        if extracao is None:
            diagnostico = {
                "sinais": trabalho.arquivo.sinais,
                "fronteiras_origem": trabalho.arquivo.fronteiras_origem,
            }
        else:
            execucao.relatorio = relatorio_qualidade(
                linhas,
                total_paginas=extracao.diagnostico.total_paginas,
                tempo_parede_segundos=monotonic() - extracao.inicio,
                falhas=extracao.falhas,
                versao_extrator=versao,
                metadados=extracao.diagnostico.metadados_descartados,
            )
            diagnostico = extracao.diagnostico.model_dump(mode="json")
        _indexar(transacao, trabalho, linhas, diagnostico, execucao.relatorio)
    return True


def _etapa_fatos(execucao: Execucao, session: Session | None) -> bool:
    if session is None:
        raise ValueError("a etapa de fatos exige a transação final")
    execucao.relatorio["eventos"] = processar_eventos(
        session,
        execucao.trabalho.arquivo.hk_processo,
        datetime.now(UTC).date(),
        identificacao_paginas=execucao.settings.identificacao_paginas,
    )
    execucao.eventos_recalculados = True
    return True


def _etapa_catalogo(execucao: Execucao, session: Session | None) -> bool:
    if session is None:
        raise ValueError("a etapa de catálogo exige a transação final")
    if execucao.eventos_recalculados:
        return True
    execucao.relatorio["eventos"] |= atualizar_achados(
        session, execucao.trabalho.arquivo.hk_processo, datetime.now(UTC).date()
    )
    return True


Etapa = Callable[[Execucao, Session | None], bool]

ETAPAS: tuple[tuple[str, Etapa], ...] = (
    ("paginas", _etapa_paginas),
    ("pecas", _etapa_pecas),
    ("fatos", _etapa_fatos),
    ("catalogo", _etapa_catalogo),
)

ETAPAS_DA_TRANSACAO_FINAL = frozenset({"fatos", "catalogo"})


def etapas_desde(primeira: str) -> tuple[tuple[str, Etapa], ...]:
    """Devolve as etapas de `ETAPAS` a partir de `primeira`, na ordem de execução.

    Args:
        primeira: Nome da primeira etapa a refazer.

    Returns:
        As etapas de `primeira` até o fim de `ETAPAS`.
    """
    nomes = [nome for nome, _ in ETAPAS]
    return ETAPAS[nomes.index(primeira) :]


def _indexar(
    session: Session,
    trabalho: Trabalho,
    linhas: list[dict[str, Any]],
    diagnostico: dict[str, Any],
    relatorio: dict[str, Any],
) -> None:
    resultado = montar_indice(linhas, diagnostico)
    gravar_indice(session, trabalho.arquivo, linhas, resultado)
    relatorio["indice"] = {
        "fonte": resultado.fonte,
        "pecas": len(resultado.pecas),
        "versoes": trabalho.versoes["pecas"],
    }
    relatorio["divergencias_fronteira"] = resultado.divergencias


def _processar(
    trabalho: Trabalho, settings: Settings, storage: ObjectStorage, parar: Event
) -> None:
    arquivo = trabalho.arquivo
    relatorio = dict(arquivo.relatorio or {})
    agendada = relatorio.pop("reprocessar_desde", None)
    primeira = (
        (reprocessamento.primeira_etapa(arquivo, trabalho.versoes) or agendada)
        if agendada
        else "paginas"
    )
    execucao = Execucao(trabalho, settings, storage, parar, relatorio)
    etapas = etapas_desde(primeira)
    for nome, etapa in etapas:
        if nome not in ETAPAS_DA_TRANSACAO_FINAL and not etapa(execucao, None):
            return

    with trabalho.transacao() as session:
        for nome, etapa in etapas:
            if nome in ETAPAS_DA_TRANSACAO_FINAL:
                etapa(execucao, session)
        relatorio = execucao.relatorio
        relatorio["versoes_processamento"] = trabalho.versoes
        estado = EstadoJob.PARCIAL if relatorio["paginas_faltando"] else EstadoJob.CONCLUIDO
        mudar_estado(
            session,
            arquivo.hk_arquivo,
            estado,
            relatorio=relatorio,
            versao_extrator=trabalho.versoes["paginas"],
        )
        atualizar_status_processo(session, arquivo.hk_processo)
    log.info("arquivo_finalizado", arquivo_id=arquivo.id, estado=estado.value)


def processar_arquivo(
    fabrica: sessionmaker[Session],
    settings: Settings,
    storage: ObjectStorage,
    hk_arquivo: bytes,
    parar: Event,
) -> None:
    """Valida, extrai e indexa o arquivo."""
    with fabrica() as session:
        assumir_papel_aplicacao(session)
        arquivo = session.get_one(VisaoArquivo, hk_arquivo)
        session.expunge(arquivo)
    trabalho = Trabalho(fabrica, arquivo, reprocessamento.versoes_atuais())
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
