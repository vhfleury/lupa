"""Sentido da dependência entre os pacotes: a intranet usa a pipeline, nunca o contrário (D2)."""

import ast
from pathlib import Path

import lupa_pipeline

PACOTE = Path(lupa_pipeline.__file__).resolve().parent
PACOTE_PROIBIDO = "lupa_intranet"


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
    return modulo == PACOTE_PROIBIDO or modulo.startswith(f"{PACOTE_PROIBIDO}.")


def test_nenhum_modulo_da_pipeline_importa_a_intranet() -> None:
    """RES-12: nenhum módulo de `lupa_pipeline` importa `lupa_intranet` (D2)."""
    violacoes = [
        f"{arquivo.relative_to(PACOTE)}: {modulo}"
        for arquivo in sorted(PACOTE.rglob("*.py"))
        for modulo in _modulos_importados(arquivo)
        if _importa_pacote_proibido(modulo)
    ]
    assert violacoes == []


def test_varredura_reconhece_import_da_intranet(tmp_path: Path) -> None:
    """RES-12: a varredura acusa `import` e `from ... import` da intranet, não nomes parecidos."""
    arquivo = tmp_path / "modulo.py"
    arquivo.write_text(
        "import lupa_intranet.api\nfrom lupa_intranet import agente\nimport lupa_intranetx\n",
        encoding="utf-8",
    )
    modulos = _modulos_importados(arquivo)
    assert [m for m in modulos if _importa_pacote_proibido(m)] == [
        "lupa_intranet.api",
        "lupa_intranet",
    ]
