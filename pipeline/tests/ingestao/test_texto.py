"""Testes do dobramento de texto único da ingestão."""

from lupa_pipeline.ingestao.texto import dobrar


def test_dobrar_preserva_o_comprimento_com_caractere_que_muda_de_tamanho() -> None:
    """RNF-08: dobrar mantém um caractere por caractere, mesmo quando lower() aumenta o tamanho."""
    texto = "İSTANBUL Ação"
    assert dobrar(texto) == "istanbul acao"
    assert len(dobrar(texto)) == len(texto)
