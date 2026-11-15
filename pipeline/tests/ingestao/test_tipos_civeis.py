"""Classificação cível de títulos e sinais de autoria (RF-PEC-01)."""

import pytest

from lupa_pipeline.ingestao.classificacao import classificar_origem, classificar_tipo


@pytest.mark.parametrize(
    ("tipo", "titulo"),
    [
        ("peticao_inicial", "PETIÇÃO INICIAL"),
        ("contestacao", "CONTESTAÇÃO"),
        ("replica", "RÉPLICA"),
        ("decisao_interlocutoria", "DECISÃO INTERLOCUTÓRIA"),
        ("sentenca", "SENTENÇA"),
        ("embargos_declaracao", "EMBARGOS DE DECLARAÇÃO"),
        ("apelacao", "APELAÇÃO"),
        ("agravo_instrumento", "AGRAVO DE INSTRUMENTO"),
        ("agravo_interno", "AGRAVO INTERNO"),
        ("contrarrazoes", "CONTRARRAZÕES"),
        ("acordao", "ACÓRDÃO"),
        ("certidao", "CERTIDÃO"),
        ("procuracao", "PROCURAÇÃO"),
        ("comprovante_preparo", "COMPROVANTE DE PREPARO"),
        ("laudo_pericial", "LAUDO PERICIAL"),
        ("parecer_mp", "PARECER DO MINISTÉRIO PÚBLICO"),
        ("outros", "TERMO DE JUNTADA"),
    ],
)
def test_tipo_pelo_titulo_civel(tipo: str, titulo: str) -> None:
    """RF-PEC-01: cada peça prevista na especificação tem classificação pelo título."""
    assert classificar_tipo([titulo]).valor == tipo


def test_sem_indicio_eh_outros_e_cargo_do_advogado_eh_parte() -> None:
    """RF-PEC-01: uma folha sem título não recebe tipo específico; OAB identifica parte."""
    assert classificar_tipo(["documento sintético avulso"]).valor == "outros"
    assert classificar_origem(["Por seu advogado", "OAB/GO 00123"]).valor == "parte"
