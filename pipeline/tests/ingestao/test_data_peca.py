"""Regras da data da peça (4E.6): preferência e direção da busca nas páginas."""

from lupa_pipeline.ingestao.data_peca import DO_FIM, DO_INICIO, REGRAS


def test_regra_declara_a_direcao_da_busca() -> None:
    """RF-ING-03 e RNF-08: cada regra traz a direção; só a de juntada busca do início."""
    direcoes = [(tipo, direcao) for tipo, _, direcao in REGRAS]
    assert direcoes == [
        ("protocolo", DO_FIM),
        ("assinatura", DO_FIM),
        ("assinatura", DO_FIM),
        ("juntada", DO_INICIO),
    ]
