"""Conferência da cadeia de representação do recorrente (A9; RF-VAL-04)."""

import re
import unicodedata
from collections import deque
from datetime import date
from typing import Any

from lupa_pipeline.dominio.enums import QualidadeParte, ResultadoAchado
from lupa_pipeline.validacoes.apoio import Coleta, regra
from lupa_pipeline.validacoes.dados import dispensas_padrao
from lupa_pipeline.validacoes.modelo import AchadoValidacao, Fato, ModeloProcesso, valor_de

NOME = "representacao_recurso"
BASE_LEGAL = "arts. 75, 103 e 104 do CPC"
PECA_PROCURADA = {
    "qualidade_recorrente": "qualificação das partes na petição do recurso",
    "advogado_subscritor": "assinatura da petição de recurso",
}


def _nome(texto: str) -> str:
    simples = unicodedata.normalize("NFKD", texto.casefold())
    return " ".join("".join(c for c in simples if not unicodedata.combining(c)).split())


def _advogado(valor: Any) -> tuple[str, str]:
    if not isinstance(valor, dict):
        return _nome(valor) if isinstance(valor, str) else "", ""
    return _nome(str(valor.get("nome") or "")), re.sub(
        r"[^A-Z0-9]", "", str(valor.get("oab") or "").upper()
    )


def _mesmo(primeiro: tuple[str, str], segundo: tuple[str, str]) -> bool:
    a, b = primeiro[1], segundo[1]
    if a and b:
        return a == b
    return bool(primeiro[0] and primeiro[0] == segundo[0])


def _cadeia(modelo: ModeloProcesso, assinante: tuple[str, str], mandatos: list[Fato]) -> list[Fato]:
    fila: deque[tuple[tuple[str, str], list[Fato]]] = deque()
    substabelecimentos: list[tuple[tuple[str, str], tuple[str, str], Fato]] = []
    for fato in mandatos:
        dados = valor_de(fato)
        if not isinstance(dados, dict):
            continue
        outorgante = dados.get("outorgante")
        advogado = _advogado(dados.get("advogado"))
        if dados.get("tipo") == "substabelecimento":
            substabelecimentos.append((_advogado(outorgante), advogado, fato))
        elif modelo.sujeito and outorgante == modelo.sujeito:
            fila.append((advogado, [fato]))
    visitados: set[tuple[str, str]] = set()
    while fila:
        advogado, caminho = fila.popleft()
        if advogado in visitados:
            continue
        visitados.add(advogado)
        if _mesmo(advogado, assinante):
            return caminho
        for origem, destino, documento in substabelecimentos:
            if _mesmo(advogado, origem):
                fila.append((destino, [*caminho, documento]))
    return []


@regra
def executar(modelo: ModeloProcesso, referencia: date) -> AchadoValidacao:
    """Verifica se o subscritor recebeu poderes diretamente ou por substabelecimento."""
    coleta = Coleta(modelo, NOME, BASE_LEGAL, PECA_PROCURADA)
    entidade = coleta.qualidade()
    if entidade is None:
        return coleta.verificar()
    tabela = dispensas_padrao()
    if entidade not in QualidadeParte:
        return coleta.verificar("A qualidade do recorrente exige conferência.")
    dispensa = tabela.dispensas.get(entidade)
    if dispensa is not None and dispensa.mandato:
        return coleta.concluir(
            ResultadoAchado.CONFORME,
            f"Dispensa de mandato pela qualidade do recorrente ({dispensa.rotulo}).",
            dispensa=entidade,
            versao_dados=tabela.versao,
        )
    subscritor = coleta.unico("advogado_subscritor")
    if subscritor is None:
        return coleta.verificar()
    advogado = _advogado(valor_de(subscritor))
    if not any(advogado):
        return coleta.verificar("A assinatura na petição de recurso não identifica o subscritor.")
    mandatos = modelo.fatos("procuracao")
    cadeia = _cadeia(modelo, advogado, mandatos)
    if not cadeia:
        coleta.registrar(mandatos)
        return coleta.concluir(
            ResultadoAchado.ATENCAO, "Não se localizou mandato do recorrente ao subscritor."
        )
    coleta.registrar(cadeia)
    paginas = list(dict.fromkeys(str(e.pagina_id) for fato in cadeia for e in fato.evidencias))
    return coleta.concluir(
        ResultadoAchado.CONFORME,
        "Mandato do recorrente ao subscritor localizado.",
        paginas_mandato=paginas,
        cadeia=[f.id for f in cadeia],
    )
