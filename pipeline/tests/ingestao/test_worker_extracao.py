"""Testes do worker na extração (4C.8 a 4C.10): gravação, idempotência, retry e justiça."""

from collections.abc import Callable
from dataclasses import replace
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from apoio_arquivos import (
    pdf_minimo,
    zip_por_peca,
)
from apoio_ingestao import AutosSinteticos, JobSemeado, Relogio, SemearJob
from lupa_pipeline.dominio.enums import (
    CenarioArquivo,
    EstadoJob,
    MotivoFalha,
    StatusProcesso,
    TipoPagina,
)
from lupa_pipeline.dominio.tabelas import (
    DiagnosticoArquivoTabela,
    JobIngestaoTabela,
    PaginaTabela,
    ProcessoTabela,
)
from lupa_pipeline.ingestao import repositorio, worker
from lupa_pipeline.ingestao.extrator_paginas import VERSAO_EXTRATOR
from lupa_pipeline.ingestao.fila import FilaMemoria
from lupa_pipeline.ingestao.sandbox import LimitesSandbox, ResultadoSandbox, executar
from lupa_pipeline.ingestao.worker import Dependencias, processar_job, sessao_sistema, varrer
from lupa_pipeline.sinteticos.gabarito import Cenario

pytestmark = pytest.mark.integracao

Executor = Callable[[str, list[str], LimitesSandbox], ResultadoSandbox]


def _processar(deps: Dependencias, job: JobSemeado) -> EstadoJob | None:
    return processar_job(deps, job.job_id, job.processo.gabinete_id)


def _job(fabrica: sessionmaker[Session], job_id: UUID) -> JobIngestaoTabela:
    with sessao_sistema(fabrica) as s:
        linha = s.get_one(JobIngestaoTabela, job_id)
        s.expunge(linha)
        return linha


def _paginas(fabrica: sessionmaker[Session], arquivo_id: UUID) -> list[PaginaTabela]:
    with sessao_sistema(fabrica) as s:
        linhas = list(
            s.scalars(
                select(PaginaTabela)
                .where(PaginaTabela.arquivo_id == arquivo_id)
                .order_by(PaginaTabela.numero)
            )
        )
        s.expunge_all()
        return linhas


def _status_processo(fabrica: sessionmaker[Session], processo_id: UUID) -> str:
    with sessao_sistema(fabrica) as s:
        return s.get_one(ProcessoTabela, processo_id).status


def _contando(chamadas: list[list[str]], base: Executor = executar) -> Executor:
    def _executor(modulo: str, argumentos: list[str], limites: LimitesSandbox) -> ResultadoSandbox:
        chamadas.append(argumentos)
        return base(modulo, argumentos, limites)

    return _executor


def _falhando(motivo: MotivoFalha) -> Executor:
    def _executor(*_args: Any) -> ResultadoSandbox:
        return ResultadoSandbox(motivo_falha=motivo)

    return _executor


def test_pdf_sintetico_com_indice_vai_a_concluido_com_paginas_diagnostico_e_relatorio(
    deps_extracao: Dependencias, semear_job: SemearJob, autos_sinteticos: AutosSinteticos
) -> None:
    """Fluxo completo: diagnóstico com fronteiras, páginas de todos os tipos, relatório."""
    dados = autos_sinteticos.arquivos[Cenario.PDF_INDICE].read_bytes()
    gabarito = autos_sinteticos.gabaritos[Cenario.PDF_INDICE]
    job = semear_job(dados, "autos.pdf")
    assert _processar(deps_extracao, job) is EstadoJob.CONCLUIDO
    linha = _job(deps_extracao.fabrica, job.job_id)
    total = len(gabarito.arquivos[0].folhas)
    assert linha.relatorio is not None
    assert linha.relatorio["paginas_extraidas"] == total
    assert linha.relatorio["paginas_faltando"] == 0
    assert linha.relatorio["abstidas"] > 0
    assert linha.versao_extrator == VERSAO_EXTRATOR
    paginas = _paginas(deps_extracao.fabrica, job.arquivo_id)
    assert [p.numero for p in paginas] == list(range(1, total + 1))
    assert {p.tipo for p in paginas} == {t.value for t in TipoPagina}
    assert all(p.sinais and p.extracao["rota"] for p in paginas)
    assert any(p.flags.get("texto_oculto") and p.trechos_ocultos for p in paginas)
    saneamento = linha.relatorio["saneamento"]
    assert saneamento["paginas_por_flag"]["texto_oculto"] >= 1
    assert saneamento["versoes"]["padroes_instrucao"]
    assert all(p.texto_normalizado is not None for p in paginas)
    with sessao_sistema(deps_extracao.fabrica) as s:
        diagnostico = repositorio.obter_diagnostico(s, job.arquivo_id)
    assert diagnostico is not None
    assert diagnostico.cenario is CenarioArquivo.PDF_COM_BOOKMARKS_E_INDICE
    assert diagnostico.cenario.value == gabarito.processo.diagnostico_esperado
    assert _status_processo(deps_extracao.fabrica, job.processo.processo_id) == (
        StatusProcesso.PRONTO.value
    )


