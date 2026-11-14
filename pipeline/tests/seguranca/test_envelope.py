"""Formatos de cifra: campo `lupa1:` e objeto `LUPAOBJ` (RF-SEG-01; D14)."""

import base64
import io
import os

import pytest

from lupa_pipeline.seguranca.envelope import (
    TAMANHO_BLOCO,
    CifraInvalidaError,
    LeitorCifrado,
    campo_cifrado,
    cifrar_campo,
    cifrar_stream,
    decifrar_campo,
    decifrar_objeto,
    gerar_dek,
    objeto_cifrado,
    processo_do_campo,
)


def test_campo_ida_e_volta_e_cabecalho() -> None:
    """RF-SEG-01: o campo decifra com a DEK e o rótulo certos e leva o `hk_processo`."""
    dek, processo = gerar_dek(), os.urandom(32)
    campo = cifrar_campo(dek, processo, "pagina.texto", "Certidão de intimação")
    assert campo_cifrado(campo) and "Certidão" not in campo
    assert processo_do_campo(campo) == processo
    assert decifrar_campo(dek, campo, "pagina.texto") == "Certidão de intimação"


def test_campo_recusa_chave_rotulo_ou_adulteracao() -> None:
    """DEK de outro processo, outra coluna ou um byte trocado: recusado."""
    dek, processo = gerar_dek(), os.urandom(32)
    campo = cifrar_campo(dek, processo, "pagina.texto", "texto")
    with pytest.raises(CifraInvalidaError):
        decifrar_campo(gerar_dek(), campo, "pagina.texto")
    with pytest.raises(CifraInvalidaError):
        decifrar_campo(dek, campo, "mensagem.texto")
    adulterado = campo[:-4] + ("AAAA" if not campo.endswith("AAAA") else "BBBB")
    with pytest.raises(CifraInvalidaError):
        decifrar_campo(dek, adulterado, "pagina.texto")
    with pytest.raises(CifraInvalidaError):
        decifrar_campo(dek, "lupa1:@@@", "pagina.texto")
    with pytest.raises(CifraInvalidaError):
        decifrar_campo(dek, "lupa1:AAAA", "pagina.texto")


def test_campo_recusa_processo_sem_hk_de_32_bytes() -> None:
    """D14: o cabeçalho do campo é o `hk_processo`; outro tamanho é recusado."""
    with pytest.raises(ValueError, match="32 bytes"):
        cifrar_campo(gerar_dek(), os.urandom(16), "sat_pagina_extracao.texto", "texto")


def test_campo_de_outro_processo_nao_decifra_com_o_hk_trocado() -> None:
    """RF-SEG-01: o `hk` do processo entra no AAD; trocar o cabeçalho invalida o campo."""
    dek = gerar_dek()
    campo = cifrar_campo(dek, bytes(32), "sat_pagina_extracao.texto", "texto")
    bruto = base64.b64decode(campo.removeprefix("lupa1:"))
    trocado = "lupa1:" + base64.b64encode(bytes([1]) * 32 + bruto[32:]).decode()
    with pytest.raises(CifraInvalidaError):
        decifrar_campo(dek, trocado, "sat_pagina_extracao.texto")


@pytest.mark.parametrize(
    "tamanho", [0, 1, 100, TAMANHO_BLOCO - 1, TAMANHO_BLOCO, TAMANHO_BLOCO + 1, 3 * TAMANHO_BLOCO]
)
def test_objeto_ida_e_volta(tamanho: int) -> None:
    """Objeto de qualquer tamanho (inclusive fronteira de bloco) volta igual."""
    dek = gerar_dek()
    claro = bytes(i % 251 for i in range(tamanho))
    cifrado = b"".join(cifrar_stream(dek, io.BytesIO(claro)))
    assert objeto_cifrado(cifrado)
    assert decifrar_objeto(dek, cifrado) == claro
    assert io.BufferedReader(LeitorCifrado(dek, io.BytesIO(claro))).read()[:7] == b"LUPAOBJ"


def test_objeto_recusa_truncado_chave_errada_e_versao() -> None:
    """Truncar no limite de bloco, outra DEK, cabeçalho desconhecido: recusado."""
    dek = gerar_dek()
    claro = b"%PDF-" + b"x" * (2 * TAMANHO_BLOCO)
    cifrado = b"".join(cifrar_stream(dek, io.BytesIO(claro)))
    cabecalho = 7 + 1 + 4 + 16
    with pytest.raises(CifraInvalidaError):
        decifrar_objeto(dek, cifrado[: cabecalho + TAMANHO_BLOCO + 16])
    with pytest.raises(CifraInvalidaError):
        decifrar_objeto(gerar_dek(), cifrado)
    with pytest.raises(CifraInvalidaError):
        decifrar_objeto(dek, cifrado[:7] + b"\x09" + cifrado[8:])
    with pytest.raises(CifraInvalidaError):
        decifrar_objeto(dek, b"%PDF-1.7")
    with pytest.raises(CifraInvalidaError):
        decifrar_objeto(dek, cifrado[:cabecalho] + b"curto")
