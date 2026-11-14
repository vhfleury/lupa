"""Executa os autos de referência na ingestão cível e compara o banco com cada gabarito.

Execute no contêiner da API, com os autos disponíveis em LUPA_SINTETICOS_DIR/referencia.
A opção --volume reaproveita linhas previamente extraídas na versão corrente, no PDF liso.
"""

import argparse
import gzip
import json
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from lupa_pipeline.config import Settings, get_settings
from lupa_pipeline.dominio.enums import ClasseProcessual, OrigemPeca, TipoPeca
from lupa_pipeline.dominio.repositorios import listar_achados, listar_fatos_por_processo
from lupa_pipeline.dominio.visoes import VisaoArquivo, VisaoPagina, VisaoParte, VisaoPeca
from lupa_pipeline.ingestao.calibracao import enviar_e_processar, semear_assessor
from lupa_pipeline.ingestao.eventos.saida import eventos_saida
from lupa_pipeline.ingestao.storage import ObjectStorage, criar_storage
from lupa_pipeline.logging import configurar_logging
from lupa_pipeline.sinteticos.achados import (
    comparar,
    referencias_de_paginas,
    referencias_do_gabarito,
)
from lupa_pipeline.sinteticos.gabarito import Cenario, Gabarito
from lupa_pipeline.sinteticos.medicao import medir
from lupa_pipeline.sinteticos.saida_pipeline import PecaSaida, RefPagina, SaidaPipeline

ORIGEM = "scripts.ponta_a_ponta"
NOMES = {
    Cenario.ZIP_POR_PECA: "autos.zip",
    Cenario.PDF_INDICE: "autos.pdf",
    Cenario.PDF_LISO: "autos.pdf",
}


def _saida(
    session: Session, processo: bytes, arquivo: bytes, gabarito: Gabarito
) -> tuple[SaidaPipeline, int, dict[str, str]]:
    paginas = {
        p.id: p
        for p in session.scalars(select(VisaoPagina).where(VisaoPagina.hk_arquivo == arquivo))
    }
    por_numero = {p.numero: p for p in paginas.values()}

    nomes = {
        p.id: p.nome
        for p in session.scalars(select(VisaoParte).where(VisaoParte.hk_processo == processo))
        if p.nome
    }
    origens = {f"entrada-{i}.pdf": a.nome for i, a in enumerate(gabarito.arquivos, start=1)}

    def ref(pagina: VisaoPagina) -> RefPagina:
        return RefPagina(
            arquivo=origens.get(pagina.origem_arquivo or "", pagina.origem_arquivo or "autos.pdf"),
            pagina=pagina.pagina_origem or pagina.numero,
        )

    pecas = session.scalars(
        select(VisaoPeca)
        .where(VisaoPeca.hk_arquivo == arquivo, VisaoPeca.vigente.is_(True))
        .order_by(VisaoPeca.pagina_inicial)
    )
    fatos = listar_fatos_por_processo(session, processo)

    referencias = {pid: ref(p) for pid, p in paginas.items()}
    saida = SaidaPipeline(
        pecas=tuple(
            PecaSaida(
                tipo=TipoPeca(p.tipo or TipoPeca.OUTROS),
                origem=OrigemPeca(p.origem or OrigemPeca.DESCONHECIDA),
                inicio=ref(por_numero[p.pagina_inicial]),
                fim=ref(por_numero[p.pagina_final or p.pagina_inicial]),
                data=p.data,
            )
            for p in pecas
        ),
        eventos=eventos_saida(fatos, referencias, nomes),
    )
    nao_literais = sum(
        all(
            (base or "")[e.inicio : e.fim] != e.trecho
            for base in (paginas[e.pagina_id].texto, paginas[e.pagina_id].texto_normalizado)
        )
        for f in fatos
        for e in f.evidencias
    )
    return saida, nao_literais, nomes | referencias_de_paginas(gabarito, referencias)


