"""Leitura recusa objeto, campo ou identidade que não esteja cifrado.

Antes da Etapa 7.4 a leitura aceitava dado em claro (legado) e devolvia como estava. Não há mais
legado em nenhum ambiente; dado em claro no bucket ou no banco agora é erro, não é lido.
"""

import io
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from lupa.dominio.tabelas import PaginaTabela
from lupa.ingestao.storage import ArmazenamentoMemoria, StorageCifrado, chave_objeto
from lupa.seguranca.chaves import decifrar_identidade
from lupa.seguranca.cofre import CofreMemoria, TokenInvalidoError
from lupa.seguranca.contexto import contexto_cifra, registrar_dek
from lupa.seguranca.envelope import CifraInvalidaError, gerar_dek, processo_do_campo
from lupa.seguranca.tipos import JsonCifrado, TextoCifrado
from tests.conftest import criar_pagina

BASE64_SEM_PREFIXO = "QUJD" * 20


def test_storage_recusa_objeto_sem_cabecalho_cifrado() -> None:
    """Objeto gravado em claro direto no bucket não é devolvido pela leitura."""
    processo_id = uuid4()
    interno = ArmazenamentoMemoria()
    chave = chave_objeto(uuid4(), processo_id, "0" * 64)
    interno.gravar(chave, io.BytesIO(b"%PDF-1.7 em claro"))
    with contexto_cifra():
        registrar_dek(processo_id, gerar_dek())
        with pytest.raises(CifraInvalidaError):
            StorageCifrado(interno).ler(chave)


def test_campo_sem_prefixo_lupa1_e_recusado_mesmo_sendo_base64() -> None:
    """Base64 válido sem o prefixo `lupa1:` não é tratado como campo cifrado."""
    with pytest.raises(CifraInvalidaError):
        processo_do_campo(BASE64_SEM_PREFIXO)


@pytest.mark.parametrize("valor", ["Certidão de intimação em claro", BASE64_SEM_PREFIXO])
def test_coluna_texto_cifrado_recusa_valor_em_claro(valor: str) -> None:
    """Texto em claro numa coluna `TextoCifrado` não volta como está."""
    with pytest.raises(CifraInvalidaError):
        TextoCifrado("pagina.texto").process_result_value(valor, None)  # type: ignore[arg-type]


def test_coluna_json_cifrado_recusa_valor_em_claro() -> None:
    """JSON em claro numa coluna `JsonCifrado` não é desserializado."""
    with pytest.raises(CifraInvalidaError):
        JsonCifrado("evidencia.trecho").process_result_value('{"a": 1}', None)  # type: ignore[arg-type]


def test_identidade_do_reu_em_claro_e_recusada() -> None:
    """Nome do réu em claro (sem token do cofre) não é devolvido como está."""
    with pytest.raises(TokenInvalidoError):
        decifrar_identidade(CofreMemoria(), uuid4(), "Fulano de Tal")


def test_identidade_ausente_continua_none() -> None:
    """Documento ausente (None) segue None."""
    assert decifrar_identidade(CofreMemoria(), uuid4(), None) is None


@pytest.mark.integracao
def test_pagina_sem_trechos_grava_lista_vazia_cifrada(sessao: Session, processo_id: UUID) -> None:
    """Sem trechos informados, a lista vazia vai cifrada ao banco e volta como lista vazia."""
    pagina_id = criar_pagina(sessao, processo_id)
    brutos = sessao.execute(
        text("SELECT trechos_ocultos, trechos_suspeitos FROM pagina WHERE id = :id"),
        {"id": pagina_id},
    ).one()
    assert all(valor.startswith("lupa1:") for valor in brutos)
    pagina = sessao.get(PaginaTabela, pagina_id)
    assert pagina is not None
    assert pagina.trechos_ocultos == [] and pagina.trechos_suspeitos == []
