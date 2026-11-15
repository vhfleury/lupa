"""Chave por hash, `hash_diff` e `hash_nome` do Data Vault (A1; D4, D5; RES-02)."""

import hashlib
from datetime import UTC, date, datetime, timedelta, timezone
from uuid import UUID

import pytest

from lupa_pipeline.dominio.chaves import (
    ChaveInvalidaError,
    chave_hash,
    chave_link,
    hash_diff,
    hash_nome,
    normalizar_cnj,
    normalizar_hash,
)


def test_chave_hash_e_o_sha256_das_partes_unidas_por_barra() -> None:
    """RES-02: o `hk` é o SHA-256 das partes normalizadas unidas por `|` (A1, passo 3)."""
    esperado = hashlib.sha256(b"00012345620258090001|abc|3").digest()
    assert chave_hash(["00012345620258090001", "abc", 3]) == esperado


def test_chave_hash_e_estavel_e_tem_32_bytes() -> None:
    """RES-02: a mesma chave de negócio sempre gera o mesmo `hk` de 32 bytes."""
    primeira = chave_hash(["assessor.um"])
    assert primeira == chave_hash(["assessor.um"])
    assert len(primeira) == 32


def test_chave_hash_e_sensivel_a_ordem() -> None:
    """RES-02: trocar a ordem das partes muda o `hk`."""
    assert chave_hash(["a", "b"]) != chave_hash(["b", "a"])


def test_chave_hash_apara_espacos_e_normaliza_em_nfc() -> None:
    """RES-02: espaços nas pontas e a forma Unicode não mudam o `hk` (A1, passo 1)."""
    decomposto = "João"
    assert chave_hash(["  João "]) == chave_hash([decomposto])


def test_chave_hash_converte_bytes_e_uuid_em_texto() -> None:
    """RES-02: `hk` de outro hub entra como hex minúsculo; UUID, na forma canônica."""
    hk = bytes.fromhex("ab" * 32)
    conversa = UUID("12345678-1234-5678-1234-567812345678")
    assert chave_hash([hk]) == chave_hash(["ab" * 32])
    assert chave_hash([conversa]) == chave_hash([str(conversa)])


def test_chave_hash_recusa_parte_vazia() -> None:
    """RES-02: parte vazia (ou só espaços) é recusada (A1, passo 2)."""
    with pytest.raises(ChaveInvalidaError, match="vazia"):
        chave_hash(["processo", "  "])


def test_chave_hash_aceita_vazia_so_na_posicao_permitida() -> None:
    """RES-02: o `sujeito` vazio é aceito quando a posição é declarada opcional."""
    assert chave_hash(["processo", ""], vazias_permitidas={1}) != chave_hash(["processo"])
    with pytest.raises(ChaveInvalidaError):
        chave_hash(["", "x"], vazias_permitidas={1})


def test_chave_hash_recusa_parte_com_barra_vertical() -> None:
    """RES-02: `|` dentro de uma parte tornaria a chave ambígua e é recusado."""
    with pytest.raises(ChaveInvalidaError, match=r"\|"):
        chave_hash(["a|b"])


def test_chave_hash_recusa_lista_vazia() -> None:
    """RES-02: uma chave de negócio sem partes não tem `hk`."""
    with pytest.raises(ChaveInvalidaError):
        chave_hash([])


def test_normalizar_cnj_deixa_so_os_digitos() -> None:
    """RES-02: número CNJ com ou sem máscara gera a mesma parte (A1, passo 1)."""
    assert normalizar_cnj("0001234-56.2025.8.09.0001") == "00012345620258090001"
    assert normalizar_cnj(" 00012345620258090001 ") == "00012345620258090001"


def test_normalizar_hash_poe_em_minusculas() -> None:
    """RES-02: hash hexadecimal em maiúsculas vira minúsculas (A1, passo 1)."""
    assert normalizar_hash(" ABCDEF ") == "abcdef"


def test_chave_link_e_o_sha256_dos_hex_dos_hubs() -> None:
    """RES-02: o `hk` do link une os hex dos `hk` dos hubs por `|` (A1, passo 4)."""
    hk_a, hk_b = bytes(32), bytes([1]) * 32
    esperado = hashlib.sha256(f"{hk_a.hex()}|{hk_b.hex()}".encode()).digest()
    assert chave_link(hk_a, hk_b) == esperado
    assert chave_link(hk_a, hk_b) != chave_link(hk_b, hk_a)


def test_chave_link_recusa_hk_com_tamanho_errado() -> None:
    """RES-02: só `hk` de 32 bytes formam um link."""
    with pytest.raises(ChaveInvalidaError):
        chave_link(bytes(31), bytes(32))


def test_hash_diff_e_sha256_do_json_canonico() -> None:
    """D5: `hash_diff` é o SHA-256 do JSON com chaves ordenadas e sem espaços (A1, passo 5)."""
    esperado = hashlib.sha256(b'{"ativo":true,"papel":"assessor"}').digest()
    assert hash_diff({"papel": "assessor", "ativo": True}) == esperado


def test_hash_diff_nao_depende_da_ordem_dos_atributos() -> None:
    """D5: a ordem em que os atributos chegam não muda o `hash_diff`."""
    assert hash_diff({"a": 1, "b": [1, 2]}) == hash_diff({"b": [1, 2], "a": 1})


def test_hash_diff_muda_quando_um_atributo_muda() -> None:
    """D5: qualquer atributo diferente gera outro `hash_diff`."""
    assert hash_diff({"ativo": True}) != hash_diff({"ativo": False})


def test_hash_diff_serializa_datas_bytes_e_uuid() -> None:
    """D5: datas em ISO (instantes em UTC), bytes em hex e UUID em texto."""
    instante = datetime(2025, 3, 10, 9, 0, tzinfo=timezone(timedelta(hours=-3)))
    em_utc = datetime(2025, 3, 10, 12, 0, tzinfo=UTC)
    assert hash_diff({"t": instante}) == hash_diff({"t": em_utc})
    assert hash_diff({"d": date(2025, 3, 10)}) == hash_diff({"d": "2025-03-10"})
    assert hash_diff({"h": [bytes(2)]}) == hash_diff({"h": ["0000"]})
    conversa = UUID(int=7)
    assert hash_diff({"u": conversa}) == hash_diff({"u": str(conversa)})


def test_hash_diff_recusa_tipo_sem_forma_canonica() -> None:
    """D5: valor sem serialização canônica é recusado em vez de virar texto arbitrário."""
    with pytest.raises(TypeError):
        hash_diff({"x": object()})


def test_hash_nome_e_o_sha256_do_texto() -> None:
    """RF-SEG-01 (D7): a `chave_nome` da parte é o SHA-256 do nome normalizado."""
    assert hash_nome("Parte Sintética") == hashlib.sha256("Parte Sintética".encode()).digest()
    assert hash_nome("Parte Sintética") != hash_nome("Outra Parte Sintética")
