"""Seleção dos extratores cíveis e construção dos fatos com evidência verificável."""

from collections.abc import Iterator

from lupa_pipeline.config import PAGINAS_IDENTIFICACAO_PADRAO
from lupa_pipeline.dominio.chaves import chave_hash
from lupa_pipeline.dominio.enums import TipoPeca
from lupa_pipeline.dominio.esquemas import Fato
from lupa_pipeline.ingestao.datas import dobrar
from lupa_pipeline.ingestao.eventos import (
    capa,
    certidao,
    decisao_agravada,
    marcos,
    preparo,
    procuracao,
    recurso,
    sentenca,
)
from lupa_pipeline.ingestao.eventos.base import Fonte
from lupa_pipeline.ingestao.eventos.modelo import Candidato, PecaTexto, evidencia_de
from lupa_pipeline.ingestao.eventos.padroes import padroes
from lupa_pipeline.ingestao.eventos.partes import chave_nome

VERSAO = str(padroes()["versao"])
ORIGEM = "pipeline.eventos"
EXTRATORES = {
    TipoPeca.CERTIDAO: certidao.extrair,
    TipoPeca.SENTENCA: sentenca.extrair,
    TipoPeca.DECISAO_INTERLOCUTORIA: decisao_agravada.extrair,
    TipoPeca.PROCURACAO: procuracao.extrair,
    TipoPeca.COMPROVANTE_PREPARO: preparo.comprovante,
}


def candidatos_da_peca(
    peca: PecaTexto,
    sujeitos: dict[str, str],
    *,
    identificacao_paginas: int = PAGINAS_IDENTIFICACAO_PADRAO,
) -> Iterator[Candidato]:
    """Aplica as regras da espécie da peça ao sujeito expressamente identificado."""
    nomes = {
        chave_nome(m[1])
        for p in peca.paginas
        for m in recurso.ROTULO_SUJEITO.finditer(p.normalizado)
    }
    sujeito = sujeitos.get(next(iter(nomes)), "") if len(nomes) == 1 else ""
    tipo = peca.tipo
    explicita = any(recurso.QUALIDADE.search(dobrar(p.normalizado)) for p in peca.paginas)
    for pagina in peca.paginas:
        fonte = Fonte(pagina, sujeito)
        if pagina.numero <= identificacao_paginas:
            yield from capa.extrair(fonte)
        if tipo in recurso.RECURSOS:
            yield from recurso.extrair(fonte, tipo, explicita)
        if tipo in marcos.MARCOS:
            yield from marcos.extrair(fonte, tipo)
        if tipo == TipoPeca.PETICAO_INICIAL:
            yield from preparo.pedido(fonte)
        if tipo == TipoPeca.ACORDAO:
            yield from preparo.decisao(fonte)
        if tipo in EXTRATORES:
            yield from EXTRATORES[tipo](fonte)


def confirmar(candidato: Candidato, processo: str) -> Fato | None:
    """Confere o trecho e converte o candidato no contrato usado pelo banco e pela medição."""
    e = evidencia_de(candidato.pagina, candidato.inicio, candidato.fim, candidato.trecho)
    if e is None:
        return None
    return Fato(
        id=chave_hash(
            [processo, candidato.tipo.value, candidato.sujeito, e.id], vazias_permitidas=(2,)
        ).hex(),
        processo_id=processo,
        sujeito=candidato.sujeito,
        tipo=candidato.tipo,
        valor=candidato.valor,
        evidencias=(e,),
        extraido_por=ORIGEM,
        versao_extrator=VERSAO,
        confianca=1.0,
    )
