"""Testes de `lupa_web.rotulos`: rótulos e datas das telas."""

import pytest

from lupa_web import rotulos


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("2026-03-04", "04/03/2026"),
        ("2026-03-04T15:30:00+00:00", "04/03/2026 12:30"),
        ("2026-03-04T15:30:00", "04/03/2026 15:30"),
        ("texto", "texto"),
        (None, "—"),
        ("", "—"),
    ],
)
def test_formatar_data_no_formato_brasileiro(valor: str | None, esperado: str) -> None:
    """RF-INT-02: datas da API aparecem como DD/MM/AAAA, com hora no fuso de Brasília."""
    assert rotulos.formatar_data(valor) == esperado


def test_legivel_usa_rotulo_conhecido_ou_a_chave_com_espacos() -> None:
    """RF-INT-02: códigos conhecidos têm rótulo; os demais viram frase."""
    assert rotulos.legivel("apelacao_civel") == "Apelação cível"
    assert rotulos.legivel("sem_arquivos") == "Sem arquivos"
    assert rotulos.legivel("pagina_em_branco") == "Pagina em branco"


def test_motivos_de_quarentena_e_falha_tem_frase_para_o_usuario() -> None:
    """RF-INT-04: motivo conhecido vira frase; desconhecido ou ausente, frase genérica."""
    assert rotulos.motivo_quarentena("senha").startswith("O arquivo está protegido")
    assert rotulos.motivo_quarentena("novo_motivo") == "Arquivo recusado (Novo motivo)."
    assert rotulos.motivo_quarentena(None) == "Arquivo recusado."
    assert rotulos.motivo_falha("erro_parser") == "Erro ao ler o PDF."
    assert rotulos.motivo_falha("outro") == "Falha no processamento (Outro)."
    assert rotulos.motivo_falha(None) == "Falha no processamento."
