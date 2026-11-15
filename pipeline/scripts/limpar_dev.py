"""Descarta o conteúdo dos processos criados pelos roteiros de desenvolvimento.

Execute na imagem da API. A opção --sim efetiva o descarte e a limpeza do storage.
A simulação informa a contagem de processos ativos. Uma nova execução retoma os objetos
pendentes de processos já descartados e preserva a cadeia de auditoria.
"""

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from lupa_intranet.auditoria.eventos import AcaoAuditoria, NovoEvento, ResultadoEvento
from lupa_intranet.auditoria.registrador import registrar
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session

from lupa_pipeline.config import get_settings
from lupa_pipeline.dominio.gravacao import travar_processo
from lupa_pipeline.dominio.tabelas import hub_processo
from lupa_pipeline.dominio.visoes import VisaoProcesso
from lupa_pipeline.ingestao.storage import ObjectStorage, criar_storage
from lupa_pipeline.seguranca.contexto import esquecer_processo
from lupa_pipeline.seguranca.descarte import apagar_objetos, descartar

ORIGENS = ("scripts.calibrar", "scripts.ponta_a_ponta", "scripts.e2e")
AMBIENTES_PERMITIDOS = {"desenvolvimento", "teste"}


class RecusaError(ValueError):
    """O script foi invocado em uma instalação de produção."""


@dataclass(frozen=True)
class Resultado:
    """Quantidades de processos selecionados e de objetos removidos."""

    processos: int
    objetos_apagados: int


def limpar(engine: Engine, *, executar: bool, ambiente: str, storage: ObjectStorage) -> Resultado:
    """Aplica o descarte aos processos marcados pelos scripts de desenvolvimento (RF-PRO-05)."""
    if ambiente not in AMBIENTES_PERMITIDOS:
        raise RecusaError("uso permitido apenas em desenvolvimento ou teste")
    consulta = (
        select(VisaoProcesso.hk_processo, VisaoProcesso.status)
        .join(hub_processo, hub_processo.c.hk_processo == VisaoProcesso.hk_processo)
        .where(hub_processo.c.record_source.in_(ORIGENS))
        .order_by(VisaoProcesso.id)
    )
    with Session(engine) as session:
        alvos = session.execute(consulta).tuples().all()
    total = sum(status != "descartado" for _, status in alvos)
    if not executar:
        return Resultado(total, 0)
    objetos = 0
    for hk, _ in alvos:
        with Session(engine) as session, session.begin():
            processo = travar_processo(session, hk)
            if processo and processo.status != "descartado":
                hash_dek = descartar(session, hk)
                registrar(
                    session,
                    NovoEvento(
                        acao=AcaoAuditoria.PROCESSO_DESCARTADO,
                        hk_processo=hk,
                        objeto_tipo="dek_sha256",
                        objeto_id=hash_dek,
                    ),
                )
        esquecer_processo(hk)
        try:
            objetos += apagar_objetos(storage, hk)
        except Exception:
            with Session(engine) as session, session.begin():
                registrar(
                    session,
                    NovoEvento(
                        acao=AcaoAuditoria.DESCARTE_OBJETOS_PENDENTE,
                        resultado=ResultadoEvento.FALHA,
                        hk_processo=hk,
                        objeto_tipo="processo",
                        objeto_id=hk.hex(),
                    ),
                )
            raise
    return Resultado(total, objetos)


def main(argumentos: Sequence[str]) -> int:
    """Simula ou efetiva a limpeza na instalação configurada."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sim", action="store_true", help="descartar o conteúdo e apagar os objetos"
    )
    args = parser.parse_args(argumentos)
    settings = get_settings()
    if settings.ambiente not in AMBIENTES_PERMITIDOS:
        sys.stderr.write("Uso permitido apenas em desenvolvimento ou teste.\n")
        return 2
    engine = create_engine(settings.database_url.get_secret_value())
    try:
        resultado = limpar(
            engine, executar=args.sim, ambiente=settings.ambiente, storage=criar_storage(settings)
        )
    finally:
        engine.dispose()
    verbo = "descartados" if args.sim else "selecionados para descarte"
    print(
        f"Processos {verbo}: {resultado.processos}. Objetos apagados: {resultado.objetos_apagados}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
