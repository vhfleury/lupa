"""Orquestração da extração de páginas (4C.8): lotes de páginas em paralelo, em processos.

Cada lote de páginas é um processo filho do sandbox (`extrator_paginas`), que abre o seu
próprio documento: o PyMuPDF nunca é usado por duas threads. No pai, um pool de threads só
espera os filhos; o worker processa um job por vez, então o teto de lotes simultâneos por job
é o teto global.
"""

from collections.abc import Callable, Generator, Iterable, Sequence
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from itertools import groupby, islice
from pathlib import Path
from threading import Event
from typing import Any

from lupa_pipeline.dominio.enums import MotivoFalha
from lupa_pipeline.ingestao.sandbox import LimitesSandbox, ResultadoSandbox, executar

MODULO_EXTRATOR = "lupa_pipeline.ingestao.extrator_paginas"


@dataclass(frozen=True)
class FontePaginas:
    """PDF de onde saem páginas: o arquivo avulso ou uma entrada do ZIP.

    Attributes:
        caminho: Arquivo local.
        nome: Nome de origem (entrada do ZIP ou nome do PDF).
        paginas: Quantidade de páginas.
        deslocamento: Páginas de fontes anteriores (numeração contínua do arquivo).
    """

    caminho: Path
    nome: str
    paginas: int
    deslocamento: int


@dataclass(frozen=True)
class Tarefa:
    """Lote de páginas consecutivas de uma fonte.

    Attributes:
        fonte: PDF de origem.
        inicio: Primeira página na fonte (1-based).
        fim: Última página na fonte (inclusiva).
    """

    fonte: FontePaginas
    inicio: int
    fim: int

    @property
    def numeros(self) -> range:
        """Números das páginas na numeração contínua do arquivo."""
        base = self.fonte.deslocamento
        return range(base + self.inicio, base + self.fim + 1)


@dataclass(frozen=True)
class ResultadoTarefa:
    """Resultado de um lote.

    Attributes:
        tarefa: Lote executado.
        paginas: Páginas extraídas (com `numero` contínuo e `origem_arquivo`).
        motivo_falha: Motivo quando o filho falhou (todas as páginas do lote faltam).
    """

    tarefa: Tarefa
    paginas: list[dict[str, Any]]
    motivo_falha: MotivoFalha | None = None


@dataclass(frozen=True)
class Paralelismo:
    """Tetos de paralelismo.

    Attributes:
        paginas_por_lote: Páginas por processo filho.
        lotes_por_job: Lotes simultâneos de um job.
    """

    paginas_por_lote: int = 8
    lotes_por_job: int = 2


Executor = Callable[[str, list[str], LimitesSandbox], ResultadoSandbox]


def planejar(fontes: Sequence[FontePaginas], paginas_por_lote: int) -> list[Tarefa]:
    """Divide as fontes em lotes de páginas consecutivas.

    Args:
        fontes: PDFs na ordem do manifesto.
        paginas_por_lote: Tamanho máximo do lote.

    Returns:
        Lotes em ordem.
    """
    return [
        Tarefa(fonte, inicio, min(fonte.paginas, inicio + paginas_por_lote - 1))
        for fonte in fontes
        for inicio in range(1, fonte.paginas + 1, paginas_por_lote)
    ]


def pendentes(tarefas: Sequence[Tarefa], prontas: set[int]) -> list[Tarefa]:
    """Intervalos consecutivos que ainda exigem extração.

    Args:
        tarefas: Lotes planejados.
        prontas: Números (contínuos) já gravados na versão corrente do extrator.

    Returns:
        Lotes a executar.
    """
    restantes = []
    for tarefa in tarefas:
        base = tarefa.fonte.deslocamento
        for pronta, grupo in groupby(tarefa.numeros, key=prontas.__contains__):
            if not pronta:
                numeros = list(grupo)
                restantes.append(Tarefa(tarefa.fonte, numeros[0] - base, numeros[-1] - base))
    return restantes


