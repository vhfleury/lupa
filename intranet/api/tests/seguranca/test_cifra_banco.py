"""Cifra em repouso da API, das leituras pelo agente e dos temporários de ingestão (RF-SEG-01)."""

import hashlib
from datetime import date
from pathlib import Path
from threading import Event

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg import Connection, sql
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from apoio_comum import criar_processo_teste, eventos_do_banco
from lupa_intranet.agente.contexto import Delimitador
from lupa_intranet.agente.ferramentas.leitura import _paginas_com_termo
from lupa_intranet.agente.ferramentas.sessao import SessaoAgente
from lupa_intranet.agente.repositorio import conversa_do_usuario, gravar_mensagem
from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.enums import PapelMensagem, StatusMensagem
from lupa_pipeline.dominio.visoes import (
    VisaoConversa,
    VisaoEvidencia,
    VisaoMensagem,
    VisaoPagina,
    VisaoParte,
    VisaoProcesso,
)
from lupa_pipeline.ingestao import processamento
from lupa_pipeline.ingestao.inventario import EntradaExtraida
from lupa_pipeline.ingestao.recepcao import ArquivoRecebido, TipoArquivo, lacrar
from lupa_pipeline.ingestao.sandbox import LimitesSandbox
from lupa_pipeline.ingestao.storage import ArmazenamentoMemoria, StorageCifrado, chave_objeto
from lupa_pipeline.seguranca.chaves import carregador_sql
from lupa_pipeline.seguranca.cofre import CHAVE_DADOS, ChaveAusenteError, CofreMemoria
from lupa_pipeline.seguranca.contexto import (
    ChaveIndisponivelError,
    abrir_dek,
    ativar_processo,
    contexto_cifra,
    definir_cofre,
    dek_de,
    dek_para_gravar,
    obter_cofre,
)
from lupa_pipeline.seguranca.envelope import CifraInvalidaError, decifrar_campo
from tests.agente.conftest import (
    NOME_PARTE,
    SENTINELA_OCULTO,
    TEXTOS,
    ProcessoAgente,
    semear_processo_agente,
)
from tests.conftest import logar

pytestmark = pytest.mark.integracao
MENSAGEM = "Relato sintético Plutomarnevisca."
CITACAO = "Segmento sintético Quiblarventossa."
PDF = b"%PDF-1.7\n% sintetico\n" + b"0" * 70_000


@pytest.fixture
def autos(engine_teste: Engine) -> ProcessoAgente:
    """Autos cíveis com dois titulares, seus textos e mensagens vinculadas ao processo."""
    caso = semear_processo_agente(engine_teste)
    hk = bytes.fromhex(caso.processo_id)
    with Session(engine_teste) as sessao, sessao.begin():
        processo = sessao.get_one(VisaoProcesso, hk)
        ativar_processo(hk, processo.chave_dados_cifrada)
        conversa = conversa_do_usuario(sessao, hk, caso.assessor.hk)
        gravar_mensagem(
            sessao,
            conversa,
            PapelMensagem.AGENTE,
            StatusMensagem.RESPONDIDA,
            MENSAGEM,
            [{"pagina_id": caso.paginas[2], "trecho": CITACAO, "hash_trecho": "a" * 64}],
        )
    return caso


def test_campo_em_repouso_so_abre_com_a_dek_do_processo(
    engine_teste: Engine, autos: ProcessoAgente
) -> None:
    """A mesma coluna pode ser lida pela view e recusa a DEK do processo vizinho."""
    hk = bytes.fromhex(autos.processo_id)
    outro = bytes.fromhex(autos.outro_processo_id)
    with (
        Session(engine_teste) as sessao,
        contexto_cifra(carregador_sql(sessionmaker(engine_teste))),
    ):
        bruto = sessao.execute(
            text("SELECT texto FROM sat_pagina_extracao WHERE hk_pagina=:p LIMIT 1"),
            {"p": bytes.fromhex(autos.paginas[1])},
        ).scalar_one()
        assert bruto.startswith("lupa1:") and NOME_PARTE not in bruto
        assert decifrar_campo(dek_de(hk), bruto, "sat_pagina_extracao.texto") == TEXTOS[1]
        with pytest.raises(CifraInvalidaError):
            decifrar_campo(dek_de(outro), bruto, "sat_pagina_extracao.texto")
        assert sessao.get_one(VisaoPagina, bytes.fromhex(autos.paginas[1])).texto == TEXTOS[1]