def test_zip_grava_paginas_com_a_entrada_de_origem(
    deps_extracao: Dependencias, semear_job: SemearJob
) -> None:
    """Numeração contínua no arquivo e posição dentro de cada entrada."""
    job = semear_job(zip_por_peca(3), "autos.zip")
    assert _processar(deps_extracao, job) is EstadoJob.CONCLUIDO
    paginas = _paginas(deps_extracao.fabrica, job.arquivo_id)
    assert [(p.numero, p.origem_arquivo, p.pagina_origem) for p in paginas] == [
        (1, "01-peca.pdf", 1),
        (2, "02-peca.pdf", 1),
        (3, "03-peca.pdf", 1),
    ]
    with sessao_sistema(deps_extracao.fabrica) as s:
        linha = s.scalar(
            select(DiagnosticoArquivoTabela).where(
                DiagnosticoArquivoTabela.arquivo_id == job.arquivo_id
            )
        )
        assert linha is not None
        assert linha.cenario == CenarioArquivo.ZIP_POR_PECA.value
        assert len(linha.fronteiras_origem) == 3


def _reabrir_extracao(fabrica: sessionmaker[Session], job_id: UUID) -> None:
    with sessao_sistema(fabrica) as s:
        s.execute(
            update(JobIngestaoTabela)
            .where(JobIngestaoTabela.id == job_id)
            .values(estado=EstadoJob.EM_EXTRACAO.value, finalizado_em=None, relatorio={})
        )


