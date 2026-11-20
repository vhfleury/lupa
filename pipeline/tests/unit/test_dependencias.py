"""Sentido da dependência entre os pacotes: a intranet usa a pipeline, nunca o contrário (D2)."""

import ast
from pathlib import Path

import lupa_pipeline

PACOTE = Path(lupa_pipeline.__file__).resolve().parent
SCRIPTS = PACOTE.parents[1] / "scripts"
PACOTES_PROIBIDOS = ("lupa_api", "lupa_web")


def _modulos_importados(arquivo: Path) -> list[str]:
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    modulos: list[str] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            modulos.extend(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
            modulos.append(no.module)
    return modulos


def _importa_pacote_proibido(modulo: str) -> bool:
    return any(
        modulo == proibido or modulo.startswith(f"{proibido}.") for proibido in PACOTES_PROIBIDOS
    )


def _arquivos_da_pipeline() -> list[Path]:
    return sorted(PACOTE.rglob("*.py")) + sorted(SCRIPTS.rglob("*.py"))


def test_pipeline_nao_importa_lupa_api_nem_lupa_web() -> None:
    """RES-12: nem `lupa_pipeline` nem `pipeline/scripts` importam `lupa_api` ou `lupa_web` (P1)."""
    violacoes = [
        f"{arquivo.name}: {modulo}"
        for arquivo in _arquivos_da_pipeline()
        for modulo in _modulos_importados(arquivo)
        if _importa_pacote_proibido(modulo)
    ]
    assert violacoes == []


def test_varredura_reconhece_import_da_intranet(tmp_path: Path) -> None:
    """RES-12: a varredura acusa `import` e `from ... import` da intranet, não nomes parecidos."""
    arquivo = tmp_path / "modulo.py"
    arquivo.write_text(
        "import lupa_api.api\nfrom lupa_web import telas\nimport lupa_apix\n",
        encoding="utf-8",
    )
    modulos = _modulos_importados(arquivo)
    assert [m for m in modulos if _importa_pacote_proibido(m)] == ["lupa_api.api", "lupa_web"]
