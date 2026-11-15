"""Reprocessamento por mudança de versão no ponto de entrada do worker (RF-ING-08)."""

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from apoio_arquivos import pdf_texto
from apoio_comum import banco_vazio, migrar
from apoio_ingestao import PararAoEsvaziar, lacrar_bytes, semear_processo
from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.correcoes import corrigir_fato, obter_fato
from lupa_pipeline.dominio.enums import StatusFato, TipoFato
from lupa_pipeline.dominio.esquemas import Evidencia
from lupa_pipeline.dominio.gravacao import gravar_satelite
from lupa_pipeline.dominio.repositorios import listar_fatos_por_processo
from lupa_pipeline.dominio.tabelas import sat_fato_anotacao
from lupa_pipeline.dominio.visoes import VisaoAnotacao, VisaoArquivo, VisaoPagina
from lupa_pipeline.ingestao import indice, processamento
from lupa_pipeline.ingestao.classificacao import classificar_tipo
from lupa_pipeline.ingestao.eventos import recurso
from lupa_pipeline.ingestao.extracao import executar_tarefa
from lupa_pipeline.ingestao.storage import StorageCifrado
from lupa_pipeline.ingestao.worker import executar_worker
from lupa_pipeline.validacoes import motor
from lupa_pipeline.validacoes.catalogo import validacoes_de

pytestmark = pytest.mark.integracao


@pytest.fixture
def banco_reprocessamento() -> Iterator[Engine]:
    """Isola os reinícios do worker de quaisquer arquivos pendentes de outros testes."""
    with banco_vazio("reprocessamento") as engine:
        migrar(engine, "head")
        yield engine


def test_reinicio_executa_so_as_etapas_afetadas_e_preserva_a_revisao(
    banco_reprocessamento: Engine,
    settings_ficticias: Settings,
    storage_memoria: StorageCifrado,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """RF-ING-08, RF-FAT-03. Versões alteradas retomam a fila e preservam correção e nota."""
    engine = banco_reprocessamento
    processo = semear_processo(engine)
    hk = processo.hk_processo
    caminho = tmp_path / "apelacao.pdf"
    caminho.write_bytes(
        pdf_texto(
            [
                "APELAÇÃO\nRecorrente: Ana Sintética\nRecurso interposto em 10/08/2026.\n"
                "Data retificada pelo gabinete em 11/08/2026."
            ]
        )
    )
    arquivo = lacrar_bytes(engine, storage_memoria, processo, caminho).hk_arquivo
    etapas = {
        "paginas": Mock(wraps=executar_tarefa),
        "pecas": Mock(wraps=classificar_tipo),
        "fatos": Mock(wraps=recurso.extrair),
        "catalogo": Mock(wraps=validacoes_de),
    }
    monkeypatch.setattr(processamento, "executar_tarefa", etapas["paginas"])
    monkeypatch.setattr(indice, "classificar_tipo", etapas["pecas"])
    monkeypatch.setattr(recurso, "extrair", etapas["fatos"])
    monkeypatch.setattr(motor, "validacoes_de", etapas["catalogo"])

    def reiniciar() -> set[str]:
        for etapa in etapas.values():
            etapa.reset_mock()
        assert (
            executar_worker(
                engine,
                settings_ficticias,
                storage_memoria,
                PararAoEsvaziar(),
                processamento.processar_arquivo,
            )
            == 0
        )
        return {nome for nome, etapa in etapas.items() if etapa.called}

    assert reiniciar() == set(etapas)
    with Session(engine) as s, s.begin():
        atual = s.get_one(VisaoArquivo, arquivo)
        assert atual.estado == "concluido"
        (fato,) = [
            f for f in listar_fatos_por_processo(s, hk) if f.tipo == TipoFato.DATA_INTERPOSICAO
        ]
        pagina = s.scalars(select(VisaoPagina).where(VisaoPagina.hk_arquivo == arquivo)).one()
        assert pagina.texto and fato.valor == "2026-08-10"
        trecho = "11/08/2026"
        inicio = pagina.texto.index(trecho)
        evidencia = Evidencia(
            id="0" * 64, pagina_id=pagina.id, trecho=trecho, inicio=inicio, fim=inicio + len(trecho)
        )
        corrigir_fato(s, fato, StatusFato.CORRIGIDO, processo.hk_usuario, "2026-08-11", evidencia)
        gravar_satelite(
            s,
            sat_fato_anotacao,
            bytes.fromhex(fato.id),
            {"texto": "Data conferida no original", "hk_usuario": processo.hk_usuario},
            "teste",
        )
        versoes = dict(atual.relatorio["versoes_processamento"])

    monkeypatch.setattr("lupa_pipeline.ingestao.reprocessamento.versoes_atuais", lambda: versoes)
    assert reiniciar() == set()
    for chave, afetadas in [
        ("catalogo", {"catalogo"}),
        ("fatos", {"fatos", "catalogo"}),
        ("pecas", {"pecas", "fatos", "catalogo"}),
        ("paginas", set(etapas)),
    ]:
        versoes[chave] = (
            versoes[chave] | {"classificacao": "teste-v2"} if chave == "pecas" else "teste-v2"
        )
        assert reiniciar() == afetadas
        with Session(engine) as s:
            atual = s.get_one(VisaoArquivo, arquivo)
            assert atual.estado == "concluido"
            assert atual.relatorio["versoes_processamento"] == versoes
            assert s.scalar(select(VisaoPagina.versao_extrator)) == versoes["paginas"]
            revisado = obter_fato(s, hk, fato.id)
            assert revisado and (revisado.valor, revisado.status) == (
                "2026-08-11",
                StatusFato.CORRIGIDO,
            )
            assert [e.trecho for e in revisado.evidencias] == [trecho]
            nota = s.scalars(select(VisaoAnotacao).where(VisaoAnotacao.hk_processo == hk)).one()
            assert (nota.alvo_id, nota.texto, nota.hk_usuario) == (
                fato.id,
                "Data conferida no original",
                processo.hk_usuario,
            )
        assert reiniciar() == set()
