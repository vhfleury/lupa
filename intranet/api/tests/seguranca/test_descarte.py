"""Descarte atômico e retomada da limpeza dos objetos sintéticos (RF-PRO-05)."""

import hashlib
import io
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from apoio_comum import UsuarioTeste, criar_pagina, criar_processo_teste, eventos_do_banco
from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.enums import PapelUsuario
from lupa_pipeline.dominio.tabelas import (
    hub_pagina,
    link_arquivo_pagina,
    sat_pagina_extracao,
    sat_pagina_saneamento,
)
from lupa_pipeline.dominio.visoes import VisaoProcesso
from lupa_pipeline.ingestao.renderizacao import chave_cache
from lupa_pipeline.ingestao.storage import (
    ArmazenamentoS3,
    StorageCifrado,
    chave_objeto,
    criar_cliente_s3,
)
from lupa_pipeline.seguranca.contexto import ChaveIndisponivelError, dek_de
from tests.conftest import criar_usuario_teste, logar

pytestmark = pytest.mark.integracao


@pytest.fixture
def storage_isolado(app_teste: FastAPI) -> Iterator[StorageCifrado]:
    """RF-PRO-05: MinIO cifrado em bucket exclusivo do teste."""
    s3 = criar_cliente_s3(Settings())
    bucket = "lupa-teste-descarte-" + uuid4().hex
    s3.create_bucket(Bucket=bucket)
    storage = StorageCifrado(ArmazenamentoS3(s3, bucket))
    app_teste.state.storage = storage
    try:
        yield storage
    finally:
        for chave in storage.listar(""):
            storage.apagar(chave)
        s3.delete_bucket(Bucket=bucket)
        s3.close()


@pytest.fixture
def desembargador(cliente: TestClient, engine_teste: Engine) -> UsuarioTeste:
    """RF-PRO-05: desembargador autenticado."""
    ator = criar_usuario_teste(engine_teste, PapelUsuario.DESEMBARGADOR)
    logar(cliente, engine_teste, ator)
    return ator


def test_descarte_preserva_hubs_links_auditoria_e_conteudo_dos_outros_processos(
    cliente: TestClient,
    engine_teste: Engine,
    desembargador: UsuarioTeste,
    storage_isolado: StorageCifrado,
) -> None:
    """RF-PRO-05: o tombstone preserva as relações e apaga a DEK, satélites, originais e cache."""
    hk = criar_processo_teste(engine_teste, desembargador)
    outro = criar_processo_teste(engine_teste, desembargador)
    with Session(engine_teste) as sessao, sessao.begin():
        pagina = criar_pagina(sessao, hk)
        chave = sessao.get_one(VisaoProcesso, hk).chave_dados_cifrada
        assert chave is not None
    original = chave_objeto(hk, "1" * 64)
    cache = chave_cache(original, 1, 2.0)
    vizinho = chave_objeto(outro, "1" * 64)
    for objeto in (original, cache, vizinho):
        storage_isolado.gravar(objeto, io.BytesIO(b"%PDF sintetico"))
    assert storage_isolado.interno.ler(original).startswith(b"LUPAOBJ")
    assert cliente.get(f"/processos/{hk.hex()}").status_code == 200
    rota = f"/processos/{hk.hex()}/descartar"
    resposta = cliente.post(rota)
    assert resposta.status_code == 200
    assert resposta.json() == {
        "processo_id": hk.hex(),
        "status": "descartado",
        "objetos_apagados": 2,
    }
    assert storage_isolado.listar("") == [vizinho]
    assert storage_isolado.ler(vizinho) == b"%PDF sintetico"
    with Session(engine_teste) as sessao:
        estado = sessao.get_one(VisaoProcesso, hk)
        assert (
            estado.status == "descartado" and estado.chave_dados_cifrada is None and estado.classe
        )
        for tabela in (sat_pagina_extracao, sat_pagina_saneamento):
            assert sessao.scalar(select(func.count()).where(tabela.c.hk_pagina == pagina)) == 0
        for tabela in (hub_pagina, link_arquivo_pagina):
            assert sessao.scalar(select(func.count()).where(tabela.c.hk_pagina == pagina)) == 1
    with pytest.raises(ChaveIndisponivelError):
        dek_de(hk)
    assert cliente.get(f"/processos/{hk.hex()}").status_code == 404
    eventos = eventos_do_banco(engine_teste, processo_id=hk.hex())
    assert {e.acao for e in eventos} >= {"processo_aberto", "processo_descartado"}
    assert [e.objeto_id for e in eventos if e.acao == "processo_descartado"] == [
        hashlib.sha256(chave.encode()).hexdigest()
    ]
    assert cliente.post(rota).json()["objetos_apagados"] == 0
    assert len(eventos_do_banco(engine_teste, hk_processo=hk, acao="processo_descartado")) == 1


def test_assessor_nao_descarta_e_processo_inexistente_retorna_404(
    cliente: TestClient, app_teste: FastAPI, engine_teste: Engine, desembargador: UsuarioTeste
) -> None:
    """RF-PRO-05: somente o desembargador descarta processos existentes."""
    hk = criar_processo_teste(engine_teste)
    outro = TestClient(app_teste, base_url="https://testserver")
    logar(outro, engine_teste, criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR))
    assert outro.post(f"/processos/{hk.hex()}/descartar").status_code == 403
    assert cliente.post(f"/processos/{'0' * 64}/descartar").status_code == 404
    with Session(engine_teste) as sessao:
        assert sessao.get_one(VisaoProcesso, hk).chave_dados_cifrada is not None


def test_falha_do_storage_registra_pendencia_e_repeticao_conclui(
    cliente: TestClient,
    engine_teste: Engine,
    desembargador: UsuarioTeste,
    storage_isolado: StorageCifrado,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RF-PRO-05: falha após o commit mantém conteúdo indisponível e permite retentar limpeza."""
    hk = criar_processo_teste(engine_teste)
    original = chave_objeto(hk, "1" * 64)
    cache = chave_cache(original, 1, 2.0)
    for objeto in (original, cache):
        storage_isolado.gravar(objeto, io.BytesIO(b"lote sintetico"))
    apagar = storage_isolado.apagar

    def falhar(chave: str) -> None:
        with Session(engine_teste) as sessao:
            assert sessao.get_one(VisaoProcesso, hk).chave_dados_cifrada is None
        if chave == cache:
            raise OSError("storage indisponível")
        apagar(chave)

    rota = f"/processos/{hk.hex()}/descartar"
    with monkeypatch.context() as patch:
        patch.setattr(storage_isolado, "apagar", falhar)
        assert cliente.post(rota).status_code == 503
    pendentes = eventos_do_banco(engine_teste, hk_processo=hk, acao="descarte_objetos_pendente")
    assert [e.resultado for e in pendentes] == ["falha"]
    assert storage_isolado.listar("") == [cache]
    assert cliente.post(rota).json()["objetos_apagados"] == 1
    assert storage_isolado.listar("") == []
