"""Templates sem estilo nem script inline e folhas de estilo existentes (RF-INT-02, D7)."""

import re
from pathlib import Path

import pytest

PACOTE = Path(__file__).resolve().parents[2] / "src" / "lupa_web"
TEMPLATES = sorted((PACOTE / "templates").rglob("*.html"))
INLINE = re.compile(r"\sstyle=|<style[\s>]|<script(?![^>]*\bsrc=)[^>]*>|\son[a-z]+=", re.I)
ESTATICO = re.compile(r"{% static '([^']+)' %}")


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.name)
def test_template_nao_tem_estilo_nem_script_inline(template: Path) -> None:
    """RF-INT-02 (D7): a CSP `style-src 'self'` não admite estilo nem script inline."""
    assert INLINE.search(template.read_text(encoding="utf-8")) is None


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.name)
def test_arquivos_estaticos_citados_existem(template: Path) -> None:
    """RF-INT-02 (D7): cada folha de estilo e script citado está em `static/`."""
    for caminho in ESTATICO.findall(template.read_text(encoding="utf-8")):
        assert (PACOTE / "static" / caminho).is_file(), caminho


FONTE_URL = re.compile(r"url\(['\"]?([^'\")]+)['\"]?\)")
FONTES_ESPERADAS = {
    ("Source Serif 4", "600", "normal"),
    ("Source Sans 3", "400", "normal"),
    ("Source Sans 3", "400", "italic"),
    ("Source Sans 3", "600", "normal"),
    ("Source Code Pro", "400", "normal"),
}


def _faces() -> list[dict[str, str]]:
    css = (PACOTE / "static" / "css" / "tokens.css").read_text(encoding="utf-8")
    faces = []
    for corpo in re.findall(r"@font-face\s*\{([^}]*)\}", css):
        propriedades = dict(re.findall(r"([\w-]+)\s*:\s*([^;]+);", corpo))
        faces.append({nome: valor.strip().strip("'\"") for nome, valor in propriedades.items()})
    return faces


def test_tokens_declaram_as_cinco_faces_source_com_swap() -> None:
    """RF-VIS-02 (D3): as cinco faces mínimas, em woff2 com `font-display: swap`."""
    faces = _faces()
    declaradas = {(f["font-family"], f["font-weight"], f["font-style"]) for f in faces}
    assert declaradas == FONTES_ESPERADAS
    assert {f["font-display"] for f in faces} == {"swap"}


def test_fontes_declaradas_existem_na_propria_origem() -> None:
    """RF-VIS-02 (D4): cada `src` aponta para um woff2 de `static/fontes/`, com a licença OFL."""
    pasta_css = PACOTE / "static" / "css"
    for face in _faces():
        (url,) = FONTE_URL.findall(face["src"])
        assert url.startswith("../fontes/") and url.endswith(".woff2"), url
        assert (pasta_css / url).resolve().is_file(), url
    licenca = (PACOTE / "static" / "fontes" / "LICENSE.md").read_text(encoding="utf-8")
    assert "SIL Open Font License, Version 1.1" in licenca