def test_reprocessar_nao_duplica_e_nova_versao_do_extrator_refaz(
    deps_extracao: Dependencias, semear_job: SemearJob, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mesma versão: nenhum lote roda de novo; versão nova: todas as páginas refeitas."""
    job = semear_job(pdf_minimo(5), "autos.pdf")
    assert _processar(deps_extracao, job) is EstadoJob.CONCLUIDO
    antes = {
        p.numero: (p.id, p.hash_texto) for p in _paginas(deps_extracao.fabrica, job.arquivo_id)
    }

    chamadas: list[list[str]] = []
    contando = replace(deps_extracao, executor=_contando(chamadas))
    _reabrir_extracao(deps_extracao.fabrica, job.job_id)
    assert _processar(contando, job) is EstadoJob.CONCLUIDO
    assert chamadas == []
    depois = {
        p.numero: (p.id, p.hash_texto) for p in _paginas(deps_extracao.fabrica, job.arquivo_id)
    }
    assert depois == antes

    monkeypatch.setattr(worker, "VERSAO_EXTRATOR", "versao-nova")
    _reabrir_extracao(deps_extracao.fabrica, job.job_id)
    assert _processar(contando, job) is EstadoJob.CONCLUIDO
    assert chamadas
    paginas = _paginas(deps_extracao.fabrica, job.arquivo_id)
    assert len(paginas) == 5
    assert {p.versao_extrator for p in paginas} == {"versao-nova"}
    assert {p.numero: p.id for p in paginas} == {n: v[0] for n, v in antes.items()}


def test_lote_que_falha_deixa_job_parcial_com_paginas_faltando(
    deps_extracao: Dependencias, semear_job: SemearJob
) -> None:
    """Um lote morto pelo limite: `parcial`, relatório diz quais páginas faltam."""

    def _primeiro_falha(modulo: str, argumentos: list[str], limites: LimitesSandbox) -> Any:
        if argumentos[1] == "1":
            return ResultadoSandbox(motivo_falha=MotivoFalha.LIMITE_CPU)
        return executar(modulo, argumentos, limites)

    job = semear_job(pdf_minimo(6), "autos.pdf")
    assert _processar(replace(deps_extracao, executor=_primeiro_falha), job) is EstadoJob.PARCIAL
    linha = _job(deps_extracao.fabrica, job.job_id)
    assert linha.relatorio is not None
    assert linha.relatorio["paginas_faltando_lista"] == [1, 2, 3, 4]
    assert linha.relatorio["falhas_por_motivo"] == {"limite_cpu": 4}
    assert _status_processo(deps_extracao.fabrica, job.processo.processo_id) == "pronto"


def test_falha_retentavel_volta_a_recebido_duas_vezes_e_depois_falha(
    deps_extracao: Dependencias, semear_job: SemearJob
) -> None:
    """`tempo_esgotado`: duas novas tentativas automáticas, depois `falho` definitivo."""
    fila = FilaMemoria()
    deps = replace(deps_extracao, executor=_falhando(MotivoFalha.TEMPO_ESGOTADO), fila=fila)
    job = semear_job(pdf_minimo(2), "autos.pdf")
    for _ in range(2):
        assert _processar(deps, job) is EstadoJob.FALHO
        assert _job(deps.fabrica, job.job_id).estado == EstadoJob.RECEBIDO.value
    assert len(fila.pedidos) == 2
    assert _processar(deps, job) is EstadoJob.FALHO
    linha = _job(deps.fabrica, job.job_id)
    assert (linha.estado, linha.motivo_falha) == ("falho", "tempo_esgotado")
    assert _processar(deps, job) is None


def test_falha_por_memoria_nunca_e_retentada(
    deps_extracao: Dependencias, semear_job: SemearJob
) -> None:
    """`limite_memoria` vai direto a `falho`."""
    deps = replace(deps_extracao, executor=_falhando(MotivoFalha.LIMITE_MEMORIA))
    job = semear_job(pdf_minimo(2), "autos.pdf")
    assert _processar(deps, job) is EstadoJob.FALHO
    linha = _job(deps.fabrica, job.job_id)
    assert (linha.estado, linha.motivo_falha) == ("falho", "limite_memoria")


def test_ocr_indisponivel_em_todas_as_paginas_falha_como_erro_de_parser(
    deps_extracao: Dependencias, semear_job: SemearJob
) -> None:
    """Páginas com `erro` no OCR contam como faltando; nenhuma gravada vira `erro_parser`."""

    def _sem_ocr(_modulo: str, argumentos: list[str], _limites: LimitesSandbox) -> Any:
        paginas = [{"numero": n, "erro": "ocr"} for n in range(int(argumentos[1]), 3)]
        return ResultadoSandbox(dados={"ok": True, "paginas": paginas})

    deps = replace(deps_extracao, executor=_sem_ocr, max_retentativas=0)
    job = semear_job(pdf_minimo(2), "autos.pdf")
    assert _processar(deps, job) is EstadoJob.FALHO
    linha = _job(deps.fabrica, job.job_id)
    assert linha.motivo_falha == MotivoFalha.ERRO_PARSER.value
    assert linha.relatorio is not None
    assert linha.relatorio["falhas_por_motivo"] == {"erro_ocr": 2}


def _rodar_fila(deps: Dependencias, fila: FilaMemoria) -> list[UUID]:
    concluidos: list[UUID] = []
    while fila.pedidos:
        job_id, gabinete_id = fila.pedidos.pop(0)
        if processar_job(deps, job_id, gabinete_id) is EstadoJob.CONCLUIDO:
            concluidos.append(job_id)
    return concluidos


def test_job_grande_cede_a_vez_e_job_pequeno_de_outro_gabinete_termina_antes(
    deps_extracao: Dependencias, semear_job: SemearJob
) -> None:
    """Round-robin por fatias: o pequeno, enfileirado depois, conclui antes do grande."""
    fila = FilaMemoria()
    deps = replace(deps_extracao, fila=fila, fatia_paginas=4)
    grande = semear_job(pdf_minimo(20), "grande.pdf")
    pequeno = semear_job(pdf_minimo(2), "pequeno.pdf")
    assert grande.processo.gabinete_id != pequeno.processo.gabinete_id
    fila.enfileirar(grande.job_id, grande.processo.gabinete_id)
    fila.enfileirar(pequeno.job_id, pequeno.processo.gabinete_id)
    assert _rodar_fila(deps, fila) == [pequeno.job_id, grande.job_id]
    linha = _job(deps.fabrica, grande.job_id)
    assert linha.tentativas == 1
    assert linha.relatorio is not None
    assert linha.relatorio["paginas_extraidas"] == 20
    assert linha.relatorio["tempo"]["parede_segundos"] > 0


def test_varredor_recupera_job_em_extracao_com_lease_vencido(
    deps_extracao: Dependencias, semear_job: SemearJob, relogio: Relogio
) -> None:
    """Worker morto na extração: o varredor reenfileira e outro worker conclui."""
    job = semear_job(pdf_minimo(2), "autos.pdf")
    with sessao_sistema(deps_extracao.fabrica) as s:
        s.execute(
            update(JobIngestaoTabela)
            .where(JobIngestaoTabela.id == job.job_id)
            .values(estado="validado", lease_expira_em=relogio.agora, lease_dono="morto")
        )
    relogio.avancar(1)
    fila = FilaMemoria()
    assert varrer(deps_extracao, fila) >= 1
    assert (job.job_id, job.processo.gabinete_id) in fila.pedidos


def test_worker_da_fundacao_nao_extrai_job_validado(
    deps: Dependencias, deps_extracao: Dependencias, semear_job: SemearJob
) -> None:
    """Sem extração ligada, `validado` é ponto final; com ela, o job segue."""
    job = semear_job(pdf_minimo(1), "autos.pdf")
    assert _processar(deps, job) is EstadoJob.VALIDADO
    assert _processar(deps, job) is None
    assert _processar(deps_extracao, job) is EstadoJob.CONCLUIDO
    with sessao_sistema(deps.fabrica) as s:
        quantidade = s.scalar(
            select(func.count())
            .select_from(PaginaTabela)
            .where(PaginaTabela.arquivo_id == job.arquivo_id)
        )
    assert quantidade == 1
