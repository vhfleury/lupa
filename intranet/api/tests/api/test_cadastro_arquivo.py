"""Contrato do cadastro por PDF ou ZIP (RF-PRO-01, RF-ING-01 e RF-ING-02)."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from apoio_arquivos import pdf_com_senha, pdf_texto, zip_de
from apoio_comum import UsuarioTeste, eventos_do_banco, gerar_numero_cnj
from lupa_pipeline.dominio.enums import PapelUsuario
from lupa_pipeline.dominio.tabelas import hub_processo
from tests.conftest import criar_usuario_teste, logar

pytestmark = pytest.mark.integracao
ROTA = "/processos/arquivos"


def _numero() -> str:
    return gerar_numero_cnj(uuid4().int % 9_000_000 + 1)


def _enviar(cliente: TestClient, dados: bytes, nome: str = "autos.pdf", **query: str) -> Response:
    return cliente.post(ROTA, params={"nome": nome, **query}, content=dados)


def _pdf(numero: str, classe: str = "Apelação cível") -> bytes:
    return pdf_texto([f"Processo nº: {numero}\nClasse: {classe}"])


@pytest.fixture
def assessor(cliente: TestClient, engine_teste: Engine) -> UsuarioTeste:
    """Autentica quem cadastra os arquivos sintéticos (RF-PRO-01)."""
    usuario = criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR)
    logar(cliente, engine_teste, usuario)
    return usuario


@pytest.mark.parametrize(
    ("rotulo", "classe"),
    [
        ("Apelação cível", "apelacao_civel"),
        ("Agravo de instrumento", "agravo_instrumento"),
        ("Agravo interno", "agravo_interno"),
        ("Embargos de declaração", "embargos_declaracao"),
        ("Ação rescisória", "acao_originaria"),
    ],
)
def test_capa_cria_processo_responsavel_arquivo_e_eventos(
    cliente: TestClient, engine_teste: Engine, assessor: UsuarioTeste, rotulo: str, classe: str
) -> None:
    """RF-PRO-01, RF-ING-01: cada classe cria processo, arquivo e auditoria pelo mesmo envio."""
    numero = _numero()
    dados, nome = _pdf(numero, rotulo), "autos.pdf"
    if classe == "agravo_interno":
        dados, nome = zip_de({"01.pdf": dados}), "autos.zip"
    envio = _enviar(cliente, dados, nome)
    assert envio.status_code == 201, envio.text
    corpo = envio.json()
    processo = corpo["processo_id"]
    assert corpo == {
        "processo_id": processo,
        "numero_cnj": numero,
        "classe": classe,
        "processo_criado": True,
        "arquivo_id": corpo["arquivo_id"],
        "estado": "recebido",
        "sha256": sha256(dados).hexdigest(),
        "tamanho_bytes": len(dados),
        "mime": "application/" + nome.split(".")[-1],
        "duplicado": False,
        "origem": {"numero_cnj": "lido", "classe": "lido"},
    }
    assert cliente.get(f"/processos/{processo}").json()["criador_id"] == assessor.id
    responsaveis = cliente.get(f"/processos/{processo}/responsaveis").json()["responsaveis"]
    assert [u["id"] for u in responsaveis] == [assessor.id]
    for acao, objeto in (("processo_criado", processo), ("upload", corpo["arquivo_id"])):
        eventos = eventos_do_banco(
            engine_teste, usuario_id=assessor.id, acao=acao, objeto_id=objeto
        )
        assert [(e.resultado, e.processo_id) for e in eventos] == [("ok", processo)]


def test_campos_ausentes_pedem_complemento_sem_criar_processo(
    cliente: TestClient, engine_teste: Engine, assessor: UsuarioTeste
) -> None:
    """RF-PRO-01: informa o que leu, mantém o banco vazio até reenvio e aceita a classe."""
    numero = _numero()
    dados = pdf_texto([f"Processo nº: {numero}"])
    with Session(engine_teste) as sessao:
        total = sessao.scalar(select(func.count()).select_from(hub_processo))
    erro = _enviar(cliente, dados)
    assert erro.status_code == 422, erro.text
    corpo = erro.json()
    assert corpo["motivo"] == "identificacao_incompleta"
    assert corpo["lido"] == {"numero_cnj": numero, "classe": None}
    assert corpo["faltando"] == ["classe"] and corpo["numeros_encontrados"] == [numero]
    with Session(engine_teste) as sessao:
        assert sessao.scalar(select(func.count()).select_from(hub_processo)) == total
    eventos = eventos_do_banco(engine_teste, usuario_id=assessor.id, acao="upload")
    assert [(e.resultado, e.processo_id) for e in eventos] == [("falha", None)]
    sucesso = _enviar(cliente, dados, classe="agravo_interno")
    assert sucesso.status_code == 201
    assert sucesso.json()["origem"] == {"numero_cnj": "lido", "classe": "informado"}


def test_numero_informado_precisa_de_digito_verificador(
    cliente: TestClient, assessor: UsuarioTeste
) -> None:
    """RF-PRO-01: mesmo com capa válida, o número informado precisa passar no módulo 97."""
    numero = _numero()
    errado = numero[:8] + f"{(int(numero[8:10]) + 1) % 100:02d}" + numero[10:]
    resposta = _enviar(cliente, _pdf(numero), numero_cnj=errado)
    assert resposta.status_code == 422 and "dígito" in resposta.json()["detail"]


def test_anexa_sem_mudar_classe_e_reconhece_o_mesmo_conteudo(
    cliente: TestClient, engine_teste: Engine, assessor: UsuarioTeste
) -> None:
    """RF-PRO-01, RF-ING-01: novo arquivo usa a classe existente e a duplicata não gera evento."""
    numero = _numero()
    processo = _enviar(cliente, _pdf(numero)).json()["processo_id"]
    segundo = _pdf(_numero(), "Agravo interno")
    novo = _enviar(cliente, segundo, numero_cnj=numero)
    assert novo.status_code == 201
    corpo = novo.json()
    assert (corpo["processo_id"], corpo["processo_criado"], corpo["classe"]) == (
        processo,
        False,
        "apelacao_civel",
    )
    assert corpo["origem"] == {"numero_cnj": "informado", "classe": "existente"}
    repetido = _enviar(cliente, segundo, numero_cnj=numero)
    assert repetido.status_code == 200
    assert repetido.json() == corpo | {"duplicado": True}
    assert len(eventos_do_banco(engine_teste, acao="upload", processo_id=processo)) == 2


def test_processo_descartado_nao_recebe_envio(cliente: TestClient, engine_teste: Engine) -> None:
    """RF-PRO-01: o mesmo número descartado devolve conflito ao anexar."""
    gestor = criar_usuario_teste(engine_teste, PapelUsuario.DESEMBARGADOR)
    logar(cliente, engine_teste, gestor)
    arquivo = _pdf(_numero())
    processo = _enviar(cliente, arquivo).json()["processo_id"]
    assert cliente.post(f"/processos/{processo}/descartar").status_code == 200
    assert _enviar(cliente, arquivo).status_code == 409


def test_upload_com_senha_e_recusado_mesmo_com_complemento(
    cliente: TestClient, app_teste: FastAPI, engine_teste: Engine, assessor: UsuarioTeste
) -> None:
    """RF-PRO-01, RF-ING-02: o PDF recusado só grava o evento de tentativa negada."""
    tabelas = [
        t
        for t in hub_processo.metadata.sorted_tables
        if t.name.startswith(("hub_", "link_", "sat_")) and t.name != "link_evento_auditoria"
    ]
    with Session(engine_teste) as sessao:
        antes = [sessao.scalar(select(func.count()).select_from(t)) for t in tabelas]
        negado = _enviar(cliente, pdf_com_senha(), numero_cnj=_numero(), classe="agravo_interno")
        assert negado.status_code == 422 and negado.json()["motivo"] == "senha"
        assert antes == [sessao.scalar(select(func.count()).select_from(t)) for t in tabelas]
    assert app_teste.state.storage.listar("") == []
    eventos = eventos_do_banco(engine_teste, usuario_id=assessor.id, acao="upload")
    assert [(e.resultado, e.processo_id) for e in eventos] == [("negado", None)]


def test_dois_envios_simultaneos_criam_um_processo_e_dois_arquivos(
    app_teste: FastAPI, engine_teste: Engine
) -> None:
    """RF-PRO-01: duas transações disputando o mesmo número concluem com um único criador."""
    clientes = [TestClient(app_teste, base_url="https://testserver") for _ in range(2)]
    for c in clientes:
        logar(c, engine_teste, criar_usuario_teste(engine_teste, PapelUsuario.ASSESSOR))
    barreira = Barrier(2)
    numero = _numero()

    def enviar(indice: int) -> Response:
        dados = pdf_texto([f"Processo nº: {numero}\nClasse: Agravo interno\nLote {indice}"])
        barreira.wait(timeout=15)
        return _enviar(clientes[indice], dados)

    with ThreadPoolExecutor(2) as executor:
        respostas = list(executor.map(enviar, range(2)))
    assert [r.status_code for r in respostas] == [201, 201]
    corpos = [r.json() for r in respostas]
    assert sorted(c["processo_criado"] for c in corpos) == [False, True]
    assert len({c["processo_id"] for c in corpos}) == 1
    assert len({c["arquivo_id"] for c in corpos}) == 2


def test_cadastro_sem_arquivo_nao_existe(cliente: TestClient, assessor: UsuarioTeste) -> None:
    """RF-PRO-01: a rota de cadastro manual deixa de aceitar POST."""
    assert (
        cliente.post(
            "/processos", json={"numero_cnj": _numero(), "classe": "agravo_interno"}
        ).status_code
        == 405
    )