def _rodar(
    fabrica: sessionmaker[Session],
    settings: Settings,
    storage: ObjectStorage,
    usuario: bytes,
    pasta: Path,
    cenario: Cenario,
    volume: Path | None = None,
) -> dict[str, Any]:
    gabarito = Gabarito.model_validate_json((pasta / "gabarito.json").read_text(encoding="utf-8"))
    volume_lido = None
    if volume and cenario is Cenario.PDF_LISO:
        with gzip.open(
            volume / pasta.parent.name / cenario.value / "linhas.json.gz", "rt", encoding="utf-8"
        ) as entrada:
            volume_lido = json.load(entrada)
    execucao = enviar_e_processar(
        fabrica,
        settings,
        storage,
        usuario,
        pasta / NOMES[cenario],
        ClasseProcessual(gabarito.processo.classe),
        ORIGEM,
        volume=volume_lido,
    )
    with fabrica() as session:
        saida, nao_literais, referencias = _saida(
            session, execucao.processo_id, execucao.arquivo_id, gabarito
        )
        achados = listar_achados(session, execucao.processo_id)
        relatorio = session.get_one(VisaoArquivo, execucao.arquivo_id).relatorio or {}
    medicao = medir(gabarito, saida)
    comparacao = comparar(
        gabarito.resultado_esperado, achados, referencias_do_gabarito(gabarito), referencias
    )
    return {
        "processo": pasta.parent.name,
        "classe": gabarito.processo.classe,
        "cenario": cenario.value,
        "folhas": len(gabarito.paginas),
        "estado": execucao.estado.value,
        "paginas_do_volume": execucao.paginas_do_volume,
        "segundos_total": round(execucao.segundos, 2),
        "segundos_por_mil_paginas": round(execucao.segundos / len(gabarito.paginas) * 1000, 1),
        "extracao_parede_segundos": (relatorio.get("tempo") or {}).get("parede_segundos"),
        "por_tipo_pagina": relatorio.get("por_tipo"),
        "fronteira": medicao.fronteira.model_dump(),
        "tipo_peca": medicao.tipo_peca.model_dump(),
        "eventos": medicao.eventos.model_dump(),
        "datas": medicao.datas.model_dump() if medicao.datas else None,
        "fatos": len(saida.eventos),
        "evidencias_nao_literais": nao_literais,
        "eventos_relatorio": relatorio.get("eventos"),
        "achados": [c.model_dump() for c in comparacao],
        "achados_iguais": sum(c.resultado_igual and c.valores_iguais for c in comparacao),
    }


def main() -> int:
    """Interpreta as opções e imprime a medição para cada processo e empacotamento."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processos", default="semente_01")
    parser.add_argument("--cenarios", default="pdf_liso")
    parser.add_argument("--volume", type=Path)
    parser.add_argument("--repetir", action="store_true")
    args = parser.parse_args()
    raiz = Path(os.environ.get("LUPA_SINTETICOS_DIR", "/app/.sinteticos")) / "referencia"
    settings = get_settings()
    configurar_logging(nivel="WARNING")
    engine = create_engine(settings.database_url.get_secret_value())
    fabrica = sessionmaker(engine)
    storage = criar_storage(settings)
    linhas = []
    try:
        with fabrica.begin() as session:
            usuario = semear_assessor(session, ORIGEM)
        for processo in args.processos.split(","):
            for cenario in (Cenario(c) for c in args.cenarios.split(",")):
                pasta = raiz / processo / cenario.value
                linha = _rodar(fabrica, settings, storage, usuario, pasta, cenario, args.volume)
                if args.repetir:
                    repetida = _rodar(fabrica, settings, storage, usuario, pasta, cenario)
                    linha["repeticao_segundos"] = repetida["segundos_total"]
                linhas.append(linha)
                resumo = {
                    k: linha[k]
                    for k in ("processo", "cenario", "estado", "segundos_total", "achados_iguais")
                }
                print(json.dumps(resumo), file=sys.stderr, flush=True)
    finally:
        engine.dispose()
    configuracao = {
        "cpus": os.cpu_count(),
        "paginas_por_lote": settings.extracao_paginas_por_lote,
        "sandbox": {
            "memoria_mb": settings.sandbox_memoria_mb,
            "cpu_segundos": settings.sandbox_cpu_segundos,
        },
    }
    print(
        json.dumps({"configuracao": configuracao, "linhas": linhas}, ensure_ascii=False, indent=1)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
