"""Rotas de processo: cadastro com classe, lista, leitura, arquivos e responsáveis.

`GET /processos` lista todos os processos, igual para qualquer usuário (RF-PRO-02), com classe,
resumo da ingestão (de `v_arquivo`) e responsáveis vigentes (de `v_responsavel`); é auditada
como `busca`. `POST /processos` grava `hub_processo`, `sat_processo_dados`, `sat_processo_estado`
e a DEK (RF-PRO-01); o assessor que cadastra vira o responsável inicial. Número repetido dá 409
com o `processo_id` do existente. `GET /processos/{id}` e as rotas abaixo dele usam
`exige_processo`: responsável não restringe acesso (RF-PRO-03) e não há sigilo (RF-PRO-04).
Responsáveis mudam por linha nova de `sat_processo_responsavel_vigencia`, só pelo desembargador.
"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from lupa_intranet.acesso.autorizacao import (
    AtorAutenticado,
    ContextoReq,
    SessaoBanco,
    exige_papel,
    exige_processo,
)
from lupa_intranet.acesso.erros import ConflitoError, DadosInvalidosError, PermissaoNegadaError
from lupa_intranet.acesso.papeis import Permissao, tem_permissao
from lupa_intranet.acesso.servico import Ator, auditar
from lupa_intranet.api.middleware import auditar_rota
from lupa_intranet.auditoria.eventos import AcaoAuditoria
from lupa_pipeline.dominio.cnj import (
    NumeroCnjInvalidoError,
    formatar_numero_cnj,
    validar_numero_cnj,
)
from lupa_pipeline.dominio.enums import ClasseProcessual, EstadoJob, PapelUsuario, StatusProcesso
from lupa_pipeline.dominio.gravacao import chave_do_hub, gravar_hub, gravar_link, gravar_satelite
from lupa_pipeline.dominio.tabelas import (
    hub_processo,
    link_processo_responsavel,
    sat_processo_dados,
    sat_processo_estado,
    sat_processo_responsavel_vigencia,
)
from lupa_pipeline.dominio.visoes import (
    VisaoArquivo,
    VisaoProcesso,
    VisaoResponsavel,
    VisaoUsuario,
    atual,
)
from lupa_pipeline.seguranca.chaves import criar_chave_processo
from lupa_pipeline.seguranca.contexto import obter_cofre

router = APIRouter()

Processo = Annotated[VisaoProcesso, Depends(exige_processo)]
Leitor = Annotated[Ator, Depends(exige_papel(Permissao.VER_PROCESSO))]
Cadastrador = Annotated[Ator, Depends(exige_papel(Permissao.SUBIR_PROCESSO))]

ORIGEM = "intranet.processos"
ESTADOS_FINAIS = frozenset({EstadoJob.CONCLUIDO, EstadoJob.QUARENTENA, EstadoJob.FALHO})
ESTADOS_COM_PENDENCIA = frozenset({EstadoJob.PARCIAL, EstadoJob.EM_REVISAO})
MENSAGEM_DUPLICADO = "número CNJ já cadastrado"
TRAVA_RESPONSAVEIS = 0x4C555041


class CorpoProcesso(BaseModel):
    """Dados do processo novo: número CNJ e classe da seção 3.1."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    numero_cnj: str = Field(min_length=25, max_length=25)
    classe: ClasseProcessual

    @field_validator("numero_cnj")
    @classmethod
    def _cnj_valido(cls, valor: str) -> str:
        try:
            return validar_numero_cnj(valor)
        except NumeroCnjInvalidoError as erro:
            raise ValueError(str(erro)) from None


class CorpoResponsaveis(BaseModel):
    """Conjunto desejado e conjunto conhecido, para evitar sobrescritas concorrentes."""

    model_config = ConfigDict(extra="forbid")

    usuarios: list[str] = Field(min_length=1, max_length=100)
    anteriores: list[str] = Field(max_length=100)


def _serializar(processo: VisaoProcesso) -> dict[str, Any]:
    return {
        "id": processo.id,
        "numero_cnj": formatar_numero_cnj(processo.numero_cnj),
        "classe": processo.classe,
        "status": processo.status,
        "em_revisao": processo.em_revisao,
        "criador_id": processo.criador_id,
        "criado_em": processo.criado_em,
    }


