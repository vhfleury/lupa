"""Correspondência da decisão agravada com o inciso do CPC (A10; RF-VAL-05)."""

from datetime import date

from lupa_pipeline.dominio.enums import ResultadoAchado
from lupa_pipeline.validacoes.apoio import Coleta, regra
from lupa_pipeline.validacoes.dados import cabimento_padrao
from lupa_pipeline.validacoes.modelo import AchadoValidacao, ModeloProcesso

NOME = "cabimento_agravo"
BASE_LEGAL = "art. 1.015 do CPC"
PECA_PROCURADA = {
    "hipotese_decisao_agravada": "decisão interlocutória agravada",
}


@regra
def executar(modelo: ModeloProcesso, referencia: date) -> AchadoValidacao:
    """Aponta o inciso associado ou encaminha a hipótese para conferência humana."""
    coleta = Coleta(modelo, NOME, BASE_LEGAL, PECA_PROCURADA)
    fato = coleta.unico("hipotese_decisao_agravada")
    if fato is None:
        return coleta.verificar()
    inciso = str(fato.valor).strip().upper()
    tabela = cabimento_padrao()
    hipotese = tabela.incisos.get(inciso)
    if not hipotese:
        return coleta.verificar("A hipótese da decisão agravada exige conferência pelo magistrado.")
    return coleta.concluir(
        ResultadoAchado.CONFORME,
        f"Inciso {inciso} identificado ({hipotese}).",
        inciso=inciso,
        trecho=fato.evidencias[0].trecho,
        versao_dados=tabela.versao,
    )
