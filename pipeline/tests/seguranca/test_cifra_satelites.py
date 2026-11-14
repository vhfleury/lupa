"""DEK do processo em `sat_processo_chave` e colunas cifradas dos satélites (D5, D14; RF-SEG-01)."""

import io

import pytest
from sqlalchemy import Engine, Text, cast, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from apoio_comum import TEXTO_PAGINA, criar_pagina, criar_processo
from lupa_pipeline.dominio.chaves import hash_diff
from lupa_pipeline.dominio.gravacao import gravar_satelite
from lupa_pipeline.dominio.tabelas import metadata, sat_pagina_extracao, sat_processo_chave
from lupa_pipeline.dominio.visoes import VisaoPagina, VisaoProcesso, atual
from lupa_pipeline.ingestao.storage import ArmazenamentoMemoria, StorageCifrado, chave_objeto
from lupa_pipeline.seguranca.chaves import carregador_sql
from lupa_pipeline.seguranca.cofre import CHAVE_DADOS
from lupa_pipeline.seguranca.contexto import (
    ChaveIndisponivelError,
    ativar_processo,
    contexto_atual,
    contexto_cifra,
    dek_de,
    obter_cofre,
)
from lupa_pipeline.seguranca.envelope import CifraInvalidaError

pytestmark = pytest.mark.integracao

MARCA = "Zumbrelanço Quintessárico"


def _pagina(sessao: Session, hk_pagina: bytes) -> VisaoPagina:
    consulta = select(VisaoPagina).where(VisaoPagina.hk_pagina == hk_pagina)
    return sessao.scalars(atual(consulta)).one()


def _linha_extracao(sessao: Session, hk_pagina: bytes) -> tuple[str, bytes]:
    linha = sessao.execute(
        text("SELECT texto, hash_diff FROM sat_pagina_extracao WHERE hk_pagina = :hk"),
        {"hk": hk_pagina},
    ).one()
    return str(linha.texto), bytes(linha.hash_diff)


def test_dek_do_processo_fica_em_sat_processo_chave_envolvida_pela_chave_lupa(
    sessao: Session,
) -> None:
    """D14: a DEK cifrada com `lupa` é a linha de `sat_processo_chave` e abre a DEK do contexto."""
    hk = criar_processo(sessao)
    token = sessao.scalar(
        select(VisaoProcesso.chave_dados_cifrada).where(VisaoProcesso.hk_processo == hk)
    )
    assert token is not None and token.startswith("mem:v")
    assert obter_cofre().decifrar(CHAVE_DADOS, token) == dek_de(hk)
    assert contexto_atual().atual == hk
    linhas = sessao.execute(
        select(sat_processo_chave.c.chave_dados_cifrada).where(
            sat_processo_chave.c.hk_processo == hk
        )
    ).all()
    assert [linha[0] for linha in linhas] == [token]


def test_coluna_cifrada_vai_ao_banco_cifrada_e_volta_em_claro_pela_view(sessao: Session) -> None:
    """RF-SEG-01: o texto da página fica `lupa1:` no satélite e a view o devolve em claro."""
    hk_pagina = criar_pagina(sessao, criar_processo(sessao), f"Certidão. {MARCA}.")
    bruto, _ = _linha_extracao(sessao, hk_pagina)
    assert bruto.startswith("lupa1:") and MARCA not in bruto
    pagina = _pagina(sessao, hk_pagina)
    assert (pagina.texto, pagina.texto_normalizado) == (f"Certidão. {MARCA}.",) * 2


def test_varredura_do_banco_nao_acha_texto_sintetico_em_claro(sessao: Session) -> None:
    """RF-SEG-01: nenhuma coluna de nenhuma tabela guarda o texto sintético em claro."""
    criar_pagina(sessao, criar_processo(sessao), f"Petição. {MARCA}.")
    achados = []
    for tabela in metadata.tables.values():
        for coluna in tabela.columns:
            filtro = cast(coluna, Text).like(f"%{MARCA}%")
            if sessao.scalar(select(func.count()).select_from(tabela).where(filtro)):
                achados.append(f"{tabela.name}.{coluna.name}")
    assert achados == []


