"""Rótulos em português dos códigos da API e formatação de datas para as telas."""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")
SEM_VALOR = "—"

CLASSES = {
    "apelacao_civel": "Apelação cível",
    "agravo_instrumento": "Agravo de instrumento",
    "embargos_declaracao": "Embargos de declaração",
    "agravo_interno": "Agravo interno",
    "acao_originaria": "Ação originária",
}

SITUACAO = {
    "sem_arquivos": "Sem arquivos",
    "processando": "Processando",
    "quarentena": "Em quarentena",
    "falho": "Falhou",
    "pendencias": "Com pendências",
    "concluido": "Concluído",
}

RESULTADO = {"conforme": "Conforme", "atencao": "Atenção", "verificar": "Verificar"}

STATUS_FATO = {"automatico": "Automático", "confirmado": "Confirmado", "corrigido": "Corrigido"}

TIPOS_PECA = (
    "peticao_inicial",
    "contestacao",
    "replica",
    "decisao_interlocutoria",
    "sentenca",
    "embargos_declaracao",
    "apelacao",
    "agravo_instrumento",
    "agravo_interno",
    "contrarrazoes",
    "acordao",
    "certidao",
    "procuracao",
    "comprovante_preparo",
    "laudo_pericial",
    "parecer_mp",
    "outros",
)

VALOR_DECIMAL = re.compile(r"\d+(\.\d+)?")

ESTADO_JOB = {
    "recebido": "Na fila",
    "validado": "Validado",
    "em_extracao": "Extraindo páginas",
    "parcial": "Parcial",
    "em_revisao": "Concluído com pendências",
    "concluido": "Concluído",
    "falho": "Falhou",
    "quarentena": "Em quarentena",
}

ESTADOS_FINAIS = frozenset({"concluido", "falho", "quarentena", "em_revisao", "parcial"})

MOTIVO_QUARENTENA = {
    "corrompido": "O arquivo está corrompido e não pôde ser aberto.",
    "senha": "O arquivo está protegido por senha. Envie uma versão sem senha.",
    "truncado": "O PDF está incompleto (o envio ou a cópia foi interrompido).",
    "assinatura_invalida": "A assinatura digital não cobre o documento inteiro.",
    "tipo_invalido": "O conteúdo não é PDF (ou o ZIP tem arquivo que não é PDF).",
    "zip_malicioso": (
        "O ZIP foi recusado por segurança (caminho perigoso, link ou tamanho excessivo)."
    ),
}

MOTIVO_FALHA = {
    "limite_memoria": "O processamento passou do limite de memória.",
    "limite_cpu": "O processamento passou do limite de tempo de CPU.",
    "tempo_esgotado": "O processamento demorou demais.",
    "erro_parser": "Erro ao ler o PDF.",
    "arquivo_ausente": "O arquivo não foi encontrado no armazenamento.",
    "erro_interno": "Erro interno no processamento.",
}


ROTULOS = {
    "peticao_inicial": "Petição inicial",
    "contestacao": "Contestação",
    "replica": "Réplica",
    "decisao_interlocutoria": "Decisão interlocutória",
    "sentenca": "Sentença",
    "apelacao": "Apelação",
    "contrarrazoes": "Contrarrazões",
    "acordao": "Acórdão",
    "certidao": "Certidão",
    "procuracao": "Procuração",
    "comprovante_preparo": "Comprovante de preparo",
    "laudo_pericial": "Laudo pericial",
    "parecer_mp": "Parecer do Ministério Público",
    "juizo": "Juízo",
    "mp": "Ministério Público",
    "ministerio_publico": "Ministério Público",
    "fazenda_publica": "Fazenda Pública",
    "defensoria_publica": "Defensoria Pública",
    "tempestividade_recurso": "Tempestividade do recurso",
    "preparo_recurso": "Preparo do recurso",
    "representacao_recurso": "Representação do recorrente",
    "cabimento_agravo": "Cabimento do agravo",
    "data_decisao_recorrida": "Data da decisão recorrida",
    "data_intimacao": "Data da intimação",
    "data_interposicao": "Data de interposição",
    "data_comprovante": "Data do comprovante",
    "data_ajuizamento": "Data do ajuizamento",
    "data_citacao": "Data da citação",
    "data_contestacao": "Data da contestação",
    "data_acordao": "Data do acórdão",
    "relator": "Relator",
    "orgao_julgador": "Órgão julgador",
    "assunto": "Assunto",
    "valor_causa": "Valor da causa",
    "juizo_origem": "Juízo de origem",
    "data_distribuicao": "Data de distribuição",
    "tipo_recurso": "Tipo de recurso",
    "qualidade_recorrente": "Qualidade do recorrente",
    "gratuidade_pedido": "Pedido de gratuidade",
    "gratuidade_decisao": "Decisão sobre a gratuidade",
    "advogado_subscritor": "Advogado subscritor",
    "hipotese_decisao_agravada": "Hipótese da decisão agravada",
    "prazo_dias": "Prazo em dias úteis",
    "atraso_dias_uteis": "Atraso em dias úteis",
    "dias_nao_contados": "Dias não contados",
    "versoes_dados": "Versões dos dados",
    "versao_dados": "Versão dos dados",
    "pecas_procuradas": "Peças consultadas",
    "paginas_mandato": "Folhas do mandato",
    "oab": "OAB",
}
POSICOES_DA_MASCARA_CNJ = {7: "-", 9: ".", 13: ".", 14: ".", 16: "."}
DIGITOS_CNJ = 20


