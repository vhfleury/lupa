"""Histórico de estados de ingestão e situação do processo no Data Vault."""

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apoio_arquivos import pdf_com_senha, pdf_minimo
from apoio_ingestao import SemearArquivo
from lupa_pipeline.dominio.enums import EstadoJob, MotivoQuarentena, StatusProcesso
from lupa_pipeline.dominio.gravacao import gravar_satelite
from lupa_pipeline.dominio.tabelas import sat_arquivo_ingestao, sat_processo_estado
from lupa_pipeline.dominio.visoes import VisaoFilaIngestao, VisaoProcesso
from lupa_pipeline.ingestao import repositorio
from lupa_pipeline.ingestao.estados import TransicaoInvalidaError

pytestmark = pytest.mark.integracao


def test_quarentena_final_sai_da_fila_e_preserva_versoes(
    semear_arquivo: SemearArquivo, engine_teste: Engine
) -> None:
    """RF-ING-02 e RF-ING-06: histórico mantém motivo e estado finais sem nova tentativa."""
    arquivo = semear_arquivo(pdf_com_senha())
    hk = arquivo.hk_arquivo
    with Session(engine_teste) as sessao, sessao.begin():
        with pytest.raises(TransicaoInvalidaError):
            repositorio.mudar_estado(sessao, hk, EstadoJob.CONCLUIDO)
        repositorio.mudar_estado(sessao, hk, EstadoJob.RECEBIDO, tentativas=1)
        linha = repositorio.mudar_estado(
            sessao, hk, EstadoJob.QUARENTENA, motivo_quarentena=MotivoQuarentena.SENHA
        )
        assert (linha.estado, linha.motivo_quarentena, linha.tentativas) == (
            "quarentena",
            "senha",
            1,
        )
        assert sessao.get(VisaoFilaIngestao, hk) is None
        assert (
            sessao.scalar(select(func.count()).where(sat_arquivo_ingestao.c.hk_arquivo == hk)) == 3
        )
        with pytest.raises(TransicaoInvalidaError):
            repositorio.mudar_estado(sessao, hk, EstadoJob.RECEBIDO)


def test_banco_exige_motivo_em_quarentena(
    semear_arquivo: SemearArquivo, engine_teste: Engine
) -> None:
    """RF-ING-02: o banco recusa linha de quarentena sem motivo e conserva o estado anterior."""
    hk = semear_arquivo(pdf_minimo()).hk_arquivo
    with pytest.raises(IntegrityError), Session(engine_teste) as sessao, sessao.begin():
        repositorio.mudar_estado(sessao, hk, EstadoJob.QUARENTENA)
    with Session(engine_teste) as sessao:
        assert repositorio.ler_arquivo(sessao, hk).estado == "recebido"


def test_status_do_processo_acompanha_ingestao_e_pronto(
    semear_arquivo: SemearArquivo, engine_teste: Engine
) -> None:
    """RF-ING-06 e A5.11: estado corrente muda por inserção e permanece estável na repetição."""
    arquivo = semear_arquivo(pdf_minimo())
    hk, processo = arquivo.hk_arquivo, arquivo.processo.hk_processo
    with Session(engine_teste) as sessao, sessao.begin():
        assert repositorio.atualizar_status_processo(sessao, processo) is StatusProcesso.EM_INGESTAO
        assert repositorio.atualizar_status_processo(sessao, processo) is None
        repositorio.mudar_estado(sessao, hk, EstadoJob.VALIDADO)
        repositorio.mudar_estado(sessao, hk, EstadoJob.EM_EXTRACAO)
        repositorio.mudar_estado(sessao, hk, EstadoJob.CONCLUIDO)
        assert repositorio.atualizar_status_processo(sessao, processo) is StatusProcesso.PRONTO
        assert (
            sessao.scalar(select(func.count()).where(sat_processo_estado.c.hk_processo == processo))
            == 3
        )


@pytest.mark.parametrize(
    "status", [StatusProcesso.EM_REVISAO, StatusProcesso.ARQUIVADO, StatusProcesso.DESCARTADO]
)
def test_ingestao_preserva_decisao_sobre_status_do_processo(
    semear_arquivo: SemearArquivo, engine_teste: Engine, status: StatusProcesso
) -> None:
    """RF-ING-06, RF-CHA-08 e RF-PRO-05: ingestão não reabre processo em estado protegido."""
    processo = semear_arquivo(pdf_minimo()).processo.hk_processo
    with Session(engine_teste) as sessao, sessao.begin():
        gravar_satelite(sessao, sat_processo_estado, processo, {"status": status.value}, "teste")
        assert repositorio.atualizar_status_processo(sessao, processo) is None
        assert (
            sessao.scalar(select(VisaoProcesso.status).where(VisaoProcesso.hk_processo == processo))
            == status.value
        )


def test_arquivo_ausente_e_mudanca_desconhecida_sao_recusados(engine_teste: Engine) -> None:
    """RF-ING-06: consulta inexistente e tentativa de alterar atributo fora do satélite falham."""
    with Session(engine_teste) as sessao, sessao.begin():
        with pytest.raises(repositorio.ArquivoNaoEncontradoError):
            repositorio.ler_arquivo(sessao, bytes(32))
        with pytest.raises(ValueError, match="atributos desconhecidos"):
            repositorio.mudar_estado(sessao, bytes(32), EstadoJob.RECEBIDO, campo_invalido=1)
