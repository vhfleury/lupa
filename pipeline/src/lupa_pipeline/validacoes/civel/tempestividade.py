"""Conferência da tempestividade em dias úteis (A7; RF-VAL-02)."""

from datetime import date

from lupa_pipeline.dominio.enums import QualidadeParte, ResultadoAchado
from lupa_pipeline.validacoes.apoio import Coleta, data_de, regra
from lupa_pipeline.validacoes.calendario import contar_prazo_util, dias_uteis_entre
from lupa_pipeline.validacoes.dados import calendario_padrao, prazos_recursos_padrao
from lupa_pipeline.validacoes.modelo import AchadoValidacao, ModeloProcesso

NOME = "tempestividade_recurso"
BASE_LEGAL = "arts. 180, 183, 186, 219, 220, 224, 1.003 § 5º e 1.023 do CPC"
PECA_PROCURADA = {
    "tipo_recurso": "petição de recurso",
    "data_intimacao": "certidão de intimação",
    "data_interposicao": "protocolo da petição de recurso",
    "qualidade_recorrente": "qualificação das partes na petição do recurso",
}


@regra
def executar(modelo: ModeloProcesso, referencia: date) -> AchadoValidacao:
    """Compara as datas provadas da intimação e da interposição com o vencimento do recurso."""
    coleta = Coleta(modelo, NOME, BASE_LEGAL, PECA_PROCURADA)
    tipo = coleta.unico("tipo_recurso")
    intimacao = coleta.unico("data_intimacao")
    interposicao = coleta.unico("data_interposicao")
    qualidade = coleta.unico("qualidade_recorrente")
    if not (tipo and intimacao and interposicao and qualidade):
        return coleta.verificar()
    tabela = prazos_recursos_padrao()
    regra = tabela.recursos.get(str(tipo.valor))
    entidade = str(qualidade.valor)
    if regra is None or entidade not in QualidadeParte:
        return coleta.verificar("Tipo de recurso ou qualidade do recorrente não reconhecidos.")
    try:
        inicio, protocolo = data_de(intimacao), data_de(interposicao)
    except ValueError:
        return coleta.verificar("A data da intimação ou da interposição exige conferência.")
    dobro = entidade in tabela.dobra
    dias = regra.dias * (tabela.multiplicador_dobro if dobro else 1)
    calendario, versoes = calendario_padrao()
    prazo = contar_prazo_util(inicio, dias, calendario.feriados, calendario.suspensoes)
    atraso, depois_do_vencimento = dias_uteis_entre(
        prazo.vencimento, protocolo, calendario.feriados, calendario.suspensoes
    )
    descartados = [
        {"data": d.data.isoformat(), "motivo": d.motivo, "fonte": calendario.fonte_em(d.data)}
        for d in (*prazo.dias_suspensos, *depois_do_vencimento)
    ]
    resultado = (
        ResultadoAchado.CONFORME if protocolo <= prazo.vencimento else ResultadoAchado.ATENCAO
    )
    fundamento = [regra.base_legal, tabela.contagem_base_legal]
    if dobro:
        fundamento.append(tabela.dobra[entidade])
    coleta.base_legal = ", ".join(fundamento)
    motivo = (
        f"{regra.nome} com prazo de {dias} dias úteis"
        f"{' (prazo em dobro)' if dobro else ''}. O prazo venceu em {prazo.vencimento:%d/%m/%Y} "
        f"e a interposição ocorreu em {protocolo:%d/%m/%Y}."
    )
    if resultado == ResultadoAchado.ATENCAO:
        unidade = "dia útil" if atraso == 1 else "dias úteis"
        motivo += f" O atraso foi de {atraso} {unidade}."
    return coleta.concluir(
        resultado,
        motivo,
        data_intimacao=inicio.isoformat(),
        data_interposicao=protocolo.isoformat(),
        prazo_dias=dias,
        prazo_em_dobro=dobro,
        vencimento=prazo.vencimento.isoformat(),
        atraso_dias_uteis=atraso,
        dias_nao_contados=descartados,
        versoes_dados={**versoes, "prazos_recursos.yaml": tabela.versao},
    )
