"""Comparação cível por recorrente, valores e páginas, mesmo quando os ids físicos mudam."""

from lupa_pipeline.dominio.enums import ResultadoAchado
from lupa_pipeline.sinteticos.achados import comparar
from lupa_pipeline.sinteticos.gabarito import ResultadoEsperado


def test_mesma_regra_para_partes_diferentes_e_achado_imprevisto() -> None:
    """Um resultado atribuído à segunda parte não pode encobrir o da primeira."""
    a = ResultadoEsperado(
        validacao="preparo_recurso",
        sujeito="Parte A",
        resultado=ResultadoAchado.CONFORME,
        valores={},
        explicacao="Pago",
    )
    b = a.model_copy(
        update={"sujeito": "Parte B", "resultado": ResultadoAchado.ATENCAO, "explicacao": "Ausente"}
    )
    extra = a.model_copy(update={"sujeito": "Parte C"})
    comparacoes = comparar([a, b], [b, a, extra])
    assert len(comparacoes) == 3
    assert sorted(c.sujeito for c in comparacoes if c.resultado_igual and c.valores_iguais) == [
        "Parte A",
        "Parte B",
    ]
    assert [c.sujeito for c in comparacoes if c.esperado is None] == ["Parte C"]


def test_hk_distinto_de_fato_e_pagina_so_bate_se_a_fonte_continua_na_mesma_folha() -> None:
    """Mantém a localização das referências e a ordem do mandato ao normalizar ids da execução."""

    def mandato(prefixo: str) -> dict[str, object]:
        return {
            "fatos": [
                {
                    "fato_id": prefixo + "1",
                    "tipo": "procuracao",
                    "valor": {"outorgante": prefixo + "A"},
                    "pagina_ids": [prefixo + "p"],
                    "evidencia_ids": [prefixo + "e"],
                },
                {
                    "fato_id": prefixo + "2",
                    "tipo": "qualidade_recorrente",
                    "valor": "particular",
                    "pagina_ids": [prefixo + "q"],
                },
            ],
            "cadeia": [prefixo + "1"],
            "paginas_mandato": [prefixo + "p"],
        }

    esperado = ResultadoEsperado(
        validacao="representacao_recurso",
        sujeito="Parte A",
        resultado=ResultadoAchado.CONFORME,
        explicacao="Mandato",
        valores=mandato("g"),
    )
    valores = mandato("b")
    assert isinstance(valores["fatos"], list)
    valores["fatos"].reverse()
    obtido = esperado.model_copy(update={"valores": valores, "sujeito": "bA"})
    gabarito = {"gA": "Parte A", "gp": "folha 3", "gq": "folha 5"}
    banco = {"bA": "Parte A", "bp": "folha 3", "bq": "folha 5"}
    assert comparar([esperado], [obtido], gabarito, banco)[0].valores_iguais
    errado = comparar([esperado], [obtido], gabarito, banco | {"bp": "folha 4"})[0]
    assert errado.resultado_igual and not errado.valores_iguais
