"""Conferência documental do preparo do recurso (A8; RF-VAL-03)."""

from datetime import date

from lupa_pipeline.dominio.enums import QualidadeParte, ResultadoAchado
from lupa_pipeline.validacoes.apoio import Coleta, data_de
from lupa_pipeline.validacoes.dados import preparo_padrao
from lupa_pipeline.validacoes.modelo import AchadoValidacao, ModeloProcesso, valor_de

NOME = "preparo_recurso"
BASE_LEGAL = "arts. 98, 99 § 7º e 1.007 do CPC"


def executar(modelo: ModeloProcesso, referencia: date) -> AchadoValidacao:
    """Confere a dispensa, a gratuidade ou a data do recolhimento provado."""
    coleta = Coleta(modelo, NOME, BASE_LEGAL)
    tipo = coleta.unico("tipo_recurso")
    qualidade = coleta.unico("qualidade_recorrente")
    if not (tipo and qualidade):
        return coleta.verificar()
    entidade = str(valor_de(qualidade))
    tabela = preparo_padrao()
    if entidade not in QualidadeParte:
        return coleta.verificar("A qualidade do recorrente exige conferência.")
    if entidade in tabela.dispensas:
        return coleta.concluir(
            ResultadoAchado.CONFORME,
            f"Dispensa de preparo pela qualidade do recorrente ({tabela.dispensas[entidade]}).",
            dispensa=entidade,
            versao_dados=tabela.versao,
        )
    decisao = coleta.unico("gratuidade_decisao", obrigatorio=False)
    if coleta.conflitos:
        return coleta.verificar()
    if decisao and valor_de(decisao) == "deferida":
        return coleta.concluir(
            ResultadoAchado.CONFORME, "Há decisão de gratuidade deferida.", dispensa="gratuidade"
        )
    if decisao and valor_de(decisao) != "indeferida":
        return coleta.verificar("O resultado da decisão sobre gratuidade exige conferência.")
    pedido = coleta.unico("gratuidade_pedido", obrigatorio=False)
    if coleta.conflitos:
        return coleta.verificar()
    if pedido and valor_de(pedido) and decisao is None:
        coleta.unico("gratuidade_decisao")
        return coleta.verificar("Há pedido de gratuidade sem decisão localizada.")
    comprovante = coleta.unico("comprovante_preparo", obrigatorio=False)
    if coleta.conflitos:
        return coleta.verificar()
    if comprovante is None:
        return coleta.concluir(ResultadoAchado.ATENCAO, "Não se localizou comprovante de preparo.")
    interposicao = coleta.unico("data_interposicao")
    if interposicao is None:
        return coleta.verificar()
    try:
        pago, protocolo = data_de(comprovante), data_de(interposicao)
    except ValueError:
        return coleta.verificar("A data do comprovante ou da interposição exige conferência.")
    resultado = ResultadoAchado.CONFORME if pago <= protocolo else ResultadoAchado.ATENCAO
    return coleta.concluir(
        resultado,
        f"Comprovante de {pago:%d/%m/%Y} e interposição em {protocolo:%d/%m/%Y}.",
        data_comprovante=pago.isoformat(),
        data_interposicao=protocolo.isoformat(),
    )
