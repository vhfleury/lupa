"""Regressão do saneamento contra o corpus de injeção (4D.10, corpus da 4B.8).

Para cada uma das dez variantes de `.sinteticos/injecao`, extrai pelo sandbox as páginas com
injeção (e a primeira, que leva os metadados do documento) e confere, por injeção do gabarito,
que a flag esperada para o vetor disparou e que o objetivo não se materializa na ingestão: o
texto oculto não está em `texto`, metadado e anotação não estão em `texto`, o bloco codificado
não está no normalizado, os homóglifos viram ASCII no normalizado. Mede recall (injeções
textuais detectadas) e falso positivo (páginas de `semente_01` com flag de saneamento) por
versão dos YAML; com `LUPA_METRICAS_INJECAO` definido, grava as métricas nesse caminho.

Gera os autos em pasta temporária quando a referência cível não está instalada.
"""

import json
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import pytest

from lupa_pipeline.dominio.enums import FlagPagina
from lupa_pipeline.ingestao.extracao import (
    FontePaginas,
    Paralelismo,
    executar_em_paralelo,
    planejar,
)
from lupa_pipeline.ingestao.parser_pdf import inspecionar
from lupa_pipeline.ingestao.sandbox import LimitesSandbox
from lupa_pipeline.ingestao.saneamento import normalizar
from lupa_pipeline.ingestao.saneamento_pagina import versoes
from lupa_pipeline.sinteticos.gabarito import VERSAO_ESQUEMA, Cenario, Gabarito, VetorInjecao
from lupa_pipeline.sinteticos.referencia import REFERENCIAS, configuracoes_injecao, gerar_processo
from lupa_pipeline.sinteticos.roteiro import Configuracao

pytestmark = [pytest.mark.integracao, pytest.mark.injecao]

RAIZ = Path(os.environ.get("LUPA_SINTETICOS_DIR", ".sinteticos")).resolve()
META_RECALL = 0.9
META_FALSO_POSITIVO = 0.05
LIMITES = LimitesSandbox(tempo_segundos=600.0, cpu_segundos=600)
FLAGS_SANEAMENTO = frozenset(f.value for f in FlagPagina if f is not FlagPagina.TEXTO_DIVERGENTE)

FLAG_ESPERADA: dict[VetorInjecao, tuple[FlagPagina, ...]] = {
    VetorInjecao.TEXTO_BRANCO: (FlagPagina.TEXTO_OCULTO,),
    VetorInjecao.FORA_DA_PAGINA: (FlagPagina.TEXTO_OCULTO,),
    VetorInjecao.METADADO_XMP: (FlagPagina.METADADO_SUSPEITO,),
    VetorInjecao.ANOTACAO: (FlagPagina.METADADO_SUSPEITO,),
    VetorInjecao.BASE64: (FlagPagina.BLOCO_CODIFICADO,),
    # numa folha digitalizada o OCR já devolve letras latinas: sobra o padrão de instrução
    VetorInjecao.HOMOGLIFOS: (FlagPagina.HOMOGLIFOS, FlagPagina.PADRAO_INSTRUCAO),
    VetorInjecao.IDIOMA_ALTERNADO: (FlagPagina.IDIOMA_INESPERADO,),
    VetorInjecao.TRANSCRICAO_CITADA: (FlagPagina.PADRAO_INSTRUCAO,),
    VetorInjecao.IMAGEM_COM_TEXTO: (FlagPagina.PADRAO_INSTRUCAO,),
}
CIRILICOS = frozenset("аеорсх")


