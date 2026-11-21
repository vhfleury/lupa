"""Contagem de prazos em dias úteis, com feriados e suspensões vindos de dados."""

import calendar
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

_UM_DIA = timedelta(days=1)
_SABADO = 5
_DOMINGO = 6
_MESES_NO_ANO = 12


@dataclass(frozen=True)
class Periodo:
    """Período de suspensão de prazos, inclusivo nas duas pontas."""

    inicio: date
    fim: date
    descricao: str
    fonte: str = ""
    anual: bool = False

    def contem(self, dia: date) -> bool:
        """Diz se o dia está no período.

        Args:
            dia: Dia a testar.

        Returns:
            Verdadeiro se ``inicio <= dia <= fim``.
        """
        if not self.anual:
            return self.inicio <= dia <= self.fim
        inicio = (self.inicio.month, self.inicio.day)
        fim = (self.fim.month, self.fim.day)
        atual = (dia.month, dia.day)
        if inicio > fim:
            return atual >= inicio or atual <= fim
        return inicio <= atual <= fim


@dataclass(frozen=True)
class FeriadoCalendario:
    """Feriado indexado no calendário, com a fonte que o declara."""

    descricao: str
    fonte: str = ""


@dataclass(frozen=True)
class Calendario:
    """Feriados e suspensões usados na contagem."""

    feriados: Mapping[date, FeriadoCalendario] = field(default_factory=dict)
    suspensoes: Sequence[Periodo] = ()

    def fonte_em(self, dia: date) -> str:
        """Identifica a origem da exclusão de um dia da contagem."""
        if dia in self.feriados:
            feriado = self.feriados[dia]
            return feriado.fonte or feriado.descricao
        for periodo in self.suspensoes:
            if periodo.contem(dia):
                return periodo.fonte or periodo.descricao
        return "art. 216 do CPC"


@dataclass(frozen=True)
class DiaDesconsiderado:
    """Dia pulado ou que deslocou o vencimento, com o motivo."""

    data: date
    motivo: str


@dataclass(frozen=True)
class ResultadoPrazo:
    """Resultado de uma contagem de prazo."""

    data_base: date
    dias: int
    vencimento_nominal: date
    vencimento: date
    deslocamentos: tuple[DiaDesconsiderado, ...]
    dias_suspensos: tuple[DiaDesconsiderado, ...]


def motivo_suspensao(dia: date, suspensoes: Sequence[Periodo]) -> str | None:
    """Retorna a descrição da suspensão que cobre o dia, se houver.

    Args:
        dia: Dia a testar.
        suspensoes: Períodos de suspensão.

    Returns:
        Descrição prefixada ou ``None``.
    """
    for periodo in suspensoes:
        if periodo.contem(dia):
            return f"suspensão: {periodo.descricao}"
    return None


def motivo_sem_expediente(
    dia: date, feriados: Mapping[date, FeriadoCalendario], suspensoes: Sequence[Periodo]
) -> str | None:
    """Diz por que o dia não tem expediente forense, ou ``None`` se tem.

    Args:
        dia: Dia a testar.
        feriados: Feriados por data.
        suspensoes: Períodos de suspensão.

    Returns:
        Motivo (feriado, suspensão, sábado, domingo) ou ``None``.
    """
    if dia in feriados:
        return f"feriado: {feriados[dia].descricao}"
    suspenso = motivo_suspensao(dia, suspensoes)
    if suspenso is not None:
        return suspenso
    if dia.weekday() == _SABADO:
        return "sábado"
    if dia.weekday() == _DOMINGO:
        return "domingo"
    return None


def _dias_seguintes(
    inicio: date, feriados: Mapping[date, FeriadoCalendario], suspensoes: Sequence[Periodo]
) -> Iterator[tuple[date, str | None]]:
    dia = inicio
    while True:
        dia += _UM_DIA
        yield dia, motivo_sem_expediente(dia, feriados, suspensoes)


def contar_prazo_util(
    data_base: date,
    dias: int,
    feriados: Mapping[date, FeriadoCalendario],
    suspensoes: Sequence[Periodo],
) -> ResultadoPrazo:
    """Conta prazo em dias úteis (para o módulo cível), excluindo o dia do começo.

    Args:
        data_base: Dia do começo.
        dias: Quantidade de dias úteis.
        feriados: Feriados por data.
        suspensoes: Períodos de suspensão.

    Returns:
        Resultado com os dias não úteis pulados em ``dias_suspensos``.
    """
    contados = 0
    atual = data_base
    pulados: list[DiaDesconsiderado] = []
    if dias <= 0:
        return ResultadoPrazo(data_base, dias, atual, atual, (), ())
    for atual, motivo in _dias_seguintes(data_base, feriados, suspensoes):
        if motivo is not None:
            pulados.append(DiaDesconsiderado(atual, motivo))
            continue
        contados += 1
        if contados == dias:
            break
    return ResultadoPrazo(data_base, dias, atual, atual, (), tuple(pulados))


def dias_uteis_entre(
    inicio: date,
    fim: date,
    feriados: Mapping[date, FeriadoCalendario],
    suspensoes: Sequence[Periodo],
) -> tuple[int, tuple[DiaDesconsiderado, ...]]:
    """Conta os dias úteis depois de ``inicio`` até ``fim``, inclusive.

    Args:
        inicio: Dia anterior ao primeiro contado.
        fim: Último dia contado.
        feriados: Feriados por data.
        suspensoes: Períodos de suspensão.

    Returns:
        Quantidade de dias úteis e os dias sem expediente pulados, em ordem.
    """
    contados = 0
    pulados: list[DiaDesconsiderado] = []
    if fim <= inicio:
        return contados, ()
    for dia, motivo in _dias_seguintes(inicio, feriados, suspensoes):
        if motivo is None:
            contados += 1
        else:
            pulados.append(DiaDesconsiderado(dia, motivo))
        if dia == fim:
            break
    return contados, tuple(pulados)


def somar_meses(dia: date, meses: int) -> date:
    """Soma meses de calendário, ajustando para o último dia quando o mês é mais curto.

    Args:
        dia: Data inicial.
        meses: Meses a somar.

    Returns:
        Data resultante.
    """
    anos, mes_indice = divmod(dia.month - 1 + meses, _MESES_NO_ANO)
    ano = dia.year + anos
    mes = mes_indice + 1
    return date(ano, mes, min(dia.day, calendar.monthrange(ano, mes)[1]))


def idade_em(nascimento: date, dia: date) -> int:
    """Calcula a idade em anos completos.

    Args:
        nascimento: Data de nascimento.
        dia: Data em que a idade é medida.

    Returns:
        Anos completos.
    """
    aniversario_passou = (dia.month, dia.day) >= (nascimento.month, nascimento.day)
    return dia.year - nascimento.year - (0 if aniversario_passou else 1)
