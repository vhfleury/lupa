"""Fatos da capa no fluxo de candidatos e evidência (RF-FAT-01)."""

from lupa_pipeline.dominio.enums import TipoPeca
from lupa_pipeline.ingestao.eventos.base import Fonte
from lupa_pipeline.ingestao.eventos.capa import extrair
from lupa_pipeline.ingestao.eventos.fatos import candidatos_da_peca, confirmar
from lupa_pipeline.ingestao.eventos.modelo import PaginaTexto, PecaTexto


def test_dados_da_capa_mantem_o_intervalo_do_valor_sem_sujeito() -> None:
    """RF-FAT-01: os seis fatos têm valor normalizado e evidência só do valor literal."""
    texto = (
        "Relator: Ana de Teste\nÓRGÃO JULGADOR: Câmara Sintética  \nAssunto: Compra e venda\n"
        "Valor da causa: R$ 1.234,56\nComarca: Teste\nDistribuição: 15 de março de 2026"
    )
    pagina = PaginaTexto("e" * 64, 1, texto, texto)
    peca = PecaTexto(TipoPeca.OUTROS, (pagina,))
    esperados = {
        "relator": ("Ana de Teste", "Ana de Teste"),
        "orgao_julgador": ("Câmara Sintética", "Câmara Sintética"),
        "assunto": ("Compra e venda", "Compra e venda"),
        "valor_causa": ("1234.56", "R$ 1.234,56"),
        "juizo_origem": ("Teste", "Teste"),
        "data_distribuicao": ("2026-03-15", "15 de março de 2026"),
    }
    obtidos = {}
    for candidato in candidatos_da_peca(peca, {}):
        fato = confirmar(candidato, "a" * 64)
        assert fato and fato.sujeito == ""
        (evidencia,) = fato.evidencias
        assert texto[evidencia.inicio : evidencia.fim] == evidencia.trecho
        obtidos[fato.tipo.value] = (fato.valor, evidencia.trecho)
    assert obtidos == esperados


def test_descarta_valores_invalidos_e_limita_por_numero_absoluto_da_pagina() -> None:
    """RF-FAT-01: ignora moeda e data inválidas e rótulos em páginas além do limite."""
    invalida = "Valor da causa: R$ 1.2,34\nData de distribuição: 31/02/2026\nAssunto: Um"
    posterior = "Assunto: Outro"
    paginas = (
        PaginaTexto("d" * 64, 2, invalida, invalida),
        PaginaTexto("e" * 64, 3, posterior, posterior),
    )
    peca = PecaTexto(TipoPeca.OUTROS, paginas)
    candidatos = list(candidatos_da_peca(peca, {}, identificacao_paginas=2))
    assert [(c.tipo.value, c.valor) for c in candidatos] == [("assunto", "Um")]


def test_campo_da_capa_nao_herda_o_recorrente_da_peca() -> None:
    """RF-FAT-01: fatos de autuação pertencem ao processo mesmo em peça com recorrente."""
    texto = "Relator: Nome Sintético"
    pagina = PaginaTexto("a" * 64, 1, texto, texto)
    (relator,) = extrair(Fonte(pagina, "b" * 64))
    assert relator.sujeito == ""