def resumir_ingestao(estados: list[str]) -> str:
    """Situação agregada da ingestão a partir dos estados dos arquivos do processo.

    Args:
        estados: Estado corrente de cada arquivo.

    Returns:
        `sem_arquivos`, `processando` (algum arquivo não final), `quarentena` (todos em
        quarentena), `falho`, `pendencias` (parcial ou em revisão) ou `concluido`.
    """
    if not estados:
        return "sem_arquivos"
    conjunto = {EstadoJob(e) for e in estados}
    if conjunto - ESTADOS_FINAIS - ESTADOS_COM_PENDENCIA:
        return "processando"
    if conjunto == {EstadoJob.QUARENTENA}:
        return "quarentena"
    if EstadoJob.FALHO in conjunto:
        return "falho"
    if conjunto & ESTADOS_COM_PENDENCIA:
        return "pendencias"
    return "concluido"


def _responsaveis_vigentes(
    sessao: Session, processo_ids: list[str]
) -> dict[str, list[dict[str, Any]]]:
    consulta = (
        select(VisaoResponsavel.processo_id, VisaoUsuario)
        .join(VisaoUsuario, VisaoUsuario.hk_usuario == VisaoResponsavel.hk_usuario)
        .where(
            VisaoResponsavel.processo_id.in_(processo_ids),
            VisaoResponsavel.vigente.is_(True),
        )
        .order_by(VisaoUsuario.nome_usuario)
        .execution_options(populate_existing=True)
    )
    linhas = sessao.execute(consulta)
    resultado: dict[str, list[dict[str, Any]]] = {}
    for processo_id, usuario in linhas:
        resultado.setdefault(processo_id, []).append(_usuario(usuario))
    return resultado


def _usuario(usuario: VisaoUsuario) -> dict[str, Any]:
    return {"id": usuario.id, "nome_usuario": usuario.nome_usuario, "ativo": usuario.ativo}


def _ingestao(sessao: Session, processo_ids: list[str]) -> dict[str, dict[str, Any]]:
    linhas = sessao.execute(
        select(VisaoArquivo.processo_id, VisaoArquivo.estado, VisaoArquivo.criado_em).where(
            VisaoArquivo.processo_id.in_(processo_ids)
        )
    )
    por_processo: dict[str, list[tuple[str | None, datetime]]] = {}
    for processo_id, estado, criado_em in linhas:
        por_processo.setdefault(processo_id, []).append((estado, criado_em))
    return {processo_id: _resumo(arquivos) for processo_id, arquivos in por_processo.items()}


def _resumo(arquivos: list[tuple[str | None, datetime]]) -> dict[str, Any]:
    estados = [estado for estado, _ in arquivos if estado]
    por_estado: dict[str, int] = {}
    for estado in estados:
        por_estado[estado] = por_estado.get(estado, 0) + 1
    return {
        "situacao": resumir_ingestao(estados),
        "por_estado": por_estado,
        "ultimo_envio": max((criado_em for _, criado_em in arquivos), default=None),
    }


def _ids_meus(ator: Ator) -> Select[tuple[str]]:
    return select(VisaoResponsavel.processo_id).where(
        VisaoResponsavel.hk_usuario == ator.hk_usuario, VisaoResponsavel.vigente.is_(True)
    )


@router.get("/processos")
@auditar_rota(AcaoAuditoria.BUSCA, conteudo=False)
def listar_processos(ator: Leitor, sessao: SessaoBanco, meus: bool = False) -> list[dict[str, Any]]:
    """Todos os processos, mais recentes primeiro, com ingestão e responsáveis (RF-PRO-02).

    Args:
        ator: Ator com permissão de ver processos.
        sessao: Sessão da requisição.
        meus: Restringe aos processos de que o usuário é responsável vigente (RF-PRO-03).

    Returns:
        Processos com `responsaveis` e `ingestao: {situacao, por_estado, ultimo_envio}`.
    """
    consulta = select(VisaoProcesso).order_by(VisaoProcesso.criado_em.desc(), VisaoProcesso.id)
    if meus:
        consulta = consulta.where(VisaoProcesso.id.in_(_ids_meus(ator)))
    processos = list(sessao.scalars(consulta))
    ids = [p.id for p in processos]
    responsaveis = _responsaveis_vigentes(sessao, ids)
    ingestao = _ingestao(sessao, ids)
    return [
        _serializar(processo)
        | {
            "responsaveis": responsaveis.get(processo.id, []),
            "ingestao": ingestao.get(processo.id) or _resumo([]),
        }
        for processo in processos
    ]


def _ligar_responsavel(
    sessao: Session, hk_processo: bytes, hk_usuario: bytes, vigente: bool
) -> None:
    ligacao = {"hk_processo": hk_processo, "hk_usuario": hk_usuario}
    hk_link = gravar_link(sessao, link_processo_responsavel, ligacao, ORIGEM)
    vigencia = {"vigente": vigente}
    gravar_satelite(sessao, sat_processo_responsavel_vigencia, hk_link, vigencia, ORIGEM)


