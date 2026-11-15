"""Número CNJ: validação e máscara de exibição (RF-PRO-01)."""

import pytest

from lupa_pipeline.dominio.chaves import normalizar_cnj
from lupa_pipeline.dominio.cnj import formatar_numero_cnj

NUMERO = "0004321-78.2025.8.09.0001"


def test_mascara_devolve_o_numero_cadastrado_a_partir_dos_digitos_do_hub() -> None:
    """RF-PRO-01: o hub guarda só dígitos; a resposta mostra o número com máscara."""
    assert formatar_numero_cnj(normalizar_cnj(NUMERO)) == NUMERO


@pytest.mark.parametrize("texto", ["123", "0004321152025809000A", ""])
def test_mascara_nao_altera_texto_que_nao_tem_vinte_digitos(texto: str) -> None:
    """RF-PRO-01: texto fora do formato do hub volta como veio."""
    assert formatar_numero_cnj(texto) == texto
