"""Estado da ingestão de cada arquivo como satélite de `hub_arquivo` (D9; RF-ING-06).

Não há job nem lease: o estado corrente é a linha mais recente de `sat_arquivo_ingestao`, lida
por `v_arquivo`. Toda mudança é linha nova com todos os atributos (D6): `mudar_estado` copia os
atributos correntes, aplica as mudanças, confere a máquina de `ingestao.estados` quando o estado
muda e grava por `dominio.gravacao`. O status do processo segue os estados dos seus arquivos
(A5, passo 11).
"""

from collections.abc import Callable
from typing import Any

from sqlalchemy import Table, select
from sqlalchemy.orm import Session, defer
from sqlalchemy.orm.attributes import set_committed_value

from lupa_pipeline.dominio.enums import EstadoJob, MotivoFalha, MotivoQuarentena, StatusProcesso
from lupa_pipeline.dominio.gravacao import gravar_satelite, travar_processo
from lupa_pipeline.dominio.tabelas import (
    atributos_do_satelite,
    sat_arquivo_ingestao,
    sat_processo_estado,
)
from lupa_pipeline.dominio.visoes import VisaoArquivo, VisaoPagina, VisaoProcesso, atual
from lupa_pipeline.ingestao.estados import exigir_transicao
from lupa_pipeline.ingestao.qualidade import resumo_saneamento

_trocar_sem_gravar: Callable[[object, str, Any], None] = set_committed_value
ORIGEM = "pipeline.ingestao"
ESTADOS_EM_ANDAMENTO = frozenset({EstadoJob.RECEBIDO, EstadoJob.VALIDADO, EstadoJob.EM_EXTRACAO})
ESTADOS_PRONTOS = frozenset({EstadoJob.CONCLUIDO, EstadoJob.PARCIAL})
STATUS_FIXOS = frozenset(
    {StatusProcesso.ARQUIVADO, StatusProcesso.EM_REVISAO, StatusProcesso.DESCARTADO}
)
CAMPOS_VARIAVEIS = frozenset(
    {"tentativas", "total_paginas", "manifesto", "relatorio", "versao_extrator"}
)


class ArquivoNaoEncontradoError(LookupError):
    """O arquivo não existe (ou não tem estado de ingestão)."""


def ler_arquivo(session: Session, hk_arquivo: bytes) -> VisaoArquivo:
    """Lê o arquivo com o estado corrente, relendo o que a sessão já tinha carregado.

    Args:
        session: Sessão com transação aberta.
        hk_arquivo: Arquivo.

    Returns:
        A linha de `v_arquivo`.

    Raises:
        ArquivoNaoEncontradoError: Arquivo inexistente.
    """
    consulta = (
        select(VisaoArquivo)
        .where(VisaoArquivo.hk_arquivo == hk_arquivo)
        .options(defer(VisaoArquivo.nome_original))
    )
    arquivo = session.scalars(atual(consulta)).one_or_none()
    if arquivo is None:
        raise ArquivoNaoEncontradoError(hk_arquivo.hex())
    return arquivo


def registrar_recebido(session: Session, hk_arquivo: bytes) -> None:
    """Grava o primeiro estado do arquivo: `recebido`, sem tentativa (A3, passo 7).

    Args:
        session: Sessão com transação aberta (hub do arquivo já gravado).
        hk_arquivo: Arquivo.
    """
    atributos = dict.fromkeys(atributos_do_satelite(sat_arquivo_ingestao))
    atributos |= {"estado": EstadoJob.RECEBIDO.value, "tentativas": 0}
    gravar_satelite(session, sat_arquivo_ingestao, hk_arquivo, atributos, ORIGEM)


def atributos(visao: Any, satelite: Table) -> dict[str, Any]:
    """Copia da linha da view os atributos de negócio de um satélite.

    Args:
        visao: Linha de uma view `v_*` que expõe as colunas do satélite.
        satelite: Satélite cujos atributos são copiados.

    Returns:
        Os atributos do satélite com os valores da linha.
    """
    return {campo: getattr(visao, campo) for campo in atributos_do_satelite(satelite)}


def processo_ativo(session: Session, hk_processo: bytes) -> VisaoProcesso | None:
    """Trava o processo com a trava do descarte e o devolve se não foi descartado (RF-ING-07).

    Args:
        session: Sessão com transação aberta.
        hk_processo: Processo.

    Returns:
        A linha de `v_processo` relida sob a trava, ou None se o processo não existe ou foi
        descartado.
    """
    processo = travar_processo(session, hk_processo)
    if processo is None or processo.status == StatusProcesso.DESCARTADO:
        return None
    return processo


