"""Vínculo entre recorrente e subscritor, inclusive substabelecimentos sucessivos."""

from datetime import date
from typing import Any

import pytest

from lupa_pipeline.validacoes.civel.representacao import executar
from lupa_pipeline.validacoes.modelo import AchadoValidacao, ModeloProcesso
from tests.validacoes.conftest import PAGINA_SINTETICA, SUJEITO, criar_fato

A = {"nome": "Ada Sintética", "oab": "GO 111"}
B = {"nome": "Beatriz Sintética", "oab": "GO 222"}
C = {"nome": "Clara Sintética", "oab": "GO 333"}


def _apurar(
    qualidade: str, advogado: dict[str, str] | None, documentos: list[dict[str, Any]]
) -> AchadoValidacao:
    fatos = [criar_fato("qualidade_recorrente", qualidade)]
    if advogado is not None:
        fatos.append(criar_fato("advogado_subscritor", advogado))
    fatos.extend(criar_fato("procuracao", d) for d in documentos)
    return executar(ModeloProcesso(fatos, sujeito=SUJEITO), date(2026, 8, 10))


def test_procuracao_e_substabelecimentos_ligam_recorrente_ao_subscritor() -> None:
    """RF-VAL-04: reconstrói a cadeia por OAB e cita a página do mandato de origem."""
    docs = [
        {"outorgante": SUJEITO, "advogado": A},
        {"outorgante": A, "advogado": B, "tipo": "substabelecimento"},
        {"outorgante": B, "advogado": C, "tipo": "substabelecimento"},
    ]
    achado = _apurar("particular", {"nome": "Outra grafia", "oab": "go-333"}, docs[::-1])
    assert achado.resultado == "conforme"
    assert achado.valores["paginas_mandato"] == [PAGINA_SINTETICA]
    assert len(achado.fatos_usados) == 5
    assert _apurar("particular", A, docs[:1]).resultado == "conforme"
    assert _apurar("particular", {"nome": "ada sintetica"}, docs[:1]).resultado == "conforme"


@pytest.mark.parametrize(
    ("advogado", "docs", "esperado"),
    [
        (A, [], "atencao"),
        (None, [], "verificar"),
        ({}, [], "verificar"),
        (A, [{"outorgante": "outro recorrente", "advogado": A}], "atencao"),
        (A, [{"outorgante": SUJEITO, "advogado": {"nome": A["nome"], "oab": "GO 444"}}], "atencao"),
        (
            A,
            [
                {"outorgante": A, "advogado": B, "tipo": "substabelecimento"},
                {"outorgante": B, "advogado": A, "tipo": "substabelecimento"},
            ],
            "atencao",
        ),
    ],
)
def test_assinatura_ausente_e_outorga_sem_vinculo(
    advogado: dict[str, str] | None, docs: list[dict[str, Any]], esperado: str
) -> None:
    """RF-VAL-04: exige assinatura, identidade e uma cadeia que comece no recorrente."""
    assert _apurar("particular", advogado, docs).resultado == esperado


@pytest.mark.parametrize(
    "qualidade", ["fazenda_publica", "defensoria_publica", "ministerio_publico"]
)
def test_representacao_da_entidade_dispensa_mandato(qualidade: str) -> None:
    """RF-VAL-04: registra a razão da dispensa de mandato da entidade."""
    achado = _apurar(qualidade, None, [])
    assert achado.resultado == "conforme"
    assert "dispensa" in achado.explicacao.lower()
