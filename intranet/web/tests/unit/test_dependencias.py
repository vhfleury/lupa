"""Sentido da dependência: `lupa_web` só fala com a API por HTTP (RES-12)."""

import ast
from pathlib import Path

import lupa_web

PACOTE = Path(lupa_web.__file__).resolve().parent
PACOTES_PROIBIDOS = ("lupa_api", "lupa_pipeline")


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


def test_lupa_web_nao_importa_lupa_api_nem_lupa_pipeline() -> None:
    """RES-12: nenhum módulo de `lupa_web` importa `lupa_api` ou `lupa_pipeline`."""
    arquivos = sorted(PACOTE.rglob("*.py"))
    violacoes = [
        f"{arquivo.name}: {modulo}"
        for arquivo in arquivos
        for modulo in _modulos_importados(arquivo)
        if _importa_pacote_proibido(modulo)
    ]
    assert arquivos
    assert violacoes == []


def test_varredura_reconhece_import_dos_outros_pacotes(tmp_path: Path) -> None:
    """RES-12: a varredura acusa `import` e `from ... import`, não nomes parecidos."""
    arquivo = tmp_path / "modulo.py"
    arquivo.write_text(
        "import lupa_api.api\nfrom lupa_pipeline import ingestao\nimport lupa_apix\n",
        encoding="utf-8",
    )
    modulos = _modulos_importados(arquivo)
    assert [m for m in modulos if _importa_pacote_proibido(m)] == ["lupa_api.api", "lupa_pipeline"]
