"""Conformidade com o padrão visual: tokens nos CSS e componentes nos templates (RF-VIS-01, 04).

Segue o algoritmo A3 do plano do padrão visual; desde a fase 6 vale para todos os templates e CSS.
"""

import re
from pathlib import Path

PACOTE = Path(__file__).resolve().parents[2] / "src" / "lupa_web"
PASTA_CSS = PACOTE / "static" / "css"
PASTA_TEMPLATES = PACOTE / "templates"
COR_OU_FONTE_LITERAL = re.compile(
    r":[^;{}]*(#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\()|font-family\s*:(?!\s*var\()", re.I
)
MARCACAO_PROPRIA = re.compile(r"<button|<table|<progress|class=\"aviso", re.I)


def ocorrencias(arquivos: list[Path], raiz: Path, padrao: re.Pattern[str]) -> list[str]:
    """Linhas com o padrão proibido nos arquivos.

    Args:
        arquivos: Arquivos a varrer.
        raiz: Pasta de onde o caminho relativo é tirado.
        padrao: Expressão proibida.

    Returns:
        `arquivo:linha: texto` de cada ocorrência.
    """
    achadas = []
    for arquivo in arquivos:
        relativo = arquivo.relative_to(raiz).as_posix()
        for numero, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
            if padrao.search(linha):
                achadas.append(f"{relativo}:{numero}: {linha.strip()}")
    return achadas


def test_css_de_tela_nao_tem_cor_nem_fonte_literal() -> None:
    """RF-VIS-01 (D5): fora de `tokens.css`, nenhum CSS declara cor ou fonte literal."""
    folhas = [f for f in sorted(PASTA_CSS.glob("*.css")) if f.name != "tokens.css"]
    assert ocorrencias(folhas, PASTA_CSS, COR_OU_FONTE_LITERAL) == []


def test_templates_de_tela_usam_componentes() -> None:
    """RF-VIS-04 (D5): fora de `componentes/` não há marcação própria de componente."""
    templates = [
        t
        for t in sorted(PASTA_TEMPLATES.rglob("*.html"))
        if not t.relative_to(PASTA_TEMPLATES).as_posix().startswith("componentes/")
    ]
    assert ocorrencias(templates, PASTA_TEMPLATES, MARCACAO_PROPRIA) == []
