"""Recepção, lacre e estado dos arquivos pela API do gabinete cível."""

from collections.abc import Iterator
from hashlib import sha256

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from apoio_arquivos import pdf_minimo, pdf_texto, zip_por_peca
from apoio_comum import criar_processo_teste, eventos_do_banco
from lupa_intranet.api.rotas import ingestao
from lupa_intranet.auditoria.eventos import AcaoAuditoria
from lupa_pipeline.config import Settings, get_settings
from lupa_pipeline.dominio.enums import EstadoJob, MotivoQuarentena, PapelUsuario, StatusProcesso
from lupa_pipeline.dominio.gravacao import gravar_satelite
from lupa_pipeline.dominio.tabelas import sat_arquivo_ingestao, sat_processo_estado
from lupa_pipeline.dominio.visoes import VisaoArquivo, VisaoFilaIngestao
from lupa_pipeline.ingestao.repositorio import mudar_estado
from lupa_pipeline.ingestao.storage import ArmazenamentoMemoria, ObjectStorage, chave_objeto
from tests.conftest import criar_usuario_teste, logar

pytestmark = pytest.mark.integracao


@pytest.fixture
def app_ingestao(app_teste: FastAPI) -> FastAPI:
    """Aplicação com as rotas de ingestão e o storage em memória."""
    app_teste.include_router(ingestao.router)
    app_teste.state.storage = ArmazenamentoMemoria()
    return app_teste


@pytest.fixture
def cliente_envio(app_ingestao: FastAPI, engine_teste: Engine) -> Iterator[TestClient]:
    """Cliente de um assessor autenticado que pode enviar a qualquer processo (RF-PRO-03)."""
    usuario = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    with TestClient(app_ingestao, base_url="https://testserver") as cliente:
        logar(cliente, engine_teste, usuario)
        yield cliente


def _enviar(cliente: TestClient, processo: bytes, dados: bytes, nome: str) -> httpx.Response:
    return cliente.post(
        f"/processos/{processo.hex()}/arquivos",
        params={"nome": nome},
        content=dados,
        headers={"Content-Type": "application/octet-stream"},
    )


def _contar_arquivos(engine: Engine, processo: bytes) -> int:
    with Session(engine) as sessao:
        return sessao.scalar(select(func.count()).where(VisaoArquivo.hk_processo == processo)) or 0


def test_envio_de_pdf_lacra_original_e_registra_upload(
    app_ingestao: FastAPI, cliente_envio: TestClient, engine_teste: Engine
) -> None:
    """RF-ING-01 e RF-PRO-04: PDF com marca de sigilo é recebido e entra na fila do banco."""
    processo = criar_processo_teste(engine_teste)
    dados = pdf_texto(["SEGREDO DE JUSTIÇA - documento sintético"])
    resposta = _enviar(cliente_envio, processo, dados, "autos.pdf")
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    hk = bytes.fromhex(corpo["arquivo_id"])
    resumo = sha256(dados).hexdigest()
    assert len(hk) == 32
    assert corpo == {
        "arquivo_id": hk.hex(),
        "sha256": resumo,
        "tamanho_bytes": len(dados),
        "estado": "recebido",
        "duplicado": False,
        "mime": "application/pdf",
    }
    chave = chave_objeto(processo, resumo)
    storage: ObjectStorage = app_ingestao.state.storage
    assert storage.ler(chave) == dados
    with Session(engine_teste) as sessao:
        assert (
            sessao.scalar(select(VisaoFilaIngestao.id).where(VisaoFilaIngestao.hk_arquivo == hk))
            == hk.hex()
        )
    eventos = eventos_do_banco(engine_teste, processo_id=processo.hex(), acao="upload")
    assert [(e.resultado, e.objeto_id) for e in eventos] == [("ok", hk.hex())]


def test_mesmo_arquivo_duas_vezes_nao_duplica(
    app_ingestao: FastAPI, cliente_envio: TestClient, engine_teste: Engine
) -> None:
    """RF-ING-01: reenviar não grava objeto, linha de estado nem evento de upload."""
    processo = criar_processo_teste(engine_teste)
    dados = zip_por_peca(2)
    primeiro = _enviar(cliente_envio, processo, dados, "autos.zip")
    assert primeiro.status_code == 201
    corpo = primeiro.json()
    chave = chave_objeto(processo, corpo["sha256"])
    assert app_ingestao.state.storage.ler(chave) == dados
    repetido = _enviar(cliente_envio, processo, dados, "outro-nome.zip")
    assert repetido.status_code == 200
    assert repetido.json() == corpo | {"duplicado": True}
    assert app_ingestao.state.storage.ler(chave) == dados
    assert _contar_arquivos(engine_teste, processo) == 1
    with Session(engine_teste) as sessao:
        hk = bytes.fromhex(corpo["arquivo_id"])
        assert (
            sessao.scalar(select(func.count()).where(sat_arquivo_ingestao.c.hk_arquivo == hk)) == 1
        )
    assert len(eventos_do_banco(engine_teste, processo_id=processo.hex(), acao="upload")) == 1


@pytest.mark.parametrize("dados", [b"MZ\x90\x00Sintetico", zip_por_peca(1)])
def test_tipo_invalido_chega_a_triagem_do_worker(
    cliente_envio: TestClient, engine_teste: Engine, dados: bytes
) -> None:
    """RF-ING-02: um arquivo de tipo não aceito entra na fila para receber motivo de quarentena."""
    processo = criar_processo_teste(engine_teste)
    resposta = _enviar(cliente_envio, processo, dados, "autos.pdf")
    assert resposta.status_code == 201
    assert (resposta.json()["estado"], resposta.json()["mime"]) == (
        "recebido",
        "application/octet-stream",
    )


