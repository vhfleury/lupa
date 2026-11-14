"""Cliente e autos cíveis sintéticos para os testes de rota e de integração."""

from collections.abc import Iterator
from dataclasses import dataclass
from threading import Event

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from apoio_arquivos import pdf_texto, zip_de
from apoio_comum import criar_processo_teste
from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.enums import PapelUsuario
from lupa_pipeline.dominio.visoes import VisaoProcesso
from lupa_pipeline.ingestao.processamento import processar_arquivo
from lupa_pipeline.seguranca.contexto import ativar_processo
from tests.conftest import criar_usuario_teste, logar


@dataclass
class Autos:
    """Arquivo no storage cifrado, com páginas e fatos extraídos na versão corrente."""

    cliente: TestClient
    processo: bytes
    arquivo: bytes

    @property
    def url(self) -> str:
        """Caminho público do processo."""
        return "/processos/" + self.processo.hex()


@pytest.fixture
def autos_civeis(
    app_teste: FastAPI,
    engine_teste: Engine,
    fabrica_sessao: sessionmaker[Session],
    settings_ficticias: Settings,
) -> Iterator[Autos]:
    """RF-ING-01: gera peças sintéticas, faz upload pela rota e executa o worker."""
    criador = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    processo = criar_processo_teste(engine_teste, criador)
    textos = [
        "PETIÇÃO INICIAL\nAutor: Marina do Lago\nRéu: Instituto das Flores\n"
        "Ajuizamento em 02/02/2025.",
        "SENTENÇA\nDecisão recorrida proferida em 03/03/2025.",
        "CERTIDÃO\nRecorrente: Marina do Lago\nIntimação do recorrente em 04/03/2025.\n"
        "Retificação para 06/03/2025.",
        "PROCURAÇÃO\nOutorgante: Marina do Lago\nOutorgado: Ari do Campo, OAB/GO 12345",
        "COMPROVANTE DE PREPARO\nRecorrente: Marina do Lago\nPreparo recolhido em 07/03/2025.",
        "APELAÇÃO\nRecorrente: Marina do Lago\nRecurso interposto em 10/03/2025.\n"
        "Advogado subscritor: Ari do Campo, OAB/GO 12345",
    ]
    dados = zip_de({f"{i:02d}-sintetico.pdf": pdf_texto([t]) for i, t in enumerate(textos)})
    with TestClient(app_teste, base_url="https://testserver") as cliente:
        logar(cliente, engine_teste, criador)
        r = cliente.post(
            f"/processos/{processo.hex()}/arquivos",
            params={"nome": "autos-sinteticos.zip"},
            content=dados,
        )
        assert r.status_code == 201, r.text
        arquivo = bytes.fromhex(r.json()["arquivo_id"])
        with fabrica_sessao() as s:
            ativar_processo(processo, s.get_one(VisaoProcesso, processo).chave_dados_cifrada)
        processar_arquivo(
            fabrica_sessao, settings_ficticias, app_teste.state.storage, arquivo, Event()
        )
        yield Autos(cliente, processo, arquivo)
