"""Valida o recurso da classe do processo para cada recorrente (D16)."""

from datetime import date

from lupa_pipeline.dominio.enums import ResultadoAchado
from lupa_pipeline.logging import get_logger
from lupa_pipeline.validacoes.apoio import renderizar
from lupa_pipeline.validacoes.catalogo import Validacao, validacoes_de
from lupa_pipeline.validacoes.modelo import AchadoValidacao, ModeloProcesso
from lupa_pipeline.validacoes.versao import VERSAO_CATALOGO

_log = get_logger(__name__)


def _executar(regra: Validacao, modelo: ModeloProcesso, referencia: date) -> AchadoValidacao:
    try:
        return regra.executar(modelo, referencia)
    except Exception as erro:
        _log.warning("validacao_falhou", validacao=regra.nome, erro_tipo=type(erro).__name__)
        return AchadoValidacao(
            validacao=regra.nome,
            sujeito=modelo.sujeito,
            versao_catalogo=VERSAO_CATALOGO,
            resultado=ResultadoAchado.VERIFICAR,
            fatos_usados=(),
            valores={"base_legal": regra.base_legal, "erro_tipo": type(erro).__name__},
            explicacao=renderizar("motor_erro", validacao=regra.nome),
        )


def executar_catalogo(
    modelo: ModeloProcesso, classe: str, referencia: date
) -> list[AchadoValidacao]:
    """Produz um achado por regra aplicável e recorrente, com os fatos da respectiva parte."""
    regras = validacoes_de(classe)
    return [
        _executar(regra, recorrente, referencia)
        for recorrente in modelo.recorrentes(classe)
        for regra in regras
    ]
