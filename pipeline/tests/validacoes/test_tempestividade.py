"""Prazos cíveis, origem dos valores e limites de tempestividade."""

from datetime import date

import pytest

from lupa_pipeline.validacoes.civel.tempestividade import executar
from lupa_pipeline.validacoes.modelo import ModeloProcesso
from tests.validacoes.conftest import SUJEITO, criar_fato

REFERENCIA = date(2026, 11, 1)


def _modelo(tipo: str, intimacao: str, interposicao: str, qualidade: str) -> ModeloProcesso:
    pares = {
        "tipo_recurso": tipo,
        "data_intimacao": intimacao,
        "data_interposicao": interposicao,
        "qualidade_recorrente": qualidade,
    }
    return ModeloProcesso([criar_fato(t, v) for t, v in pares.items()], sujeito=SUJEITO)


@pytest.mark.parametrize(
    ("tipo", "qualidade", "protocolo", "prazo", "resultado", "atraso"),
    [
        ("apelacao_civel", "particular", "2026-08-24", 15, "conforme", 0),
        ("apelacao_civel", "particular", "2026-08-25", 15, "atencao", 1),
        ("agravo_interno", "fazenda_publica", "2026-09-15", 30, "conforme", 0),
        ("agravo_instrumento", "defensoria_publica", "2026-09-15", 30, "conforme", 0),
        ("embargos_declaracao", "ministerio_publico", "2026-08-17", 10, "conforme", 0),
        ("embargos_declaracao", "particular", "2026-08-10", 5, "conforme", 0),
    ],
)
def test_prazo_e_dias_uteis_de_atraso_por_classe_e_qualidade(
    tipo: str, qualidade: str, protocolo: str, prazo: int, resultado: str, atraso: int
) -> None:
    """RF-VAL-02: aceita o último dia, apura o atraso e aplica a dobra de cada ente."""
    modelo = _modelo(tipo, "2026-08-03", protocolo, qualidade)
    achado = executar(modelo, REFERENCIA)
    assert achado.resultado == resultado
    assert achado.valores["prazo_dias"] == prazo
    assert achado.valores["atraso_dias_uteis"] == atraso
    assert achado.valores["prazo_em_dobro"] == (qualidade != "particular")
    assert set(achado.fatos_usados) == {f.id for f in modelo.todos}
    assert all(ref["pagina_ids"] for ref in achado.valores["fatos"])


def test_feriado_local_e_recesso_tem_data_e_fonte() -> None:
    """RF-VAL-02: lista a fonte do feriado e da suspensão inclusiva até 20/01."""
    modelo = _modelo("embargos_declaracao", "2026-10-23", "2026-11-03", "particular")
    achado = executar(modelo, REFERENCIA)
    assert achado.valores["vencimento"] == "2026-11-03"
    dias = {dia["data"]: dia for dia in achado.valores["dias_nao_contados"]}
    assert "tjgo.jus.br" in dias["2026-10-30"]["fonte"]
    assert "2026-10-28" not in dias
    modelo = _modelo("embargos_declaracao", "2026-12-18", "2027-01-27", "particular")
    achado = executar(modelo, REFERENCIA)
    assert achado.valores["vencimento"] == "2027-01-27"
    assert {d["data"] for d in achado.valores["dias_nao_contados"]} >= {"2026-12-20", "2027-01-20"}


def test_fato_ausente_identifica_peca_e_conflito_cita_as_duas_fontes() -> None:
    """RF-FAT-02, RF-VAL-02: conflito mostra fatos e valores; ausência aponta onde procurou."""
    modelo = _modelo("apelacao_civel", "2026-08-03", "2026-08-24", "particular")
    demais = [f for f in modelo.todos if f.tipo != "data_intimacao"]
    achado = executar(ModeloProcesso(demais), REFERENCIA)
    assert achado.resultado == "verificar"
    assert achado.valores["faltantes"] == ["data_intimacao"]
    assert "certidão" in achado.explicacao
    divergente = criar_fato("data_intimacao", "2026-08-04")
    conf = executar(ModeloProcesso([*modelo.todos, divergente]), REFERENCIA)
    assert conf.resultado == "verificar"
    assert set(conf.valores["conflitos"][0]["fato_ids"]) == {
        modelo.fatos("data_intimacao")[0].id,
        divergente.id,
    }
    assert set(conf.valores["conflitos"][0]["fato_ids"]) <= set(conf.fatos_usados)
