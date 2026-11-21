"""Conferência documental do preparo do recurso (A8; RF-VAL-03)."""

from datetime import date

from lupa_pipeline.dominio.enums import QualidadeParte, ResultadoAchado
from lupa_pipeline.validacoes.apoio import Coleta, data_de, regra
from lupa_pipeline.validacoes.dados import dispensas_padrao
from lupa_pipeline.validacoes.modelo import AchadoValidacao, ModeloProcesso, valor_de

NOME = "preparo_recurso"
BASE_LEGAL = "arts. 98, 99 § 7º e 1.007 do CPC"


@regra
def executar(modelo: ModeloProcesso, referencia: date) -> AchadoValidacao:
    """Confere a dispensa, a gratuidade ou a data do recolhimento provado."""
    coleta = Coleta(modelo, NOME, BASE_LEGAL)
    tipo = coleta.unico("tipo_recurso")
    entidade = coleta.qualidade()
    if not (tipo and entidade):
        return coleta.verificar()
    tabela = dispensas_padrao()
    if entidade not in QualidadeParte:
        return coleta.verificar("A qualidade do recorrente exige conferência.")
    dispensa = tabela.dispensas.get(entidade)
    if dispensa is not None and dispensa.preparo:
        return coleta.concluir(
            ResultadoAchado.CONFORME,
            f"Dispensa de preparo pela qualidade do recorrente ({dispensa.rotulo}).",
            dispensa=entidade,
            versao_dados=tabela.versao,
        )
    decisao = coleta.unico("gratuidade_decisao", obrigatorio=False)
    if decisao and valor_de(decisao) == "deferida":
        return coleta.concluir(
            ResultadoAchado.CONFORME, "Há decisão de gratuidade deferida.", dispensa="gratuidade"
        )
    if decisao and valor_de(decisao) != "indeferida":
        return coleta.verificar("O resultado da decisão sobre gratuidade exige conferência.")
    pedido = coleta.unico("gratuidade_pedido", obrigatorio=False)
    if pedido and valor_de(pedido) and decisao is None:
        coleta.unico("gratuidade_decisao")
        return coleta.verificar("Há pedido de gratuidade sem decisão localizada.")
    comprovante = coleta.unico("comprovante_preparo", obrigatorio=False)
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