@pytest.fixture(scope="module")
def corpus(tmp_path_factory: pytest.TempPathFactory) -> tuple[list[Path], Path]:
    """Usa o corpus de referência instalado ou gera as mesmas variantes cíveis para a suíte."""
    local = tmp_path_factory.mktemp("corpus-civel")

    def materializar(raiz: Path, nome: str, config: Configuracao) -> Path:
        pasta = RAIZ / raiz / nome / Cenario.PDF_LISO.value
        arquivo = pasta / "gabarito.json"
        if (pasta / "autos.pdf").is_file() and arquivo.is_file():
            if json.loads(arquivo.read_text("utf-8")).get("versao_esquema") == VERSAO_ESQUEMA:
                return pasta
        gerar_processo(nome, config, local / raiz, (Cenario.PDF_LISO,))
        return local / raiz / nome / Cenario.PDF_LISO.value

    variantes = [
        materializar(Path("injecao"), nome, config).parent
        for nome, config in configuracoes_injecao().items()
    ]
    controle = replace(REFERENCIAS["semente_01"], paginas_alvo=30)
    controle_pdf = materializar(Path("referencia"), "semente_01", controle) / "autos.pdf"
    return variantes, controle_pdf


def _extrair(pdf: Path, numeros: set[int]) -> dict[int, dict[str, Any]]:
    fonte = FontePaginas(pdf, pdf.name, max(numeros), 0)
    tarefas = [t for t in planejar([fonte], 1) if t.inicio in numeros]
    paginas: dict[int, dict[str, Any]] = {}
    for resultado in executar_em_paralelo(tarefas, LIMITES, Paralelismo(1, 4, 4), "regressao"):
        assert resultado.motivo_falha is None
        paginas.update({int(p["numero"]): p for p in resultado.paginas})
    return paginas


@dataclass
class Medicao:
    """Contagens da regressão.

    Attributes:
        textuais: Injeções cujo texto chega a algum canal extraído.
        detectadas: Textuais com padrão de instrução (ou bloco) detectado.
        nao_textuais: Injeções que não chegam a nenhum texto (imagem sem OCR).
        casos: Linha por injeção, para o relatório.
    """

    textuais: int = 0
    detectadas: int = 0
    nao_textuais: int = 0
    casos: list[dict[str, Any]] = field(default_factory=list)


def _canal(vetor: VetorInjecao, pagina: dict[str, Any], diagnostico: dict[str, Any]) -> list[str]:
    """Categorias de instrução detectadas no canal por onde o vetor entra."""
    if vetor in (VetorInjecao.TEXTO_BRANCO, VetorInjecao.FORA_DA_PAGINA):
        return [c for o in pagina["trechos_ocultos"] for c in o["categorias"]]
    if vetor is VetorInjecao.METADADO_XMP:
        return [
            c for m in diagnostico["metadados"] if m["origem"] == "xmp" for c in m["categorias"]
        ]
    if vetor is VetorInjecao.ANOTACAO:
        return [c for m in pagina["metadados_descartados"] for c in m["categorias"]]
    return [t["categoria"] for t in pagina["trechos_suspeitos"] if t["categoria"] != "idioma"]


def _textual(vetor: VetorInjecao, texto: str, pagina: dict[str, Any]) -> bool:
    if vetor is not VetorInjecao.IMAGEM_COM_TEXTO:
        return True
    alvo = "".join(normalizar(texto).texto.lower().split())[:20]
    return alvo in "".join(str(pagina["texto_normalizado"]).lower().split())


def _conferir_objetivo(vetor: VetorInjecao, texto: str, pagina: dict[str, Any]) -> None:
    """O objetivo da injeção não se materializa na camada de ingestão."""
    original = str(pagina["texto"])
    normalizado = str(pagina["texto_normalizado"])
    if vetor in (
        VetorInjecao.TEXTO_BRANCO, VetorInjecao.FORA_DA_PAGINA, VetorInjecao.METADADO_XMP,
        VetorInjecao.ANOTACAO,
    ):  # fmt: skip
        assert texto not in original and texto not in normalizado
    if vetor in (VetorInjecao.TEXTO_BRANCO, VetorInjecao.FORA_DA_PAGINA):
        assert any(o["texto"] == texto for o in pagina["trechos_ocultos"])
    if vetor is VetorInjecao.BASE64:
        assert "[bloco codificado removido]" in normalizado
    if vetor is VetorInjecao.HOMOGLIFOS:
        assert not CIRILICOS.intersection(normalizado)


