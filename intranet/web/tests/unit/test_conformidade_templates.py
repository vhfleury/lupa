"""Conformidade com o padrão visual: tokens nos CSS e componentes nos templates (RF-VIS-01, 04).

Segue o algoritmo A3 do plano do padrão visual. Os grupos de telas ainda não migrados ficam em
`PENDENTES`; cada fase de migração tira o seu grupo.
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
PENDENTES = {
    "dossie": (
        "processos/dossie.html",
        "processos/validacoes.html",
        "processos/visualizador.html",
        "dossie.css",
        "validacoes.css",
        "visualizador.css",
    ),
    "chat": ("chat/", "chat.css"),
    "gestao": ("auditoria/", "usuarios/", "auditoria.css", "usuarios.css"),
}


def _pendente(relativo: str) -> bool:
    return any(relativo.startswith(item) for grupo in PENDENTES.values() for item in grupo)


def ocorrencias(arquivos: list[Path], raiz: Path, padrao: re.Pattern[str]) -> list[str]:
    """Linhas com o padrão proibido nos arquivos fora da lista de pendentes.

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
        if _pendente(relativo):
            continue
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


def test_pendentes_citam_arquivos_que_existem() -> None:
    """RF-VIS-04 (D5): cada item da lista de pendentes é um template ou CSS existente."""
    for grupo, itens in PENDENTES.items():
        for item in itens:
            raiz = PASTA_CSS if item.endswith(".css") else PASTA_TEMPLATES
            assert (raiz / item).exists(), f"{grupo}: {item}"