def mascarar_cnj(texto: str) -> str:
    """Número CNJ com a máscara `NNNNNNN-DD.AAAA.J.TR.OOOO`, como o `mascararCnj` do SvelteKit.

    Args:
        texto: Número com ou sem máscara.

    Returns:
        Os até 20 dígitos com os separadores nas posições do CNJ.
    """
    digitos = re.sub(r"\D", "", texto)[:DIGITOS_CNJ]
    return "".join(
        POSICOES_DA_MASCARA_CNJ.get(posicao, "") + digito for posicao, digito in enumerate(digitos)
    )


def legivel(chave: str) -> str:
    """Texto legível de um identificador em `snake_case`.

    Args:
        chave: Identificador da API.

    Returns:
        O rótulo conhecido ou a chave com espaços e inicial maiúscula.
    """
    conhecido = CLASSES.get(chave) or SITUACAO.get(chave) or ROTULOS.get(chave)
    if conhecido:
        return conhecido
    texto = chave.replace("_", " ")
    return texto[:1].upper() + texto[1:]


def formatar_data(valor: str | None) -> str:
    """Data (`AAAA-MM-DD`) ou data e hora ISO no formato brasileiro, no fuso de Brasília.

    Args:
        valor: Texto ISO da API ou `None`.

    Returns:
        `DD/MM/AAAA`, `DD/MM/AAAA HH:MM`, o próprio texto se não for data, ou "—".
    """
    if not valor:
        return SEM_VALOR
    try:
        if len(valor) == len("AAAA-MM-DD"):
            return date.fromisoformat(valor).strftime("%d/%m/%Y")
        momento = datetime.fromisoformat(valor)
    except ValueError:
        return valor
    if momento.tzinfo is not None:
        momento = momento.astimezone(FUSO)
    return momento.strftime("%d/%m/%Y %H:%M")


def motivo_quarentena(motivo: str | None) -> str:
    """Explicação da quarentena para o usuário.

    Args:
        motivo: Código do motivo.

    Returns:
        Frase do motivo conhecido ou genérica.
    """
    if not motivo:
        return "Arquivo recusado."
    return MOTIVO_QUARENTENA.get(motivo, f"Arquivo recusado ({legivel(motivo)}).")


def motivo_falha(motivo: str | None) -> str:
    """Explicação da falha de processamento para o usuário.

    Args:
        motivo: Código do motivo.

    Returns:
        Frase do motivo conhecido ou genérica.
    """
    if not motivo:
        return "Falha no processamento."
    return MOTIVO_FALHA.get(motivo, f"Falha no processamento ({legivel(motivo)}).")


def texto_do_valor(valor: object) -> str:
    """Texto de um valor do JSON da API para leitura humana.

    Args:
        valor: Valor qualquer do JSON.

    Returns:
        "Sim"/"Não", datas formatadas, listas separadas por " · " e objetos como "Chave: valor".
    """
    if valor is None:
        return SEM_VALOR
    if isinstance(valor, bool):
        return "Sim" if valor else "Não"
    if isinstance(valor, str):
        return formatar_data(valor) if len(valor) == len("AAAA-MM-DD") else valor
    if isinstance(valor, list):
        return " · ".join(texto_do_valor(item) for item in valor) or SEM_VALOR
    if isinstance(valor, dict):
        return " · ".join(f"{legivel(str(k))}: {texto_do_valor(v)}" for k, v in valor.items())
    return str(valor)


def pares(
    dados: dict[str, Any] | None, omitir: frozenset[str] = frozenset()
) -> list[tuple[str, str]]:
    """Pares (rótulo, texto) de um objeto da API, para uma lista de definições.

    Args:
        dados: Objeto da API ou `None`.
        omitir: Chaves que não aparecem.

    Returns:
        Lista na ordem do objeto.
    """
    return [
        (legivel(chave), texto_do_valor(valor))
        for chave, valor in (dados or {}).items()
        if chave not in omitir
    ]


def formatar_moeda(valor: str) -> str:
    """Valor decimal da API (`1500.50`) em reais (`R$ 1.500,50`).

    Args:
        valor: Texto do valor.

    Returns:
        O valor em reais, ou o próprio texto se não for decimal.
    """
    if not VALOR_DECIMAL.fullmatch(valor):
        return valor
    texto = f"{Decimal(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


def percentual(valor: float) -> str:
    """Fração como percentual inteiro.

    Args:
        valor: Fração entre 0 e 1.

    Returns:
        Texto como `92%`.
    """
    return f"{round(valor * 100)}%"
