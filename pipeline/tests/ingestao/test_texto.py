"""Testes do dobramento de texto único da ingestão."""

from lupa_pipeline.ingestao.texto import (
    colapsar_espacos,
    dobrar,
    levenshtein,
    maiusculas_sem_acento,
)


def test_dobrar_preserva_o_comprimento_com_caractere_que_muda_de_tamanho() -> None:
    """RNF-08: dobrar mantém um caractere por caractere, mesmo quando lower() aumenta o tamanho."""
    texto = "İSTANBUL Ação"
    assert dobrar(texto) == "istanbul acao"
    assert len(dobrar(texto)) == len(texto)


def test_levenshtein_com_prefixo_e_sufixo_comuns() -> None:
    """RNF-08: a distância é a mesma com e sem prefixo e sufixo comuns."""
    assert levenshtein("prefixo abc sufixo", "prefixo abd sufixo") == 1
    assert levenshtein("abc", "abd") == levenshtein("abd", "abc") == 1
    assert levenshtein("", "abc") == 3
    assert levenshtein("kitten", "sitting") == 3


def test_colapsar_espacos_aplica_nfc() -> None:
    """RNF-08: espaços e quebras viram um espaço, e o texto sai na forma NFC."""
    decomposto = "Ação"
    assert colapsar_espacos(f"  {decomposto}\n de\tteste ") == "Ação de teste"


def test_maiusculas_sem_acento_remove_pontuacao() -> None:
    """RNF-08: maiúsculas sem acento, sem pontuação, preservando a barra e os dígitos."""
    assert maiusculas_sem_acento("Petição, inicial: fls. 1/2") == "PETICAO INICIAL FLS 1/2"
