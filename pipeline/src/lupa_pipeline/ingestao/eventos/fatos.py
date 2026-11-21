"""Seleção dos extratores cíveis e construção dos fatos com evidência verificável."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass

from lupa_pipeline.config import PAGINAS_IDENTIFICACAO_PADRAO
from lupa_pipeline.dominio.chaves import chave_hash
from lupa_pipeline.dominio.enums import TipoPeca
from lupa_pipeline.dominio.esquemas import Fato
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


@dataclass(frozen=True)
class Contexto:
    """Dados da peça que os extratores consultam além da página.

    Attributes:
        tipo: Espécie da peça.
        qualidade_explicita: Se alguma página declara a qualidade do recorrente.
        identificacao_paginas: Quantas páginas iniciais são lidas como capa.
    """

    tipo: TipoPeca
    qualidade_explicita: bool
    identificacao_paginas: int


Extrator = Callable[[Fonte, Contexto], Iterator[Candidato]]


def capa_inicial(fonte: Fonte, contexto: Contexto) -> Iterator[Candidato]:
    """Extrai os campos da capa só nas páginas iniciais de identificação."""
    if fonte.pagina.numero <= contexto.identificacao_paginas:
        yield from capa.extrair(fonte)


def _recurso(fonte: Fonte, contexto: Contexto) -> Iterator[Candidato]:
    """Extrai os elementos formais do recurso da espécie da peça."""
    yield from recurso.extrair(fonte, contexto.tipo, contexto.qualidade_explicita)


def _marco(fonte: Fonte, contexto: Contexto) -> Iterator[Candidato]:
    """Extrai o marco próprio da espécie da peça."""
    yield from marcos.extrair(fonte, contexto.tipo)


def _pagina(extrair: Callable[[Fonte], Iterator[Candidato]]) -> Extrator:
    """Adapta ao registro um extrator que só lê a página."""

    def extrator(fonte: Fonte, contexto: Contexto) -> Iterator[Candidato]:
        yield from extrair(fonte)

    return extrator


PROPRIOS: dict[TipoPeca, tuple[Extrator, ...]] = {
    **{tipo: (_recurso,) for tipo in recurso.RECURSOS},
    **{tipo: (_marco,) for tipo in marcos.MARCOS},
    TipoPeca.PETICAO_INICIAL: (_marco, _pagina(preparo.pedido)),
    TipoPeca.ACORDAO: (_marco, _pagina(preparo.decisao)),
    TipoPeca.CERTIDAO: (_pagina(certidao.extrair),),
    TipoPeca.SENTENCA: (_pagina(sentenca.extrair),),
    TipoPeca.DECISAO_INTERLOCUTORIA: (_pagina(decisao_agravada.extrair),),
    TipoPeca.PROCURACAO: (_pagina(procuracao.extrair),),
    TipoPeca.COMPROVANTE_PREPARO: (_pagina(preparo.comprovante),),
}
EXTRATORES: dict[TipoPeca, tuple[Extrator, ...]] = {
    tipo: (capa_inicial, *PROPRIOS.get(tipo, ())) for tipo in TipoPeca
}


def candidatos_da_peca(
    peca: PecaTexto,
    sujeitos: dict[str, str],
    *,
    identificacao_paginas: int = PAGINAS_IDENTIFICACAO_PADRAO,
) -> Iterator[Candidato]:
    """Aplica, página a página, os extratores registrados para a espécie da peça."""
    nomes = {
        chave_nome(m[1])
        for p in peca.paginas
        for m in recurso.ROTULO_SUJEITO.finditer(p.normalizado)
    }
    sujeito = sujeitos.get(next(iter(nomes)), "") if len(nomes) == 1 else ""
    contexto = Contexto(
        tipo=peca.tipo,
        qualidade_explicita=any(recurso.QUALIDADE.search(p.dobrado) for p in peca.paginas),
        identificacao_paginas=identificacao_paginas,
    )
    for pagina in peca.paginas:
        fonte = Fonte(pagina, sujeito)
        for extrator in EXTRATORES[peca.tipo]:
            yield from extrator(fonte, contexto)


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
