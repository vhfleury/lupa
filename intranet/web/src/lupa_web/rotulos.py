"""Rótulos em português dos códigos da API e formatação de datas para as telas."""

from datetime import date, datetime
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


def legivel(chave: str) -> str:
    """Texto legível de um identificador em `snake_case`.

    Args:
        chave: Identificador da API.

    Returns:
        O rótulo conhecido ou a chave com espaços e inicial maiúscula.
    """
    conhecido = CLASSES.get(chave) or SITUACAO.get(chave)
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