def _converter(tarefa: Tarefa, resultado: ResultadoSandbox) -> ResultadoTarefa:
    if resultado.motivo_falha is not None:
        return ResultadoTarefa(tarefa, [], resultado.motivo_falha)
    if resultado.dados.get("ok") is not True:
        return ResultadoTarefa(tarefa, [], MotivoFalha.ERRO_PARSER)
    paginas = []
    for pagina in resultado.dados.get("paginas", []):
        numero = int(pagina["numero"])
        paginas.append(
            pagina
            | {
                "numero": tarefa.fonte.deslocamento + numero,
                "origem_arquivo": tarefa.fonte.nome,
                "pagina_origem": numero,
            }
        )
    return ResultadoTarefa(tarefa, paginas)


def executar_tarefa(
    tarefa: Tarefa, limites: LimitesSandbox, executor: Executor = executar
) -> ResultadoTarefa:
    """Extrai um lote num processo filho do sandbox.

    Args:
        tarefa: Lote.
        limites: Limites do filho.
        executor: Função que roda o filho (injetável nos testes).

    Returns:
        Páginas extraídas ou o motivo da falha.
    """
    argumentos = [str(tarefa.fonte.caminho), str(tarefa.inicio), str(tarefa.fim)]
    return _converter(tarefa, executor(MODULO_EXTRATOR, argumentos, limites))


def executar_em_paralelo[Item, Resultado](
    itens: Iterable[Item],
    rodar: Callable[[Item], Resultado],
    lotes_por_job: int,
    parar: Event | None = None,
) -> Generator[Resultado, None, None]:
    """Roda os itens em até `lotes_por_job` threads, devolvendo cada resultado ao terminar.

    Um item só é submetido quando há thread livre e `parar` não está marcado; os itens em curso
    terminam e são devolvidos. Fechar o iterador (erro de quem consome) descarta os itens ainda
    não submetidos e espera os em curso.

    Args:
        itens: Itens a rodar, na ordem de submissão.
        rodar: Função executada na thread (só espera o processo filho do sandbox).
        lotes_por_job: Itens simultâneos; `1` roda um por vez.
        parar: Sinal que interrompe novas submissões.

    Yields:
        Resultados na ordem de término.
    """
    fila = iter(itens)
    trabalhadores = max(1, lotes_por_job)
    with ThreadPoolExecutor(max_workers=trabalhadores, thread_name_prefix="lote") as pool:
        em_curso = {pool.submit(rodar, item) for item in islice(fila, trabalhadores)}
        while em_curso:
            prontos, em_curso = wait(em_curso, return_when=FIRST_COMPLETED)
            for futuro in prontos:
                if parar is None or not parar.is_set():
                    em_curso.update(pool.submit(rodar, item) for item in islice(fila, 1))
                yield futuro.result()


def linha_pagina(pagina: dict[str, Any], versao_extrator: str) -> dict[str, Any]:
    """Converte o resultado de uma página na linha gravada em `pagina`.

    Args:
        pagina: Página devolvida pelo extrator (já com numeração contínua e origem).
        versao_extrator: Versão do extrator que a produziu.

    Returns:
        Colunas de `pagina` (sem ids nem hash, que o repositório preenche).
    """
    return {
        "numero": int(pagina["numero"]),
        "tipo": str(pagina["tipo"]),
        "texto": str(pagina.get("texto") or ""),
        "flags": dict(pagina.get("flags") or {}),
        "sinais": dict(pagina.get("sinais") or {}),
        "coordenadas": dict(pagina.get("coordenadas") or {}),
        "extracao": {
            "rota": pagina.get("rota"),
            "versao_roteador": pagina.get("versao_roteador"),
            "segundos": pagina.get("segundos"),
            "ocr": pagina.get("ocr"),
            "divergencia": pagina.get("divergencia"),
            "saneamento": pagina.get("saneamento"),
            "metadados_descartados": list(pagina.get("metadados_descartados") or []),
            "imagens_nativas": list(pagina.get("imagens_nativas") or []),
        },
        "texto_normalizado": pagina.get("texto_normalizado"),
        "trechos_ocultos": list(pagina.get("trechos_ocultos") or []),
        "trechos_suspeitos": list(pagina.get("trechos_suspeitos") or []),
        "texto_nativo": pagina.get("texto_nativo"),
        "texto_ocr": pagina.get("texto_ocr"),
        "versao_extrator": versao_extrator,
        "origem_arquivo": pagina.get("origem_arquivo"),
        "pagina_origem": pagina.get("pagina_origem"),
    }