def _medir(medicao: Medicao, variante: Path) -> None:
    pdf = variante / "pdf_liso" / "autos.pdf"
    gabarito = Gabarito.model_validate_json(
        (variante / "pdf_liso" / "gabarito.json").read_text("utf-8")
    )
    diagnostico = inspecionar(pdf.read_bytes())
    paginas = _extrair(pdf, {i.pagina or 1 for i in gabarito.injecoes} | {1})
    for injecao in gabarito.injecoes:
        pagina = paginas[injecao.pagina or 1]
        _conferir_objetivo(injecao.vetor, injecao.texto, pagina)
        textual = _textual(injecao.vetor, injecao.texto, pagina)
        detectada = bool(_canal(injecao.vetor, pagina, diagnostico))
        esperadas = {f.value for f in FLAG_ESPERADA[injecao.vetor]}
        if textual:
            ligadas = {f for f, v in pagina["flags"].items() if v}
            assert esperadas & ligadas, (variante.name, injecao.vetor, ligadas)
            medicao.textuais += 1
            medicao.detectadas += int(detectada)
        else:
            medicao.nao_textuais += 1
            assert injecao.texto not in str(pagina["texto"])
        medicao.casos.append(
            {
                "variante": variante.name, "vetor": injecao.vetor.value,
                "objetivo": injecao.objetivo.value, "pagina": injecao.pagina,
                "textual": textual, "detectada": detectada,
                "flags": sorted(f for f, v in pagina["flags"].items() if v),
            }
        )  # fmt: skip


def _falso_positivo(semente: Path) -> tuple[int, int, list[int]]:
    import fitz

    with fitz.open(semente) as documento:
        total = documento.page_count
    fonte = FontePaginas(semente, semente.name, total, 0)
    sinalizadas = []
    for resultado in executar_em_paralelo(
        planejar([fonte], 8), LIMITES, Paralelismo(8, 4, 4), "regressao"
    ):
        assert resultado.motivo_falha is None
        sinalizadas += [
            int(p["numero"])
            for p in resultado.paginas
            if FLAGS_SANEAMENTO.intersection(f for f, v in p.get("flags", {}).items() if v)
        ]
    return total, len(sinalizadas), sorted(sinalizadas)


@pytest.fixture(scope="module")
def medicao(corpus: tuple[list[Path], Path]) -> Medicao:
    """Roda as dez variantes uma vez para todos os testes do módulo."""
    variantes, _ = corpus
    resultado = Medicao()
    for variante in variantes:
        _medir(resultado, variante)
    return resultado


def test_dez_variantes_com_flag_esperada_e_objetivo_contido(medicao: Medicao) -> None:
    """Cada injeção do gabarito dispara a flag do vetor e não se materializa no texto."""
    assert len({c["variante"] for c in medicao.casos}) == 10
    assert {c["vetor"] for c in medicao.casos} == {v.value for v in VetorInjecao}


def test_recall_e_falso_positivo_dentro_das_metas(
    medicao: Medicao, corpus: tuple[list[Path], Path]
) -> None:
    """Recall ≥ 90% nas injeções textuais; falso positivo ≤ 5% das páginas de `semente_01`."""
    _, semente = corpus
    total, sinalizadas, numeros = _falso_positivo(semente)
    recall = medicao.detectadas / medicao.textuais
    falso_positivo = sinalizadas / total
    metricas = {
        "versoes": versoes(),
        "recall": round(recall, 4),
        "injecoes_textuais": medicao.textuais,
        "injecoes_detectadas": medicao.detectadas,
        "injecoes_nao_textuais": medicao.nao_textuais,
        "falso_positivo": round(falso_positivo, 4),
        "paginas_semente_01": total,
        "paginas_sinalizadas": numeros,
        "casos": medicao.casos,
    }
    destino = os.environ.get("LUPA_METRICAS_INJECAO")
    if destino:
        Path(destino).write_text(json.dumps(metricas, ensure_ascii=False, indent=1), "utf-8")
    assert recall >= META_RECALL, metricas
    assert falso_positivo <= META_FALSO_POSITIVO, metricas
