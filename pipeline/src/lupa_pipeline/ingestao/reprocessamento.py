"""Reagendamento seletivo dos arquivos quando mudam as versões de A5 (RF-ING-08)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from lupa_pipeline.dominio.enums import EstadoJob, StatusProcesso
from lupa_pipeline.dominio.gravacao import gravar_satelite, travar_processo
from lupa_pipeline.dominio.tabelas import sat_arquivo_ingestao
from lupa_pipeline.dominio.visoes import VisaoArquivo, VisaoProcesso
from lupa_pipeline.ingestao import extrator_paginas, indice
from lupa_pipeline.ingestao.eventos import fatos
from lupa_pipeline.ingestao.repositorio import (
    CAMPOS_VARIAVEIS,
    ESTADOS_PRONTOS,
    ORIGEM,
    atualizar_status_processo,
    ler_arquivo,
)
from lupa_pipeline.validacoes.dados import (
    cabimento_padrao,
    calendario_padrao,
    dispensas_padrao,
    prazos_recursos_padrao,
)
from lupa_pipeline.validacoes.versao import VERSAO_CATALOGO


def versoes_atuais() -> dict[str, Any]:
    """Identifica as regras e suas fontes versionadas em ordem de dependência."""
    _, calendario = calendario_padrao()
    fontes = {
        **calendario,
        "prazos": prazos_recursos_padrao().versao,
        "dispensas": dispensas_padrao().versao,
        "cabimento": cabimento_padrao().versao,
    }
    return {
        "paginas": extrator_paginas.VERSAO_EXTRATOR,
        "pecas": indice.versoes(),
        "fatos": f"{fatos.VERSAO}/dispensas={dispensas_padrao().versao}",
        "catalogo": "/".join([VERSAO_CATALOGO, *(f"{k}={v}" for k, v in sorted(fontes.items()))]),
    }


def primeira_etapa(arquivo: VisaoArquivo, atuais: dict[str, Any]) -> str | None:
    """Localiza a primeira dependência alterada, inclusive em relatórios anteriores à 0.2."""
    relatorio = arquivo.relatorio or {}
    anteriores = relatorio.get("versoes_processamento") or {
        "paginas": arquivo.versao_extrator,
        "pecas": (relatorio.get("indice") or {}).get("versoes"),
        "fatos": (relatorio.get("eventos") or {}).get("versao_extrator"),
    }
    return next(
        (
            etapa
            for etapa in ("paginas", "pecas", "fatos", "catalogo")
            if anteriores.get(etapa) != atuais[etapa]
        ),
        None,
    )


def reagendar_desatualizados(fabrica: sessionmaker[Session]) -> None:
    """Abre uma nova execução para cada arquivo pronto com versões desatualizadas."""
    atuais = versoes_atuais()
    with fabrica() as session:
        candidatos = session.execute(
            select(VisaoArquivo.hk_arquivo, VisaoArquivo.hk_processo)
            .join(VisaoProcesso, VisaoArquivo.hk_processo == VisaoProcesso.hk_processo)
            .where(
                VisaoProcesso.status != StatusProcesso.DESCARTADO,
                VisaoArquivo.estado.in_(ESTADOS_PRONTOS),
                VisaoArquivo.relatorio["paginas_total"].as_integer().is_not(None),
                VisaoArquivo.relatorio["versoes_processamento"].is_distinct_from(atuais),
            )
        ).all()
    for hk_arquivo, hk_processo in candidatos:
        with fabrica.begin() as session:
            processo = travar_processo(session, hk_processo)
            if processo is None or processo.status == StatusProcesso.DESCARTADO:
                continue
            arquivo = ler_arquivo(session, hk_arquivo)
            etapa = primeira_etapa(arquivo, atuais)
            if arquivo.estado not in ESTADOS_PRONTOS or etapa is None:
                continue
            dados = {campo: getattr(arquivo, campo) for campo in CAMPOS_VARIAVEIS}
            dados.update(
                estado=EstadoJob.EM_EXTRACAO.value,
                tentativas=0,
                motivo_quarentena=None,
                motivo_falha=None,
                relatorio=arquivo.relatorio | {"reprocessar_desde": etapa},
            )
            gravar_satelite(session, sat_arquivo_ingestao, hk_arquivo, dados, ORIGEM)
            atualizar_status_processo(session, hk_processo)