def gravar_processo(
    sessao: Session, corpo: CorpoProcesso, ator: Ator, *, origem: str = ORIGEM
) -> bytes:
    """Cadastra o processo, abre a DEK e atribui o assessor que o cadastrou."""
    hk = gravar_hub(sessao, hub_processo, {"numero_cnj": corpo.numero_cnj}, origem)
    dados = {"classe": corpo.classe.value, "hk_usuario": ator.hk_usuario}
    gravar_satelite(sessao, sat_processo_dados, hk, dados, origem)
    estado = {"status": StatusProcesso.CRIADO.value}
    gravar_satelite(sessao, sat_processo_estado, hk, estado, origem)
    criar_chave_processo(sessao, obter_cofre(), hk, origem)
    if ator.papel is PapelUsuario.ASSESSOR:
        _ligar_responsavel(sessao, hk, ator.hk_usuario, vigente=True)
    return hk


def _consulta_processo(hk_processo: bytes) -> Select[tuple[VisaoProcesso]]:
    return atual(select(VisaoProcesso).where(VisaoProcesso.hk_processo == hk_processo))


@router.post("/processos", status_code=201, response_model=None)
def criar_processo(
    corpo: CorpoProcesso, ator: Cadastrador, sessao: SessaoBanco, ctx: ContextoReq
) -> dict[str, Any] | JSONResponse:
    """Cadastra o processo com número CNJ e classe (RF-PRO-01).

    Args:
        corpo: Número CNJ (dígito verificador conferido) e classe.
        ator: Quem cadastra.
        sessao: Sessão da requisição.
        ctx: Contexto para a auditoria.

    Returns:
        Processo criado, ou 409 com o `processo_id` do existente.
    """
    hk = chave_do_hub(hub_processo, {"numero_cnj": corpo.numero_cnj})
    if sessao.scalars(_consulta_processo(hk)).one_or_none() is not None:
        return JSONResponse(
            status_code=409, content={"detail": MENSAGEM_DUPLICADO, "processo_id": hk.hex()}
        )
    gravar_processo(sessao, corpo, ator)
    processo = sessao.scalars(_consulta_processo(hk)).one()
    auditar(
        sessao,
        ctx,
        AcaoAuditoria.PROCESSO_CRIADO,
        hk_usuario=ator.hk_usuario,
        hk_processo=hk,
        objeto_tipo="processo",
        objeto_id=hk.hex(),
    )
    return _serializar(processo)


@router.get("/processos/{processo_id}")
@auditar_rota(AcaoAuditoria.PROCESSO_ABERTO, conteudo=True)
def abrir_processo(processo: Processo) -> dict[str, Any]:
    """Devolve os dados do processo; gera `processo_aberto`.

    Args:
        processo: Processo já carregado por `exige_processo`.

    Returns:
        Dados básicos do processo.
    """
    return _serializar(processo)


@router.get("/processos/{processo_id}/arquivos")
@auditar_rota(AcaoAuditoria.PROCESSO_ABERTO, conteudo=False)
def listar_arquivos(processo: Processo, sessao: SessaoBanco) -> dict[str, Any]:
    """Arquivos do processo com o estado corrente da ingestão (RF-ING-06).

    Args:
        processo: Processo carregado.
        sessao: Sessão da requisição.

    Returns:
        `{processo_id, status, situacao, arquivos: [...]}`, mais recentes primeiro.
    """
    linhas = sessao.scalars(
        select(VisaoArquivo)
        .where(VisaoArquivo.hk_processo == processo.hk_processo)
        .order_by(VisaoArquivo.criado_em.desc(), VisaoArquivo.id)
    )
    arquivos = [
        {
            "arquivo_id": arquivo.id,
            "nome": arquivo.nome_original,
            "mime": arquivo.mime,
            "tamanho_bytes": arquivo.tamanho_bytes,
            "enviado_em": arquivo.criado_em,
            "estado": arquivo.estado,
            "motivo_quarentena": arquivo.motivo_quarentena,
            "motivo_falha": arquivo.motivo_falha,
            "total_paginas": arquivo.total_paginas,
            "relatorio": arquivo.relatorio,
            "estado_em": arquivo.estado_em,
        }
        for arquivo in linhas
    ]
    return {
        "processo_id": processo.id,
        "status": processo.status,
        "situacao": resumir_ingestao([a["estado"] for a in arquivos if a["estado"]]),
        "arquivos": arquivos,
    }


def _vigentes(sessao: Session, processo: VisaoProcesso) -> set[str]:
    consulta = select(VisaoResponsavel.usuario_id).where(
        VisaoResponsavel.hk_processo == processo.hk_processo, VisaoResponsavel.vigente.is_(True)
    )
    return set(sessao.scalars(atual(consulta)))


