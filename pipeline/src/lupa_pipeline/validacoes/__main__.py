"""CLI das validações: python -m lupa_pipeline.validacoes --fatos ARQUIVO --classe CLASSE."""

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from lupa_pipeline.dominio.enums import ClasseProcessual
from lupa_pipeline.dominio.esquemas import Fato
from lupa_pipeline.validacoes.modelo import ModeloProcesso
from lupa_pipeline.validacoes.motor import executar_catalogo


def main(argv: Sequence[str] | None = None) -> int:
    """Produz os mesmos achados da ingestão a partir de fatos de um único processo."""
    parser = argparse.ArgumentParser(prog="python -m lupa_pipeline.validacoes")
    parser.add_argument("--fatos", type=Path, required=True, help="arquivo JSON de fatos")
    parser.add_argument("--classe", required=True, choices=[c.value for c in ClasseProcessual])
    parser.add_argument("--referencia", type=date.fromisoformat)
    args = parser.parse_args(argv)
    try:
        fatos = TypeAdapter(list[Fato]).validate_json(args.fatos.read_text(encoding="utf-8"))
    except (OSError, ValueError, ValidationError):
        parser.error("não foi possível ler o arquivo de fatos ou validar o seu formato")
    if len({f.processo_id for f in fatos}) > 1:
        parser.error("o arquivo deve conter fatos de um único processo")
    achados = executar_catalogo(ModeloProcesso(fatos), args.classe, args.referencia or date.today())
    sys.stdout.write(
        json.dumps([a.model_dump(mode="json") for a in achados], ensure_ascii=False, indent=2)
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
