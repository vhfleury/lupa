"""Calibra a ingestão de um PDF ou ZIP cível e grava as evidências para conferência manual."""

import argparse
import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lupa_pipeline.config import get_settings
from lupa_pipeline.dominio.enums import ClasseProcessual
from lupa_pipeline.ingestao.calibracao import (
    coletar,
    enviar_e_processar,
    para_markdown,
    semear_assessor,
)
from lupa_pipeline.ingestao.storage import criar_storage
from lupa_pipeline.logging import configurar_logging


def main(argv: list[str] | None = None) -> int:
    """Executa a calibração e grava ``relatorio.md`` e ``relatorio.json``.

    Args:
        argv: Argumentos (padrão: os da linha de comando).

    Returns:
        Código de saída (0 se o job terminou concluído ou parcial).
    """
    parser = argparse.ArgumentParser(prog="calibrar.py", description=__doc__.splitlines()[0])
    parser.add_argument("arquivo", type=Path, help="PDF ou ZIP dos autos")
    parser.add_argument("--saida", type=Path, default=Path("/tmp/calibracao"))  # noqa: S108
    parser.add_argument("--titulo", default="processo de calibração")
    parser.add_argument(
        "--classe", choices=list(ClasseProcessual), default=ClasseProcessual.APELACAO_CIVEL.value
    )
    args = parser.parse_args(argv)
    settings = get_settings()
    configurar_logging(nivel="WARNING")
    engine = create_engine(settings.database_url.get_secret_value())
    fabrica = sessionmaker(engine)
    try:
        with fabrica.begin() as session:
            usuario = semear_assessor(session, "scripts.calibrar")
        execucao = enviar_e_processar(
            fabrica,
            settings,
            criar_storage(settings),
            usuario,
            args.arquivo,
            ClasseProcessual(args.classe),
            "scripts.calibrar",
        )
        with fabrica() as session:
            dados = coletar(session, execucao.processo_id, execucao.arquivo_id)
    finally:
        engine.dispose()
    dados["execucao"] = {
        "processo_id": execucao.processo_id.hex(),
        "estado": execucao.estado.value,
        "segundos": round(execucao.segundos, 2),
    }
    args.saida.mkdir(parents=True, exist_ok=True)
    (args.saida / "relatorio.md").write_text(para_markdown(dados, args.titulo), encoding="utf-8")
    (args.saida / "relatorio.json").write_text(
        json.dumps(dados, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
    )
    concluiu = dados["execucao"]["estado"] in ("concluido", "parcial")
    return 0 if concluiu else 1


if __name__ == "__main__":
    raise SystemExit(main())
