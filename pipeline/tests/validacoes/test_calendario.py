"""Contagem de dias úteis entre duas datas no calendário."""

from datetime import date

from lupa_pipeline.validacoes.calendario import DiaDesconsiderado, Periodo, dias_uteis_entre


def test_dias_uteis_entre_registra_feriado_e_fim_de_semana() -> None:
    """RF-VAL-02. Conta os dias úteis depois do início até o fim e lista os dias pulados."""
    sexta = date(2030, 3, 1)
    contagem, pulados = dias_uteis_entre(
        sexta,
        date(2030, 3, 8),
        {date(2030, 3, 5): "feriado sintético"},
        [Periodo(date(2030, 3, 6), date(2030, 3, 6), "suspensão sintética")],
    )
    assert contagem == 3
    assert pulados == (
        DiaDesconsiderado(date(2030, 3, 2), "sábado"),
        DiaDesconsiderado(date(2030, 3, 3), "domingo"),
        DiaDesconsiderado(date(2030, 3, 5), "feriado: feriado sintético"),
        DiaDesconsiderado(date(2030, 3, 6), "suspensão: suspensão sintética"),
    )


def test_dias_uteis_entre_sem_intervalo_e_zero() -> None:
    """RF-VAL-02. Fim igual ou anterior ao início não conta nenhum dia."""
    assert dias_uteis_entre(date(2030, 3, 4), date(2030, 3, 4), {}, []) == (0, ())
