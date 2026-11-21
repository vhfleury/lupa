"""Índice de peças e histórico das classificações no Data Vault (A5, A12)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.enums import MetodoClassificacao, OrigemPeca, TipoPeca
from lupa_pipeline.dominio.esquemas import calcular_hash
from lupa_pipeline.dominio.gravacao import gravar_hub, gravar_link, gravar_satelite
from lupa_pipeline.dominio.tabelas import (
    hub_evidencia,
    hub_peca,
    link_arquivo_peca,
    link_pagina_evidencia,
    sat_evidencia_trecho,
    sat_pagina_fronteira,
    sat_peca_classificacao,
)
from lupa_pipeline.dominio.visoes import (
    VisaoArquivo,
    VisaoEvidencia,
    VisaoPeca,
    VisaoPecaHistorico,
    atual,
)
from lupa_pipeline.ingestao.indice import ResultadoIndice
from lupa_pipeline.ingestao.repositorio import ORIGEM, atributos


class ReclassificacaoInvalidaError(ValueError):
    """Pedido fora do intervalo do arquivo ou peça que deixou de ser vigente."""


def gravar_evidencia(
    session: Session,
    pagina: dict[str, Any],
    inicio: int,
    fim: int,
    trecho: str,
    bbox: dict[str, Any] | None = None,
) -> bytes:
    """Confere os offsets e grava o trecho com o vínculo à página."""
    texto = pagina["texto"]
    if not trecho or inicio < 0 or fim > len(texto) or texto[inicio:fim] != trecho:
        raise ValueError("o trecho não confere com o texto da página")
    chave = {campo: pagina[campo] for campo in ("numero_cnj", "sha256", "numero")}
    hk = gravar_hub(session, hub_evidencia, chave | {"inicio": inicio, "fim": fim}, ORIGEM)
    ligacao = {"hk_pagina": pagina["hk_pagina"], "hk_evidencia": hk}
    gravar_link(session, link_pagina_evidencia, ligacao, ORIGEM)
    dados = {"trecho": trecho, "hash_trecho": calcular_hash(trecho), "bbox": bbox}
    gravar_satelite(session, sat_evidencia_trecho, hk, dados, ORIGEM)
    return hk


def _hub(session: Session, arquivo: VisaoArquivo, inicio: int) -> bytes:
    chave = {"numero_cnj": arquivo.numero_cnj, "sha256": arquivo.sha256, "pagina_inicial": inicio}
    hk = gravar_hub(session, hub_peca, chave, ORIGEM)
    gravar_link(
        session, link_arquivo_peca, {"hk_arquivo": arquivo.hk_arquivo, "hk_peca": hk}, ORIGEM
    )
    return hk


def gravar_indice(
    session: Session,
    arquivo: VisaoArquivo,
    paginas: list[dict[str, Any]],
    resultado: ResultadoIndice,
) -> int:
    """Grava fronteiras e versões automáticas, preservando intervalos corrigidos pelo usuário."""
    for pagina, sinais in zip(paginas, resultado.sinais, strict=True):
        publicos = {chave: valor for chave, valor in sinais.items() if chave != "cabecalho"}
        gravar_satelite(
            session,
            sat_pagina_fronteira,
            pagina["hk_pagina"],
            {"sinais_fronteira": publicos},
            ORIGEM,
        )
    por_numero = {p["numero"]: p for p in paginas}
    existentes = list(
        session.scalars(atual(select(VisaoPeca).where(VisaoPeca.hk_arquivo == arquivo.hk_arquivo)))
    )
    manuais = [p for p in existentes if p.metodo == MetodoClassificacao.MANUAL]
    vigentes: set[bytes] = set()
    inseridas = 0
    for peca in resultado.pecas:
        if any(
            p.pagina_inicial == peca.pagina_inicial
            or (
                p.vigente
                and p.pagina_inicial <= peca.pagina_final
                and (p.pagina_final or p.pagina_inicial) >= peca.pagina_inicial
            )
            for p in manuais
        ):
            continue
        evidencia = peca.evidencia_data
        hk_evidencia = (
            gravar_evidencia(
                session,
                por_numero[evidencia["pagina"]],
                evidencia["inicio"],
                evidencia["fim"],
                evidencia["trecho"],
            )
            if evidencia
            else None
        )
        hk = _hub(session, arquivo, peca.pagina_inicial)
        dados = {
            "tipo": peca.tipo.value,
            "origem": peca.origem.value,
            "metodo": peca.metodo.value,
            "pagina_final": peca.pagina_final,
            "confianca": peca.confianca,
            "data": peca.data,
            "tipo_data": peca.tipo_data,
            "hk_evidencia_data": hk_evidencia,
            "flags": peca.flags,
            "classificacao": peca.classificacao,
            "vigente": True,
            "hk_usuario": None,
        }
        inseridas += gravar_satelite(session, sat_peca_classificacao, hk, dados, ORIGEM)
        vigentes.add(hk)
    for antiga in existentes:
        if (
            antiga.metodo != MetodoClassificacao.MANUAL
            and antiga.vigente
            and antiga.hk_peca not in vigentes
        ):
            gravar_satelite(
                session,
                sat_peca_classificacao,
                antiga.hk_peca,
                atributos(antiga, sat_peca_classificacao) | {"vigente": False},
                ORIGEM,
            )
    return inseridas


def resumo_flags(flags: dict[str, Any]) -> dict[str, Any]:
    """Agrupa os sinais das peças e o número de páginas por marca de saneamento."""
    paginas = dict(flags.get("paginas") or {})
    return {
        "peca": sorted(k for k, v in (flags.get("peca") or {}).items() if v),
        "saneamento": paginas,
        "total_saneamento": sum(paginas.values()),
    }


def _evidencias(
    session: Session, pecas: Sequence[VisaoPeca | VisaoPecaHistorico]
) -> dict[bytes, VisaoEvidencia]:
    chaves = {p.hk_evidencia_data for p in pecas if p.hk_evidencia_data}
    if not chaves:
        return {}
    consulta = select(VisaoEvidencia).where(VisaoEvidencia.hk_evidencia.in_(chaves))
    return {evidencia.hk_evidencia: evidencia for evidencia in session.scalars(consulta)}


def _serializar(
    peca: VisaoPeca | VisaoPecaHistorico,
    arquivo_id: str,
    evidencias: Mapping[bytes, VisaoEvidencia],
) -> dict[str, Any]:
    evidencia = evidencias.get(peca.hk_evidencia_data) if peca.hk_evidencia_data else None
    campos = (
        "tipo",
        "origem",
        "pagina_inicial",
        "pagina_final",
        "data",
        "tipo_data",
        "confianca",
        "metodo",
        "vigente",
        "flags",
        "classificacao",
    )
    return {campo: getattr(peca, campo) for campo in campos} | {
        "id": peca.hk_peca.hex(),
        "arquivo_id": arquivo_id,
        "resumo_flags": resumo_flags(peca.flags or {}),
        "autor_id": peca.hk_usuario.hex() if peca.hk_usuario else None,
        "alterado_em": peca.classificada_em if isinstance(peca, VisaoPeca) else peca.load_dts,
        "evidencia_data": None
        if evidencia is None
        else {
            campo: getattr(evidencia, campo)
            for campo in ("id", "pagina_id", "trecho", "inicio", "fim", "hash_trecho")
        },
    }


def indice_processo(session: Session, processo_id: bytes) -> list[dict[str, Any]]:
    """Lista as peças vigentes do processo em ordem de arquivo e página."""
    consulta = (
        select(VisaoPeca)
        .join(VisaoArquivo, VisaoPeca.hk_arquivo == VisaoArquivo.hk_arquivo)
        .where(VisaoPeca.hk_processo == processo_id, VisaoPeca.vigente.is_(True))
        .order_by(VisaoArquivo.criado_em, VisaoArquivo.id, VisaoPeca.pagina_inicial)
    )
    pecas = list(session.scalars(atual(consulta)))
    evidencias = _evidencias(session, pecas)
    return [_serializar(p, p.arquivo_id, evidencias) | {"ordem": n} for n, p in enumerate(pecas, 1)]


def obter_peca(session: Session, processo_id: bytes, peca_id: str) -> VisaoPeca | None:
    """Busca uma peça pelo id público dentro do processo."""
    return session.scalar(
        atual(
            select(VisaoPeca).where(VisaoPeca.hk_processo == processo_id, VisaoPeca.id == peca_id)
        )
    )


def detalhar_peca(session: Session, peca: VisaoPeca) -> dict[str, Any]:
    """Devolve a peça corrente e as classificações anteriores, com autor e instante."""
    chaves = [peca.hk_peca] + [
        bytes.fromhex(i) for i in (peca.classificacao or {}).get("anteriores", [])
    ]
    consulta = (
        select(VisaoPecaHistorico)
        .where(VisaoPecaHistorico.hk_peca.in_(chaves))
        .order_by(VisaoPecaHistorico.load_dts.desc())
    )
    anteriores = [
        p
        for p in session.scalars(consulta)
        if p.load_dts != peca.classificada_em or p.hk_peca != peca.hk_peca
    ]
    evidencias = _evidencias(session, [peca, *anteriores])
    historico = [_serializar(p, peca.arquivo_id, evidencias) for p in anteriores]
    return _serializar(peca, peca.arquivo_id, evidencias) | {"historico": historico}


@dataclass(frozen=True)
class PedidoReclassificacao:
    """Classificação ou novo intervalo solicitado pelo usuário (A12)."""

    tipo: TipoPeca | None = None
    origem: OrigemPeca | None = None
    pagina_inicial: int | None = None
    pagina_final: int | None = None


def reclassificar(
    session: Session, peca: VisaoPeca, pedido: PedidoReclassificacao, usuario: bytes
) -> VisaoPeca:
    """Insere classificação manual e encerra a peça de origem quando a chave muda."""
    arquivo = session.get_one(VisaoArquivo, peca.hk_arquivo)
    inicio = peca.pagina_inicial if pedido.pagina_inicial is None else pedido.pagina_inicial
    fim = peca.pagina_final if pedido.pagina_final is None else pedido.pagina_final
    if not peca.vigente or not fim or not 1 <= inicio <= fim <= (arquivo.total_paginas or 0):
        raise ReclassificacaoInvalidaError("peça sem vigência ou intervalo fora do arquivo")
    hk = _hub(session, arquivo, inicio)
    dados = atributos(peca, sat_peca_classificacao) | {
        "metodo": MetodoClassificacao.MANUAL.value,
        "hk_usuario": usuario,
        "pagina_final": fim,
        "confianca": 1.0,
    }
    if pedido.tipo is not None:
        dados["tipo"] = pedido.tipo.value
    if pedido.origem is not None:
        dados["origem"] = pedido.origem.value
    if peca.hk_evidencia_data:
        evidencia = session.get_one(VisaoEvidencia, peca.hk_evidencia_data)
        if not inicio <= evidencia.numero <= fim:
            dados.update(data=None, tipo_data=None, hk_evidencia_data=None)
    if hk != peca.hk_peca:
        gravar_satelite(
            session,
            sat_peca_classificacao,
            peca.hk_peca,
            atributos(peca, sat_peca_classificacao)
            | {"vigente": False, "hk_usuario": usuario, "metodo": "manual"},
            ORIGEM,
        )
        anteriores = (peca.classificacao or {}).get("anteriores", [])
        dados["classificacao"] = (peca.classificacao or {}) | {
            "anteriores": list(dict.fromkeys([peca.id, *anteriores]))
        }
    gravar_satelite(session, sat_peca_classificacao, hk, dados, ORIGEM)
    return session.scalars(atual(select(VisaoPeca).where(VisaoPeca.hk_peca == hk))).one()
