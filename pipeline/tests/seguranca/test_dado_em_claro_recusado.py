"""Leitura recusa objeto ou campo que não esteja cifrado (RF-SEG-01).

Dado em claro no bucket ou no banco é erro, não é lido.
"""

import io
import os

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from apoio_comum import criar_pagina, criar_processo
from lupa_pipeline.dominio.visoes import VisaoPagina, atual
from lupa_pipeline.ingestao.storage import ArmazenamentoMemoria, StorageCifrado, chave_objeto
from lupa_pipeline.seguranca.contexto import contexto_cifra, registrar_dek
from lupa_pipeline.seguranca.envelope import CifraInvalidaError, gerar_dek, processo_do_campo
from lupa_pipeline.seguranca.tipos import JsonCifrado, TextoCifrado

BASE64_SEM_PREFIXO = "QUJD" * 20
DIALETO = create_engine("postgresql+psycopg://").dialect


def test_storage_recusa_objeto_sem_cabecalho_cifrado() -> None:
    """RF-SEG-01: objeto gravado em claro direto no bucket não é devolvido pela leitura."""
    processo = os.urandom(32)
    interno = ArmazenamentoMemoria()
    chave = chave_objeto(processo, "0" * 64)
    interno.gravar(chave, io.BytesIO(b"%PDF-1.7 em claro"))
    with contexto_cifra():
        registrar_dek(processo, gerar_dek())
        with pytest.raises(CifraInvalidaError):
            StorageCifrado(interno).ler(chave)


def test_campo_sem_prefixo_lupa1_e_recusado_mesmo_sendo_base64() -> None:
    """RF-SEG-01: base64 válido sem o prefixo `lupa1:` não é tratado como campo cifrado."""
    with pytest.raises(CifraInvalidaError):
        processo_do_campo(BASE64_SEM_PREFIXO)


@pytest.mark.parametrize("valor", ["Certidão de intimação em claro", BASE64_SEM_PREFIXO])
def test_coluna_texto_cifrado_recusa_valor_em_claro(valor: str) -> None:
    """RF-SEG-01: texto em claro numa coluna `TextoCifrado` não volta como está."""
    with pytest.raises(CifraInvalidaError):
        TextoCifrado("sat_pagina_extracao.texto").process_result_value(valor, DIALETO)


def test_coluna_json_cifrado_recusa_valor_em_claro() -> None:
    """RF-SEG-01: JSON em claro numa coluna `JsonCifrado` não é desserializado."""
    with pytest.raises(CifraInvalidaError):
        JsonCifrado("sat_fato_valor.valor").process_result_value('{"a": 1}', DIALETO)


@pytest.mark.integracao
def test_pagina_sem_trechos_grava_lista_vazia_cifrada(sessao: Session) -> None:
    """RF-SEG-01: a lista vazia de trechos vai cifrada ao satélite e volta como lista vazia."""
    hk_pagina = criar_pagina(sessao, criar_processo(sessao))
    brutos = sessao.execute(
        text(
            "SELECT trechos_ocultos, trechos_suspeitos FROM sat_pagina_saneamento "
            "WHERE hk_pagina = :hk"
        ),
        {"hk": hk_pagina},
    ).one()
    assert all(valor.startswith("lupa1:") for valor in brutos)
    pagina = sessao.scalars(atual(select(VisaoPagina).where(VisaoPagina.hk_pagina == hk_pagina)))
    assert [(p.trechos_ocultos, p.trechos_suspeitos) for p in pagina] == [([], [])]