def test_hash_diff_do_satelite_cifrado_e_hmac_com_a_dek(sessao: Session) -> None:
    """D5: o `hash_diff` de satélite cifrado é HMAC com a DEK, e a repetição não grava."""
    hk_processo = criar_processo(sessao)
    hk_pagina = criar_pagina(sessao, hk_processo)
    _, gravado = _linha_extracao(sessao, hk_pagina)
    pagina = _pagina(sessao, hk_pagina)
    atributos = {coluna: getattr(pagina, coluna) for coluna in _atributos_extracao()}
    assert gravado == hash_diff(atributos, dek=dek_de(hk_processo))
    assert gravado != hash_diff(atributos)
    assert gravar_satelite(sessao, sat_pagina_extracao, hk_pagina, atributos, "teste") is False


def _atributos_extracao() -> list[str]:
    tecnicas = {"hk_pagina", "load_dts", "record_source", "hash_diff"}
    return [c.name for c in sat_pagina_extracao.columns if c.name not in tecnicas]


def test_mesmo_texto_em_processos_diferentes_tem_hash_diff_diferente(sessao: Session) -> None:
    """D5: sem a DEK do processo, o `hash_diff` não serve de dicionário para o texto."""
    primeiro = criar_pagina(sessao, criar_processo(sessao), TEXTO_PAGINA)
    segundo = criar_pagina(sessao, criar_processo(sessao), TEXTO_PAGINA)
    assert _linha_extracao(sessao, primeiro)[1] != _linha_extracao(sessao, segundo)[1]


def test_storage_grava_cifrado_no_caminho_do_processo() -> None:
    """D14, RF-SEG-01: objeto em `processo/<hex>/<sha256>`, cifrado com a DEK do processo."""
    hk = bytes(range(32))
    interno = ArmazenamentoMemoria()
    chave = chave_objeto(hk, "a" * 64)
    with contexto_cifra() as contexto:
        contexto.deks[hk] = bytes(32)
        StorageCifrado(interno).gravar(chave, io.BytesIO(f"%PDF {MARCA}".encode()))
        guardado = interno.ler(chave)
        assert guardado.startswith(b"LUPAOBJ") and MARCA.encode() not in guardado
        assert StorageCifrado(interno).ler(chave) == f"%PDF {MARCA}".encode()
    assert chave.startswith(f"processo/{hk.hex()}/")


def test_leitura_sem_dek_no_contexto_abre_pela_view_do_banco(
    fabrica_sessao: sessionmaker[Session], engine_teste: Engine
) -> None:
    """D14: campo de processo sem DEK aberta é lido com a chave de `v_processo` e o cofre."""
    with fabrica_sessao() as session, session.begin():
        hk_pagina = criar_pagina(session, criar_processo(session), f"Sentença. {MARCA}.")
    with contexto_cifra(carregador_sql(fabrica_sessao)), Session(engine_teste) as session:
        assert _pagina(session, hk_pagina).texto == f"Sentença. {MARCA}."


def test_valor_em_claro_no_satelite_e_recusado_na_leitura(sessao: Session) -> None:
    """RF-SEG-01: texto gravado em claro por fora da aplicação dá erro explícito na leitura."""
    hk_pagina = criar_pagina(sessao, criar_processo(sessao))
    sessao.execute(text("ALTER TABLE sat_pagina_extracao DISABLE TRIGGER USER"))
    sessao.execute(
        text("UPDATE sat_pagina_extracao SET texto = :claro WHERE hk_pagina = :hk"),
        {"claro": f"Texto em claro {MARCA}", "hk": hk_pagina},
    )
    with pytest.raises(CifraInvalidaError):
        _pagina(sessao, hk_pagina)


def test_processo_sem_chave_nao_abre_a_dek() -> None:
    """RF-PRO-05: processo sem linha em `sat_processo_chave` (descartado) não tem DEK."""
    with contexto_cifra(), pytest.raises(ChaveIndisponivelError):
        ativar_processo(bytes(32), None)
