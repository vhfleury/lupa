"""Ingestão de autos cíveis pelo HTTP, fila PostgreSQL e MinIO com chave por processo."""

import json
from pathlib import Path
from random import SystemRandom
from threading import Event
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

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
from lupa_pipeline.ingestao.eventos.etapa import processar_eventos
from lupa_pipeline.ingestao.processamento import processar_arquivo
from lupa_pipeline.ingestao.storage import ObjectStorage, criar_storage, prefixo_processo
from lupa_pipeline.ingestao.worker import executar_worker
from lupa_pipeline.sinteticos import identidades
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


def _conferir_ficha_e_reprocessamento(
    cliente: TestClient, engine: Engine, hk: bytes, gab: Gabarito
) -> None:
    """RF-FAT-01/03/04, RF-ING-08: confronta a capa com a prova e preserva a revisão humana."""
    tipos = {
        "relator",
        "orgao_julgador",
        "assunto",
        "valor_causa",
        "juizo_origem",
        "data_distribuicao",
    }
    base = f"/processos/{hk.hex()}"
    previstos = {e.tipo.value: e.valor for e in gab.eventos if e.tipo.value in tipos}
    dossie = cliente.get(base + "/dossie").json()
    dados = dossie["ficha"]["dados_capa"]
    assert set(previstos) == tipos
    assert {d["tipo"]: d["valor"] for d in dados} == previstos
    fatos = {f["id"]: f for f in cliente.get(base + "/fatos").json()["fatos"]}
    for d in dados:
        prova = fatos[d["fato_id"]]["evidencias"][0]
        assert (d["pagina_id"], d["evidencia_id"]) == (prova["pagina_id"], prova["id"])
    assert [e["data"] for e in dossie["linha_do_tempo"] if e["tipo"] == "data_distribuicao"] == [
        previstos["data_distribuicao"]
    ]
    relator = next(d for d in dados if d["tipo"] == "relator")
    evidencia = fatos[relator["fato_id"]]["evidencias"][0]
    pedido = {k: evidencia[k] for k in ("pagina_id", "inicio", "fim", "trecho")}
    novo = relator["valor"].upper()
    correcao = cliente.post(
        f"{base}/fatos/{relator['fato_id']}/corrigir",
        json=pedido | {"status": "corrigido", "valor": novo},
    )
    assert correcao.status_code == 201, correcao.text
    with Session(engine) as sessao, sessao.begin():
        processar_eventos(sessao, hk, gab.processo.data_referencia)
    ficha = cliente.get(base + "/dossie").json()["ficha"]
    assert [d["valor"] for d in ficha["dados_capa"] if d["tipo"] == "relator"] == [novo]


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
    """RF-PRO-01, RF-ING-03/08, RF-FAT-01/03/04, RNF-01/02: do cadastro ao gabarito."""
    config = Configuracao(
        semente=19,
        classe=classe,
        paginas_alvo=15,
        tempestivo=True,
        mistura={Composicao.NATIVA: 1.0},
        proporcao_vazias=0,
    )
    gerar_cnj = identidades.gerar_numero_cnj
    with patch.object(
        identidades, "gerar_numero_cnj", side_effect=lambda _, ano: gerar_cnj(SystemRandom(), ano)
    ):
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
        r = cliente.post(
            "/processos/arquivos",
            params={"nome": arquivo.caminho.name},
            content=arquivo.caminho.read_bytes(),
        )
        assert r.status_code == 201, r.text
        corpo = r.json()
        assert corpo["processo_criado"] and corpo["numero_cnj"] == gab.processo.numero_cnj
        assert corpo["classe"] == classe and corpo["origem"] == {
            "numero_cnj": "lido",
            "classe": "lido",
        }
        hk = bytes.fromhex(corpo["processo_id"])
        try:
            esperado = bytes.fromhex(corpo["arquivo_id"])
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
            if cenario == Cenario.PDF_LISO:
                _conferir_ficha_e_reprocessamento(cliente, engine_teste, hk, gab)
        finally:
            for chave in storage.listar(prefixo_processo(hk)):
                storage.apagar(chave)
