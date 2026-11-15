"""Os dez processos de referência (``semente_01`` a ``semente_10``) e o corpus de injeção.

Tamanhos crescentes de 200 a 5.000 folhas. A mistura vai de 90% digitalizado (o menor) a 90%
nativo (o maior): assim os dois extremos existem e o volume em disco fica administrável (folha
digitalizada pesa de 150 a 300 KB; nativa, poucos KB). Os resultados esperados das validações
variam entre os dez para cobrir ``conforme``, ``atencao`` e ``verificar``.
"""

import time
from dataclasses import dataclass
from pathlib import Path

from lupa_pipeline.dominio.enums import ClasseProcessual, QualidadeParte
from lupa_pipeline.sinteticos.empacotamento import exportar
from lupa_pipeline.sinteticos.gabarito import TODOS_VETORES, Cenario, Composicao
from lupa_pipeline.sinteticos.gerador import gerar_conteudo
from lupa_pipeline.sinteticos.roteiro import Configuracao, PreparoSintetico


def mistura(digitalizada: float) -> dict[Composicao, float]:
    """Mistura de composições com a fração digitalizada pedida.

    Args:
        digitalizada: Fração de folhas digitalizadas (0 a 0,92).

    Returns:
        Pesos por composição (híbridas fixas em 5% e 3%; o resto é nativo).
    """
    return {
        Composicao.NATIVA: max(0.0, 1.0 - digitalizada - 0.08),
        Composicao.DIGITALIZADA: digitalizada,
        Composicao.HIBRIDA_CORPO: 0.05,
        Composicao.HIBRIDA_ASSINATURA: 0.03,
    }


_PLANO = (
    (200, 0.90, "apelacao_civel", True, "pago", True, "particular"),
    (300, 0.80, "agravo_instrumento", False, "pedido", True, "particular"),
    (450, 0.70, "embargos_declaracao", True, "ausente", False, "fazenda_publica"),
    (650, 0.60, "agravo_interno", False, "ausente", False, "particular"),
    (900, 0.50, "acao_originaria", True, "ausente", False, "particular"),
    (1200, 0.40, "apelacao_civel", False, "deferido", True, "particular"),
    (1600, 0.30, "agravo_instrumento", True, "ausente", False, "defensoria_publica"),
    (2200, 0.20, "embargos_declaracao", False, "ausente", False, "particular"),
    (3200, 0.15, "agravo_interno", True, "ausente", False, "ministerio_publico"),
    (5000, 0.02, "acao_originaria", False, "ausente", False, "particular"),
)

REFERENCIAS: dict[str, Configuracao] = {
    f"semente_{n:02d}": Configuracao(
        semente=1000 + n,
        paginas_alvo=paginas,
        mistura=mistura(dig),
        tempestivo=tempestivo,
        classe=ClasseProcessual(classe),
        preparo=PreparoSintetico(preparo),
        mandato=mandato,
        qualidade=QualidadeParte(qualidade),
    )
    for n, (paginas, dig, classe, tempestivo, preparo, mandato, qualidade) in enumerate(
        _PLANO, start=1
    )
}


@dataclass(frozen=True)
class ResumoGeracao:
    """Resumo de um processo gerado.

    Attributes:
        nome: Nome da pasta.
        folhas: Folhas de conteúdo.
        pecas: Peças.
        segundos: Tempo total (conteúdo e três cenários).
        bytes_por_cenario: Tamanho do arquivo de autos por cenário.
    """

    nome: str
    folhas: int
    pecas: int
    segundos: float
    bytes_por_cenario: dict[str, int]


def gerar_processo(
    nome: str, config: Configuracao, destino: Path, cenarios: tuple[Cenario, ...] = tuple(Cenario)
) -> ResumoGeracao:
    """Gera um processo e grava os cenários em ``destino/nome``.

    Args:
        nome: Nome da pasta do processo.
        config: Configuração.
        destino: Pasta raiz.
        cenarios: Cenários a gravar.

    Returns:
        Resumo com tempo e tamanhos.
    """
    inicio = time.perf_counter()
    conteudo = gerar_conteudo(config)
    arquivos = exportar(conteudo, destino / nome, cenarios)
    conteudo.documento.close()
    return ResumoGeracao(
        nome=nome, folhas=len(conteudo.paginas), pecas=len(conteudo.pecas),
        segundos=round(time.perf_counter() - inicio, 2),
        bytes_por_cenario={a.cenario.value: a.bytes for a in arquivos},
    )  # fmt: skip


def configuracoes_injecao(paginas: int = 30) -> dict[str, Configuracao]:
    """Uma variante por vetor de injeção e uma com todos os vetores.

    Args:
        paginas: Tamanho de cada variante.

    Returns:
        Configurações por nome de pasta.
    """
    variantes = {
        f"injecao_{vetor.value}": Configuracao(
            semente=5000 + i, paginas_alvo=paginas, mistura=mistura(0.2), injecoes=(vetor,)
        )
        for i, vetor in enumerate(TODOS_VETORES, start=1)
    }
    variantes["injecao_todos"] = Configuracao(
        semente=5999, paginas_alvo=paginas, mistura=mistura(0.2), injecoes=TODOS_VETORES
    )
    return variantes