def _assessores_ativos(sessao: Session, ids: set[str] | None = None) -> list[VisaoUsuario]:
    consulta = select(VisaoUsuario).where(
        VisaoUsuario.papel == PapelUsuario.ASSESSOR.value, VisaoUsuario.ativo.is_(True)
    )
    if ids is not None:
        consulta = consulta.where(VisaoUsuario.id.in_(ids))
    return list(sessao.scalars(atual(consulta.order_by(VisaoUsuario.nome_usuario))))


def _listar_responsaveis(sessao: Session, processo: VisaoProcesso) -> list[dict[str, Any]]:
    return _responsaveis_vigentes(sessao, [processo.id]).get(processo.id, [])


@router.get("/processos/{processo_id}/responsaveis")
@auditar_rota(AcaoAuditoria.PROCESSO_ABERTO, conteudo=False)
def listar_responsaveis(
    processo: Processo, ator: AtorAutenticado, sessao: SessaoBanco
) -> dict[str, Any]:
    """Responsáveis vigentes; o desembargador também recebe os assessores ativos elegíveis.

    Args:
        processo: Processo carregado.
        ator: Ator autenticado.
        sessao: Sessão da requisição.

    Returns:
        `{responsaveis, disponiveis, pode_gerir}`.
    """
    pode_gerir = tem_permissao(ator.papel, Permissao.GERIR_ASSESSOR)
    disponiveis = [_usuario(u) for u in _assessores_ativos(sessao)] if pode_gerir else []
    return {
        "responsaveis": _listar_responsaveis(sessao, processo),
        "disponiveis": disponiveis,
        "pode_gerir": pode_gerir,
    }


def _travar_responsaveis(sessao: Session, processo: VisaoProcesso) -> None:
    chave = int.from_bytes(processo.hk_processo[:4], "big", signed=True)
    sessao.execute(select(func.pg_advisory_xact_lock(TRAVA_RESPONSAVEIS, chave)))


def _conferir_novos(sessao: Session, corpo: CorpoResponsaveis) -> dict[str, VisaoUsuario]:
    novos = {usuario_id.lower() for usuario_id in corpo.usuarios}
    if len(novos) != len(corpo.usuarios):
        raise DadosInvalidosError("não repita responsáveis")
    validos = {u.id: u for u in _assessores_ativos(sessao, novos)}
    if set(validos) != novos:
        raise DadosInvalidosError("selecione apenas assessores ativos")
    return validos


@router.post("/processos/{processo_id}/responsaveis")
def definir_responsaveis(
    corpo: CorpoResponsaveis,
    processo: Processo,
    ator: AtorAutenticado,
    sessao: SessaoBanco,
    ctx: ContextoReq,
) -> dict[str, Any]:
    """Adiciona ou transfere a responsabilidade a assessores ativos (RF-PRO-03).

    Args:
        corpo: Conjunto desejado e o conjunto que o cliente conhecia.
        processo: Processo carregado.
        ator: Desembargador.
        sessao: Sessão da requisição.
        ctx: Contexto para a auditoria.

    Returns:
        `{responsaveis}` depois da mudança.

    Raises:
        PermissaoNegadaError: Papel sem `gerir_assessor`.
        ConflitoError: Os responsáveis mudaram desde a leitura do cliente.
        DadosInvalidosError: Usuário repetido, inexistente, inativo ou que não é assessor.
    """
    if not tem_permissao(ator.papel, Permissao.GERIR_ASSESSOR):
        raise PermissaoNegadaError("somente o desembargador pode alterar responsáveis")
    _travar_responsaveis(sessao, processo)
    atuais = _vigentes(sessao, processo)
    if atuais != {usuario_id.lower() for usuario_id in corpo.anteriores}:
        raise ConflitoError("Os responsáveis mudaram. Recarregue a lista antes de salvar.")
    novos = _conferir_novos(sessao, corpo)
    mudancas = (
        (set(novos) - atuais, True, AcaoAuditoria.RESPONSAVEL_ADICIONADO),
        (atuais - set(novos), False, AcaoAuditoria.RESPONSAVEL_REMOVIDO),
    )
    for ids, vigente, acao in mudancas:
        for usuario_id in sorted(ids):
            _ligar_responsavel(sessao, processo.hk_processo, bytes.fromhex(usuario_id), vigente)
            auditar(
                sessao,
                ctx,
                acao,
                hk_usuario=ator.hk_usuario,
                hk_processo=processo.hk_processo,
                objeto_tipo="usuario",
                objeto_id=usuario_id,
            )
    return {"responsaveis": _listar_responsaveis(sessao, processo)}
