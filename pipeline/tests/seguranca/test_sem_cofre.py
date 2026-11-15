"""Dados gravados em claro, sem cofre nem cifra na aplicação (RF-SEG-01)."""

import hashlib
import importlib.util
import inspect
import io
import json

import pytest
from sqlalchemy import Column, create_engine

from lupa_pipeline.config import Settings
from lupa_pipeline.dominio import chaves
from lupa_pipeline.dominio.tabelas import sat_fato_valor, sat_pagina_extracao
from lupa_pipeline.ingestao.storage import ArmazenamentoMemoria, criar_storage

MODULOS_REMOVIDOS = ["cofre", "contexto", "chaves", "envelope", "tipos"]
PREFIXO_CIFRA = "lupa1:"
DIALETO = create_engine("postgresql+psycopg://").dialect


def _gravar_no_banco(coluna: Column[object], valor: object) -> object:
    processador = coluna.type.bind_processor(DIALETO)
    return processador(valor) if processador else valor


def test_hash_nome_e_sha256_do_texto_sem_chave() -> None:
    """RF-SEG-01: hash_nome é o SHA-256 determinístico do texto, com 32 bytes."""
    esperado = hashlib.sha256("Parte Sintética".encode()).digest()
    assert chaves.hash_nome("Parte Sintética") == esperado
    assert chaves.hash_nome("Parte Sintética") == chaves.hash_nome("Parte Sintética")
    assert len(esperado) == chaves.TAMANHO_HK


def test_hash_diff_nao_aceita_dek_e_e_sha256_do_json_canonico() -> None:
    """RF-SEG-01: hash_diff não recebe DEK e é o SHA-256 do JSON canônico."""
    atributos = {"texto": "conteúdo sintético", "numero": 1}
    assert "dek" not in inspect.signature(chaves.hash_diff).parameters
    esperado = hashlib.sha256(chaves.json_canonico(atributos)).digest()
    assert chaves.hash_diff(atributos) == esperado


def test_storage_em_memoria_grava_os_bytes_originais(settings_ficticias: Settings) -> None:
    """RF-SEG-01: o storage em memória guarda e devolve os bytes sem cabeçalho LUPAOBJ."""
    settings = settings_ficticias.model_copy(update={"storage_backend": "memoria"})
    storage = criar_storage(settings)
    assert isinstance(storage, ArmazenamentoMemoria)
    conteudo = b"%PDF-1.4 conteudo sintetico"
    chave = f"processos/{'ab' * 32}/{'cd' * 32}.pdf"
    storage.gravar(chave, io.BytesIO(conteudo))
    assert storage.ler(chave) == conteudo
    gravado = storage._objetos[chave]
    assert gravado == conteudo
    assert not gravado.startswith(b"LUPAOBJ")


@pytest.mark.parametrize("modulo", MODULOS_REMOVIDOS)
def test_modulos_de_cifra_nao_existem(modulo: str) -> None:
    """RF-SEG-01: os módulos do cofre e da cifra foram removidos."""
    assert importlib.util.find_spec(f"lupa_pipeline.seguranca.{modulo}") is None


def test_coluna_de_texto_de_conteudo_grava_em_claro() -> None:
    """RF-SEG-01: o texto da página vai ao banco como está, sem processo ativo."""
    texto = "Texto sintético da página"
    gravado = _gravar_no_banco(sat_pagina_extracao.c.texto, texto)
    assert gravado == texto


def test_coluna_json_de_conteudo_grava_em_claro() -> None:
    """RF-SEG-01: o valor do fato vai ao banco como JSON em claro, sem prefixo de cifra."""
    valor = {"data": "2026-01-15", "observacao": "intimação sintética"}
    gravado = _gravar_no_banco(sat_fato_valor.c.valor, valor)
    serializado = gravado if isinstance(gravado, str) else json.dumps(gravado)
    assert not serializado.startswith(PREFIXO_CIFRA)
    assert json.loads(serializado) == valor
