"""Vocabulário da classificação e da extração cível."""

from lupa_pipeline.dominio.enums import MetodoClassificacao, OrigemPeca, TipoFato, TipoPeca


def test_pecas_correspondem_a_secao_tres_da_especificacao() -> None:
    """RF-PEC-01: classificação usa os dezessete tipos cíveis e os métodos permitidos."""
    assert set(TipoPeca) == {
        "peticao_inicial",
        "contestacao",
        "replica",
        "decisao_interlocutoria",
        "sentenca",
        "embargos_declaracao",
        "apelacao",
        "agravo_instrumento",
        "agravo_interno",
        "contrarrazoes",
        "acordao",
        "certidao",
        "procuracao",
        "comprovante_preparo",
        "laudo_pericial",
        "parecer_mp",
        "outros",
    }
    assert set(OrigemPeca) == {"juizo", "mp", "parte", "terceiro", "desconhecida"}
    assert set(MetodoClassificacao) == {"regra", "manual"}


def test_fatos_cobrem_os_dados_das_validacoes_e_os_marcos() -> None:
    """RF-FAT-01: enum aceita os quinze tipos de fato da especificação cível."""
    assert set(TipoFato) == {
        "data_decisao_recorrida",
        "data_intimacao",
        "tipo_recurso",
        "data_interposicao",
        "qualidade_recorrente",
        "comprovante_preparo",
        "gratuidade_pedido",
        "gratuidade_decisao",
        "advogado_subscritor",
        "procuracao",
        "hipotese_decisao_agravada",
        "data_ajuizamento",
        "data_citacao",
        "data_contestacao",
        "data_acordao",
    }
