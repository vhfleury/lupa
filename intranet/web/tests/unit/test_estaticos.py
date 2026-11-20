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