def test_chave_unica_rotacionada_preserva_as_deks_e_destruida_impede_abertura(
    engine_teste: Engine,
) -> None:
    """Os dois processos da instalação usam DEKs distintas envolvidas por uma chave só."""
    anterior = obter_cofre()
    cofre = CofreMemoria()
    definir_cofre(cofre)
    try:
        processos = [criar_processo_teste(engine_teste) for _ in range(2)]
        with Session(engine_teste) as sessao:
            tokens = [sessao.get_one(VisaoProcesso, hk).chave_dados_cifrada for hk in processos]
        chaves = []
        for token in tokens:
            assert token is not None
            chaves.append(abrir_dek(cofre, token))
        assert chaves[0] != chaves[1]
        cofre.rotacionar(CHAVE_DADOS)
        for token, dek in zip(tokens, chaves, strict=True):
            assert token is not None
            novo = cofre.recifrar(CHAVE_DADOS, token)
            assert novo.startswith("mem:v2:") and abrir_dek(cofre, novo) == dek
        cofre.destruir_chave(CHAVE_DADOS)
        for token in tokens:
            assert token is not None
            with pytest.raises(ChaveAusenteError):
                abrir_dek(cofre, token)
    finally:
        definir_cofre(anterior)


def test_sem_processo_ativo_nao_grava_e_sem_dek_nao_le(autos: ProcessoAgente) -> None:
    """Escopos isolados recusam gravação em claro e abertura de uma chave ausente."""
    with contexto_cifra(), pytest.raises(ChaveIndisponivelError):
        dek_para_gravar()
    with contexto_cifra(), pytest.raises(ChaveIndisponivelError):
        ativar_processo(bytes.fromhex(autos.processo_id), None)


def test_dossie_le_nome_cifrado_e_registra_consulta_do_assessor(
    app_teste: FastAPI, engine_teste: Engine, autos: ProcessoAgente
) -> None:
    """A consulta apresenta o mesmo nome da qualificação, com auditoria do acesso aos autos."""
    hk = bytes.fromhex(autos.processo_id)
    with (
        Session(engine_teste) as sessao,
        contexto_cifra(carregador_sql(sessionmaker(engine_teste))),
    ):
        parte = sessao.scalars(select(VisaoParte).where(VisaoParte.hk_processo == hk)).one()
        assert parte.nome == NOME_PARTE
        bruto = sessao.execute(
            text("SELECT nome FROM sat_parte_identidade WHERE hk_parte=:p"), {"p": parte.hk_parte}
        ).scalar_one()
        assert bruto.startswith("lupa1:") and NOME_PARTE not in bruto
    rota = f"/processos/{autos.processo_id}/dossie"
    with TestClient(app_teste, base_url="https://testserver") as cliente:
        logar(cliente, engine_teste, autos.assessor)
        resposta = cliente.get(rota)
    assert (
        resposta.status_code == 200 and resposta.json()["ficha"]["partes"][0]["nome"] == NOME_PARTE
    )
    acessos = eventos_do_banco(engine_teste, acao="processo_aberto", hk_processo=hk)
    assert [(e.usuario_id, e.objeto_id) for e in acessos] == [(autos.assessor.id, rota)]


