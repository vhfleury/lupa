"""Ingestão de autos cíveis pelo HTTP, fila PostgreSQL e MinIO com chave por processo."""

import json
from pathlib import Path
from threading import Event
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from apoio_comum import criar_processo_teste
from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.enums import ClasseProcessual, PapelUsuario
from lupa_pipeline.dominio.repositorios import listar_achados, listar_fatos_por_processo
from lupa_pipeline.dominio.visoes import (
    VisaoArquivo,
    VisaoPagina,
    VisaoParte,
    VisaoPeca,
    VisaoProcesso,
)
from lupa_pipeline.ingestao.processamento import processar_arquivo
from lupa_pipeline.ingestao.storage import ObjectStorage, criar_storage, prefixo_processo
from lupa_pipeline.ingestao.worker import executar_worker
from lupa_pipeline.seguranca.contexto import ativar_processo
from lupa_pipeline.sinteticos.empacotamento import exportar
from lupa_pipeline.sinteticos.gabarito import Cenario, Composicao, Gabarito
from lupa_pipeline.sinteticos.gerador import gerar_conteudo
from lupa_pipeline.sinteticos.roteiro import Configuracao
from tests.conftest import criar_usuario_teste, logar

pytestmark = pytest.mark.integracao


def _valor(valor: Any, nomes: dict[str, str]) -> str:
    if isinstance(valor, dict) and isinstance(valor.get("outorgante"), str):
        valor = {**valor, "outorgante": nomes.get(valor["outorgante"], valor["outorgante"])}
    return json.dumps(valor, ensure_ascii=False, sort_keys=True)


def _conferir(sessao: Session, hk: bytes, arquivo: bytes, gab: Gabarito) -> None:
    processo = sessao.get_one(VisaoProcesso, hk)
    ativar_processo(hk, processo.chave_dados_cifrada)
    trabalho = sessao.get_one(VisaoArquivo, arquivo)
    assert (trabalho.estado, processo.status) == ("concluido", "pronto")
    paginas = {
        p.id: p
        for p in sessao.scalars(select(VisaoPagina).where(VisaoPagina.hk_arquivo == arquivo))
    }
    assert len(paginas) == len(gab.paginas)
    pecas = sessao.scalars(
        select(VisaoPeca)
        .where(VisaoPeca.hk_arquivo == arquivo, VisaoPeca.vigente.is_(True))
        .order_by(VisaoPeca.pagina_inicial)
    )
    assert [(p.pagina_inicial, p.pagina_final, p.tipo) for p in pecas] == [
        (p.pagina_inicial, p.pagina_final, p.tipo.value) for p in gab.pecas
    ]
    partes = list(sessao.scalars(select(VisaoParte).where(VisaoParte.hk_processo == hk)))
    assert {(p.nome, p.polo, p.qualidade) for p in partes} == {
        (p.nome, p.polo.value, p.qualidade.value) for p in gab.partes
    }
    nomes = {p.id: p.nome for p in partes if p.nome}
    fatos = listar_fatos_por_processo(sessao, hk)
    previstos = {(f.tipo.value, f.sujeito, _valor(f.valor, {}), f.pagina) for f in gab.eventos}
    obtidos = set()
    for fato in fatos:
        for e in fato.evidencias:
            pag = paginas[e.pagina_id]
            assert pag.texto and pag.texto[e.inicio : e.fim] == e.trecho
            obtidos.add(
                (
                    fato.tipo.value,
                    nomes.get(fato.sujeito, fato.sujeito),
                    _valor(fato.valor, nomes),
                    pag.numero,
                )
            )
    assert obtidos == previstos
    achados = listar_achados(sessao, hk)
    assert {(a.validacao, nomes[a.sujeito], a.resultado) for a in achados} == {
        (a.validacao, a.sujeito, a.resultado) for a in gab.resultado_esperado
    }


@pytest.mark.parametrize(
    ("classe", "cenario"),
    [
        *((c, Cenario.ZIP_POR_PECA) for c in ClasseProcessual),
        (ClasseProcessual.APELACAO_CIVEL, Cenario.PDF_LISO),
    ],
)
def test_upload_fila_e_resultados_conferem_com_gabarito(
    classe: ClasseProcessual,
    cenario: Cenario,
    tmp_path: Path,
    app_teste: FastAPI,
    engine_teste: Engine,
    settings_ficticias: Settings,
) -> None:
    """RF-ING-03, RF-FAT-04, RNF-01/02. Cada peça, parte e fato deve remeter ao PDF."""
    config = Configuracao(
        semente=19,
        classe=classe,
        paginas_alvo=15,
        tempestivo=True,
        mistura={Composicao.NATIVA: 1.0},
        proporcao_vazias=0,
    )
    conteudo = gerar_conteudo(config)
    try:
        (arquivo,) = exportar(conteudo, tmp_path, (cenario,))
    finally:
        conteudo.documento.close()
    gab = Gabarito.model_validate_json(arquivo.gabarito.read_bytes())
    usuario = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    storage = criar_storage(Settings())
    app_teste.state.storage = storage
    with TestClient(app_teste, base_url="https://testserver") as cliente:
        logar(cliente, engine_teste, usuario)
        # O banco de testes é compartilhado pelas parametrizações; cada cadastro exige CNJ novo.
        hk = criar_processo_teste(engine_teste, usuario, classe=classe)
        try:
            r = cliente.post(
                f"/processos/{hk.hex()}/arquivos",
                params={"nome": arquivo.caminho.name},
                content=arquivo.caminho.read_bytes(),
            )
            assert r.status_code == 201, r.text
            esperado = bytes.fromhex(r.json()["arquivo_id"])
            parar = Event()

            def executar(
                fabrica: sessionmaker[Session],
                settings: Settings,
                objetos: ObjectStorage,
                atual: bytes,
                fim: Event,
            ) -> None:
                try:
                    processar_arquivo(fabrica, settings, objetos, atual, fim)
                finally:
                    if atual == esperado:
                        parar.set()

            assert executar_worker(engine_teste, settings_ficticias, storage, parar, executar) == 0
            with Session(engine_teste) as sessao:
                _conferir(sessao, hk, esperado, gab)
        finally:
            for chave in storage.listar(prefixo_processo(hk)):
                storage.apagar(chave)