@pytest.mark.parametrize(("dados", "status"), [(b"", 422), (pdf_minimo(), 413)])
def test_recusa_sem_objeto_tem_evento_negado(
    app_ingestao: FastAPI,
    cliente_envio: TestClient,
    engine_teste: Engine,
    settings_ficticias: Settings,
    dados: bytes,
    status: int,
) -> None:
    """RF-ING-01: arquivo vazio ou acima do limite não grava arquivo e registra a recusa."""
    pequeno = settings_ficticias.model_copy(update={"upload_limite_bytes": 100})
    app_ingestao.dependency_overrides[get_settings] = lambda: pequeno
    processo = criar_processo_teste(engine_teste)
    assert _enviar(cliente_envio, processo, dados, "autos.pdf").status_code == status
    assert _contar_arquivos(engine_teste, processo) == 0
    assert app_ingestao.state.storage.listar(f"processo/{processo.hex()}/") == []
    eventos = eventos_do_banco(engine_teste, processo_id=processo.hex(), acao="upload")
    assert [e.resultado for e in eventos] == ["negado"]


def test_envio_recusa_processo_descartado_e_inexistente(
    cliente_envio: TestClient, engine_teste: Engine
) -> None:
    """RF-PRO-05 e RF-ING-01: 409 após o descarte, 404 para identificador inexistente."""
    processo = criar_processo_teste(engine_teste)
    with Session(engine_teste) as sessao, sessao.begin():
        gravar_satelite(
            sessao,
            sat_processo_estado,
            processo,
            {"status": StatusProcesso.DESCARTADO.value},
            "teste",
        )
    assert _enviar(cliente_envio, processo, pdf_minimo(), "autos.pdf").status_code == 409
    assert _enviar(cliente_envio, bytes(32), pdf_minimo(), "autos.pdf").status_code == 404
    assert cliente_envio.get(f"/processos/{processo.hex()}").status_code == 404
    assert _contar_arquivos(engine_teste, processo) == 0


def test_relatorio_mostra_paginas_faltantes_e_quarentena_mostra_motivo(
    cliente_envio: TestClient, engine_teste: Engine
) -> None:
    """RF-ING-06: o assessor consulta páginas faltantes e motivo de quarentena do seu arquivo."""
    processo = criar_processo_teste(engine_teste)
    outro = criar_processo_teste(engine_teste)
    resposta = _enviar(cliente_envio, processo, pdf_minimo(3), "autos.pdf")
    assert resposta.status_code == 201
    hk = bytes.fromhex(resposta.json()["arquivo_id"])
    segundo = _enviar(cliente_envio, processo, pdf_minimo(1), "anexo.pdf")
    hk_senha = bytes.fromhex(segundo.json()["arquivo_id"])
    with Session(engine_teste) as sessao, sessao.begin():
        mudar_estado(sessao, hk, EstadoJob.VALIDADO, total_paginas=3)
        mudar_estado(sessao, hk, EstadoJob.EM_EXTRACAO)
        mudar_estado(sessao, hk, EstadoJob.PARCIAL, relatorio={"paginas_faltando_lista": [2]})
        mudar_estado(
            sessao, hk_senha, EstadoJob.QUARENTENA, motivo_quarentena=MotivoQuarentena.SENHA
        )
    base = f"/processos/{processo.hex()}/arquivos"
    arquivos = {a["arquivo_id"]: a for a in cliente_envio.get(base).json()["arquivos"]}
    assert arquivos[hk_senha.hex()]["motivo_quarentena"] == "senha"
    assert arquivos[hk.hex()]["relatorio"]["paginas_faltando_lista"] == [2]
    relatorio = cliente_envio.get(f"{base}/{hk.hex()}/relatorio")
    assert relatorio.status_code == 200
    assert relatorio.json()["estado"] == "parcial"
    assert relatorio.json()["relatorio"]["paginas_faltando_lista"] == [2]
    for recurso in ("relatorio", "diagnostico", "alertas"):
        caminho = f"/processos/{outro.hex()}/arquivos/{hk.hex()}/{recurso}"
        assert cliente_envio.get(caminho).status_code == 404


def test_falha_ao_auditar_desfaz_upload_e_reenvio_recupera_objeto(
    app_ingestao: FastAPI, engine_teste: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RF-ING-01 e RF-AUD-01: falha ao auditar resulta em 500 sem arquivo visível, com retry."""
    processo = criar_processo_teste(engine_teste)
    usuario = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    dados = pdf_minimo()
    chave = chave_objeto(processo, sha256(dados).hexdigest())

    def falhar(*args: object, **kwargs: object) -> None:
        assert AcaoAuditoria.UPLOAD in args
        raise RuntimeError("falha sintética da auditoria")

    with TestClient(
        app_ingestao, base_url="https://testserver", raise_server_exceptions=False
    ) as cliente:
        logar(cliente, engine_teste, usuario)
        with monkeypatch.context() as ajuste:
            ajuste.setattr(ingestao, "auditar", falhar)
            assert _enviar(cliente, processo, dados, "autos.pdf").status_code == 500
        assert _contar_arquivos(engine_teste, processo) == 0
        assert eventos_do_banco(engine_teste, processo_id=processo.hex(), acao="upload") == []
        storage: ObjectStorage = app_ingestao.state.storage
        assert storage.ler(chave) == dados
        assert _enviar(cliente, processo, dados, "autos.pdf").status_code == 201
        assert storage.ler(chave) == dados