def mudar_estado(
    session: Session,
    hk_arquivo: bytes,
    novo: EstadoJob,
    *,
    motivo_quarentena: MotivoQuarentena | None = None,
    motivo_falha: MotivoFalha | None = None,
    **mudancas: Any,
) -> VisaoArquivo:
    """Grava uma linha nova do estado da ingestão do arquivo.

    Os motivos valem só para a linha nova; os demais atributos (`tentativas`, `total_paginas`,
    `manifesto`, `relatorio`, `versao_extrator`) vêm da linha corrente, salvo os informados.
    Manter o estado (para mudar só a contagem de tentativas, por exemplo) não passa pela
    máquina de estados.

    Args:
        session: Sessão com transação aberta.
        hk_arquivo: Arquivo.
        novo: Estado da linha nova.
        motivo_quarentena: Obrigatório quando `novo` é `quarentena` (CHECK do satélite).
        motivo_falha: Motivo quando `novo` é `falho`.
        **mudancas: Atributos que mudam na linha nova.

    Returns:
        A linha de `v_arquivo` lida antes da gravação, com os atributos do satélite trocados
        pelos gravados, sem reler a view; `estado_em` continua o da linha anterior.

    Raises:
        ArquivoNaoEncontradoError: Arquivo inexistente.
        TransicaoInvalidaError: Mudança de estado não permitida.
        ValueError: Atributo desconhecido em `mudancas`.
    """
    desconhecidos = set(mudancas) - CAMPOS_VARIAVEIS
    if desconhecidos:
        raise ValueError(f"atributos desconhecidos: {sorted(desconhecidos)}")
    arquivo = ler_arquivo(session, hk_arquivo)
    corrente = EstadoJob(arquivo.estado) if arquivo.estado else None
    if corrente is None:
        raise ArquivoNaoEncontradoError(hk_arquivo.hex())
    if novo is not corrente:
        exigir_transicao(corrente, novo)
    dados = atributos(arquivo, sat_arquivo_ingestao) | mudancas
    dados |= {
        "estado": novo.value,
        "motivo_quarentena": motivo_quarentena.value if motivo_quarentena else None,
        "motivo_falha": motivo_falha.value if motivo_falha else None,
    }
    gravar_satelite(session, sat_arquivo_ingestao, hk_arquivo, dados, ORIGEM)
    for campo, valor in dados.items():
        _trocar_sem_gravar(arquivo, campo, valor)
    return arquivo


def _status_pelos_arquivos(estados: set[EstadoJob]) -> StatusProcesso | None:
    if estados & ESTADOS_EM_ANDAMENTO:
        return StatusProcesso.EM_INGESTAO
    if estados & ESTADOS_PRONTOS:
        return StatusProcesso.PRONTO
    return None


def atualizar_status_processo(session: Session, hk_processo: bytes) -> StatusProcesso | None:
    """Ajusta o status do processo aos estados dos seus arquivos (A5, passo 11).

    Algum arquivo em andamento: `em_ingestao`. Nenhum em andamento e algum `concluido` ou
    `parcial`: `pronto`. Processo arquivado, em revisão ou descartado não muda.

    Args:
        session: Sessão com transação aberta.
        hk_processo: Processo.

    Returns:
        O novo status, ou None se nada mudou.
    """
    consulta = select(VisaoProcesso.status).where(VisaoProcesso.hk_processo == hk_processo)
    status = session.scalar(consulta.execution_options(populate_existing=True))
    if status is None or StatusProcesso(status) in STATUS_FIXOS:
        return None
    estados = session.scalars(
        select(VisaoArquivo.estado).where(VisaoArquivo.hk_processo == hk_processo)
    )
    novo = _status_pelos_arquivos({EstadoJob(estado) for estado in estados if estado is not None})
    if novo is None or novo.value == status:
        return None
    gravar_satelite(session, sat_processo_estado, hk_processo, {"status": novo.value}, ORIGEM)
    return novo


def alertas_arquivo(session: Session, arquivo: VisaoArquivo) -> dict[str, Any]:
    """Reúne marcas de saneamento por página e metadados suspeitos, sem expor texto (RF-ING-05)."""
    metadados = arquivo.metadados_descartados or []
    consulta = (
        select(
            VisaoPagina.numero,
            VisaoPagina.flags,
            VisaoPagina.trechos_ocultos,
            VisaoPagina.trechos_suspeitos,
        )
        .where(VisaoPagina.hk_arquivo == arquivo.hk_arquivo)
        .order_by(VisaoPagina.numero)
    )
    linhas = list(session.execute(consulta))
    resumo = resumo_saneamento(
        [
            {"numero": n, "flags": f, "ocultos": len(o or []), "suspeitos": s}
            for n, f, o, s in linhas
        ],
        metadados,
    )
    paginas = [
        {
            "numero": numero,
            "flags": sorted(chave for chave, ligada in flags.items() if ligada),
            "trechos_ocultos": [
                {k: v for k, v in trecho.items() if k != "texto"} for trecho in ocultos or []
            ],
            "trechos_suspeitos": suspeitos or [],
        }
        for numero, flags, ocultos, suspeitos in linhas
        if any((flags or {}).values())
    ]
    return {
        "arquivo_id": arquivo.id,
        "resumo": resumo,
        "metadados_suspeitos": [m for m in metadados if m.get("categorias")],
        "paginas": paginas,
    }