def test_dump_logico_nao_contem_textos_nomes_mensagens_ou_citacoes(
    engine_teste: Engine, autos: ProcessoAgente
) -> None:
    """COPY de cada tabela de usuário detecta texto claro em qualquer satélite ou trilha."""
    hk = bytes.fromhex(autos.processo_id)
    with (
        Session(engine_teste) as sessao,
        contexto_cifra(carregador_sql(sessionmaker(engine_teste))),
    ):
        assert (
            sessao.scalar(
                select(VisaoMensagem.texto)
                .join(VisaoConversa, VisaoConversa.hk_conversa == VisaoMensagem.hk_conversa)
                .where(VisaoConversa.hk_processo == hk)
            )
            == MENSAGEM
        )
        assert sessao.scalars(
            select(VisaoEvidencia.trecho).where(VisaoEvidencia.hk_processo == hk)
        ).all()
    partes: list[bytes] = []
    with engine_teste.connect() as conexao:
        bruta = conexao.connection.driver_connection
        assert isinstance(bruta, Connection)
        with bruta.cursor() as cursor:
            cursor.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
            )
            for (tabela,) in cursor.fetchall():
                comando = sql.SQL("COPY {} TO STDOUT").format(sql.Identifier("public", tabela))
                with cursor.copy(comando) as copia:
                    partes.extend(bytes(bloco) for bloco in copia)
    dump = b"".join(partes).decode()
    assert "lupa1:" in dump
    for sentinela in (MENSAGEM, CITACAO, NOME_PARTE, SENTINELA_OCULTO, TEXTOS[3]):
        assert sentinela not in dump


def test_busca_em_memoria_respeita_teto_de_paginas(
    engine_teste: Engine, autos: ProcessoAgente
) -> None:
    """Uma palavra exclusiva da terceira página só aparece quando a janela a inclui."""
    with (
        Session(engine_teste) as sessao,
        contexto_cifra(carregador_sql(sessionmaker(engine_teste))),
    ):
        agente = SessaoAgente(
            sessao,
            bytes.fromhex(autos.processo_id),
            "apelacao_civel",
            autos.numero_cnj,
            Delimitador(),
            lambda *_: None,
            date(2025, 4, 1),
        )
        assert [p.numero for p in _paginas_com_termo(agente, "certifico")] == [3]
        assert _paginas_com_termo(agente, "certifico", limite_paginas=2) == []


def test_worker_decifra_em_temporario_0600_e_apaga_mesmo_em_falha(
    engine_teste: Engine,
    settings_ficticias: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O PDF sai do storage cifrado e a falha induzida na inspeção limpa o diretório local."""
    hk = criar_processo_teste(engine_teste)
    fabrica = sessionmaker(engine_teste)
    storage = StorageCifrado(ArmazenamentoMemoria())
    original = tmp_path / "upload.pdf"
    original.write_bytes(PDF)
    recebido = ArquivoRecebido(original, hashlib.sha256(PDF).hexdigest(), len(PDF), TipoArquivo.PDF)
    with fabrica.begin() as sessao:
        processo = sessao.get_one(VisaoProcesso, hk)
        assert processo.hk_criador is not None
        ativar_processo(hk, processo.chave_dados_cifrada)
        lacre = lacrar(
            sessao,
            storage,
            recebido,
            hk_processo=hk,
            enviado_por=processo.hk_criador,
            nome_original="autos.pdf",
        )
    copia = storage.interno.ler(chave_objeto(hk, recebido.sha256))
    assert copia.startswith(b"LUPAOBJ") and PDF not in copia
    trabalho = tmp_path / "trabalho"
    trabalho.mkdir()
    vistos = []

    def falhar(entradas: list[EntradaExtraida], _limites: LimitesSandbox) -> None:
        temporario = entradas[0].caminho
        vistos.append(temporario.stat().st_mode & 0o777)
        assert temporario.read_bytes() == PDF
        raise RuntimeError("falha sintética")

    monkeypatch.setattr(processamento, "_inspecionar", falhar)
    with pytest.raises(RuntimeError, match="falha sintética"):
        processamento.processar_arquivo(
            fabrica,
            settings_ficticias.model_copy(update={"ingestao_dir_temporario": trabalho}),
            storage,
            lacre.hk_arquivo,
            Event(),
        )
    assert vistos == [0o600]
    assert list(trabalho.iterdir()) == []
