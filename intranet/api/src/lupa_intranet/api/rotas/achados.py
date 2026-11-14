"""Fatos, versões, achados e anotações do processo (A11, RF-DOS-06)."""

from collections import defaultdict
from typing import Annotated, Any, Self

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from lupa_intranet.acesso.autorizacao import (
    AtorAutenticado,
    ContextoReq,
    SessaoBanco,
    exige_processo,
)
from lupa_intranet.acesso.erros import DadosInvalidosError, NaoEncontradoError
from lupa_intranet.acesso.servico import auditar
from lupa_intranet.api.middleware import auditar_rota
from lupa_intranet.auditoria.eventos import AcaoAuditoria
from lupa_pipeline.dominio import correcoes
from lupa_pipeline.dominio.chaves import chave_hash
from lupa_pipeline.dominio.enums import StatusFato
from lupa_pipeline.dominio.esquemas import Evidencia, Fato, IdPublico
from lupa_pipeline.dominio.gravacao import gravar_satelite
from lupa_pipeline.dominio.repositorios import (
    evidencias_por_id,
    listar_achados,
    listar_fatos_por_processo,
    processo_para_gravar,
)
from lupa_pipeline.dominio.tabelas import sat_achado_anotacao, sat_fato_anotacao
from lupa_pipeline.dominio.visoes import (
    VisaoAchado,
    VisaoAchadoHistorico,
    VisaoAnotacao,
    VisaoFato,
    VisaoFatoHistorico,
    VisaoPagina,
    VisaoProcesso,
)
from lupa_pipeline.ingestao.eventos.etapa import achados_do_processo
from lupa_pipeline.ingestao.repositorio_eventos import gravar_achados

router = APIRouter()
Processo = Annotated[VisaoProcesso, Depends(exige_processo)]


class CorpoCorrecao(BaseModel):
    """Valor e localização da prova escolhida na correção humana."""

    model_config = ConfigDict(extra="forbid")
    status: StatusFato
    valor: Any = None
    pagina_id: IdPublico | None = None
    inicio: int | None = Field(None, ge=0)
    fim: int | None = Field(None, gt=0)
    trecho: str | None = Field(None, min_length=1)

    @model_validator(mode="after")
    def _coerente(self) -> Self:
        campos = (self.valor, self.pagina_id, self.inicio, self.fim, self.trecho)
        if self.status == StatusFato.CORRIGIDO and all(c is not None for c in campos):
            if self.inicio is not None and self.fim is not None and self.fim > self.inicio:
                return self
        if self.status == StatusFato.CONFIRMADO and all(c is None for c in campos):
            return self
        raise ValueError(
            "informe valor, página, início, fim e trecho ao corrigir, ou apenas confirme"
        )


class CorpoAnotacao(BaseModel):
    """Nota sobre exatamente um alvo do processo."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    achado_id: IdPublico | None = None
    fato_id: IdPublico | None = None
    texto: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def _um_alvo(self) -> Self:
        if (self.achado_id is None) == (self.fato_id is None):
            raise ValueError("informe achado_id ou fato_id")
        return self


@router.get("/processos/{processo_id}/achados")
@auditar_rota(AcaoAuditoria.PROCESSO_ABERTO, conteudo=True)
def obter_achados(processo: Processo, sessao: SessaoBanco) -> dict[str, Any]:
    """Resultados correntes por validação e recorrente."""
    return {
        "processo_id": processo.id,
        "status": processo.status,
        "achados": [
            a.model_dump(mode="json") for a in listar_achados(sessao, processo.hk_processo)
        ],
    }


@router.get("/processos/{processo_id}/achados/historico")
@auditar_rota(AcaoAuditoria.PROCESSO_ABERTO, conteudo=True)
def historico_achados(processo: Processo, sessao: SessaoBanco) -> dict[str, Any]:
    """Resultados em ordem de gravação, com a versão corrente de cada achado marcada."""
    vigentes = {a.id: a.criado_em for a in listar_achados(sessao, processo.hk_processo)}
    linhas = sessao.scalars(
        select(VisaoAchadoHistorico)
        .where(VisaoAchadoHistorico.hk_processo == processo.hk_processo)
        .order_by(VisaoAchadoHistorico.criado_em, VisaoAchadoHistorico.id)
    )
    return {
        "processo_id": processo.id,
        "achados": [
            {
                "id": a.id,
                "processo_id": a.processo_id,
                "sujeito": a.sujeito,
                "validacao": a.validacao,
                "resultado": a.resultado,
                "versao_catalogo": a.versao_catalogo,
                "valores": a.valores,
                "fatos_usados": [hk.hex() for hk in a.fatos_usados],
                "explicacao": a.explicacao,
                "criado_em": a.criado_em,
                "vigente": vigentes.get(a.id) == a.criado_em,
            }
            for a in linhas
        ],
    }


def _anotacao(a: VisaoAnotacao) -> dict[str, Any]:
    return {
        "id": chave_hash([a.alvo_tipo, a.alvo_id, a.criada_em.isoformat()]).hex(),
        "fato_id": a.alvo_id if a.alvo_tipo == "fato" else None,
        "achado_id": a.alvo_id if a.alvo_tipo == "achado" else None,
        "usuario_id": a.usuario_id,
        "autor": a.nome_usuario,
        "texto": a.texto,
        "criado_em": a.criada_em,
    }


def _com_paginas(
    session: Session, processo: VisaoProcesso, fatos: list[tuple[Fato, bool]]
) -> list[dict[str, Any]]:
    numeros = {e.pagina_id for fato, _ in fatos for e in fato.evidencias}
    paginas = {
        p.id: (p.arquivo_id, p.numero)
        for p in session.execute(
            select(VisaoPagina.id, VisaoPagina.arquivo_id, VisaoPagina.numero).where(
                VisaoPagina.hk_processo == processo.hk_processo, VisaoPagina.id.in_(numeros)
            )
        )
    }
    notas: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in session.scalars(
        select(VisaoAnotacao)
        .where(VisaoAnotacao.hk_processo == processo.hk_processo, VisaoAnotacao.alvo_tipo == "fato")
        .order_by(VisaoAnotacao.criada_em)
    ):
        notas[a.alvo_id].append(_anotacao(a))
    return [
        f.model_dump(mode="json", exclude={"evidencias"})
        | {
            "vigente": vigente,
            "anotacoes": notas[f.id],
            "evidencias": [
                e.model_dump(mode="json")
                | {"arquivo_id": paginas[e.pagina_id][0], "pagina": paginas[e.pagina_id][1]}
                for e in f.evidencias
            ],
        }
        for f, vigente in fatos
    ]


@router.get("/processos/{processo_id}/fatos")
@auditar_rota(AcaoAuditoria.PROCESSO_ABERTO, conteudo=True)
def fatos_correntes(processo: Processo, sessao: SessaoBanco) -> dict[str, Any]:
    """Fatos com evidências verificáveis e notas humanas."""
    fatos = listar_fatos_por_processo(sessao, processo.hk_processo)
    return {
        "processo_id": processo.id,
        "fatos": _com_paginas(sessao, processo, [(f, True) for f in fatos]),
    }


@router.get("/processos/{processo_id}/fatos/historico")
@auditar_rota(AcaoAuditoria.PROCESSO_ABERTO, conteudo=True)
def historico_fatos(processo: Processo, sessao: SessaoBanco) -> dict[str, Any]:
    """Versões dos valores com as evidências que os sustentavam no instante da gravação."""
    linhas = sessao.execute(
        select(VisaoFato, VisaoFatoHistorico)
        .join(VisaoFatoHistorico, VisaoFato.hk_fato == VisaoFatoHistorico.hk_fato)
        .where(VisaoFato.hk_processo == processo.hk_processo)
        .order_by(VisaoFatoHistorico.load_dts, VisaoFato.id)
    ).all()
    evidencias = evidencias_por_id(
        sessao, {hk for f, v in linhas for hk in (v.evidencias_vigentes or [f.hk_evidencia_origem])}
    )
    fatos = []
    for f, v in linhas:
        fato = Fato.model_validate(
            {
                "id": f.id,
                "processo_id": f.processo_id,
                "tipo": f.tipo,
                "sujeito": f.sujeito,
                "valor": v.valor,
                "extraido_por": v.extraido_por,
                "versao_extrator": v.versao_extrator,
                "confianca": v.confianca,
                "status": v.status,
                "criado_em": v.load_dts,
                "evidencias": [
                    evidencias[hk] for hk in (v.evidencias_vigentes or [f.hk_evidencia_origem])
                ],
            }
        )
        fatos.append((fato, f.vigente and v.load_dts == f.atualizado_em))
    return {"processo_id": processo.id, "fatos": _com_paginas(sessao, processo, fatos)}


@router.post("/processos/{processo_id}/fatos/{fato_id}/corrigir", status_code=201)
def corrigir_fato(
    processo: Processo,
    fato_id: str,
    corpo: CorpoCorrecao,
    ator: AtorAutenticado,
    sessao: SessaoBanco,
    ctx: ContextoReq,
) -> dict[str, Any]:
    """Confere o trecho e reexecuta as regras sobre a versão revista."""
    original = correcoes.obter_fato(sessao, processo.hk_processo, fato_id)
    if original is None:
        raise NaoEncontradoError("fato não encontrado")
    evidencia = None
    if corpo.pagina_id and corpo.inicio is not None and corpo.fim and corpo.trecho:
        evidencia = Evidencia(
            id=chave_hash([corpo.pagina_id, corpo.inicio, corpo.fim]).hex(),
            pagina_id=corpo.pagina_id,
            inicio=corpo.inicio,
            fim=corpo.fim,
            trecho=corpo.trecho,
        )
    try:
        novo = correcoes.corrigir_fato(
            sessao, original, corpo.status, ator.hk_usuario, corpo.valor, evidencia
        )
    except ValueError as erro:
        raise DadosInvalidosError(str(erro)) from None
    auditar(
        sessao,
        ctx,
        AcaoAuditoria.FATO_CORRIGIDO,
        hk_usuario=ator.hk_usuario,
        hk_processo=processo.hk_processo,
        objeto_tipo="fato",
        objeto_id=novo.id,
    )
    achados = achados_do_processo(
        sessao, processo.hk_processo, processo.classe or "", ctx.agora.date()
    )
    novos = gravar_achados(sessao, processo.hk_processo, achados)
    auditar(
        sessao,
        ctx,
        AcaoAuditoria.VALIDACAO_EXECUTADA,
        hk_usuario=ator.hk_usuario,
        hk_processo=processo.hk_processo,
        objeto_tipo="processo",
        objeto_id=processo.id,
    )
    return {
        "fato": novo.model_dump(mode="json"),
        "achados_gravados": novos,
        "achados": [
            a.model_dump(mode="json") for a in listar_achados(sessao, processo.hk_processo)
        ],
    }


@router.get("/processos/{processo_id}/anotacoes")
@auditar_rota(AcaoAuditoria.PROCESSO_ABERTO, conteudo=True)
def listar_anotacoes(processo: Processo, sessao: SessaoBanco) -> dict[str, Any]:
    """Lista as notas do processo em ordem de criação."""
    linhas = sessao.scalars(
        select(VisaoAnotacao)
        .where(VisaoAnotacao.hk_processo == processo.hk_processo)
        .order_by(VisaoAnotacao.criada_em)
    )
    return {"processo_id": processo.id, "anotacoes": [_anotacao(a) for a in linhas]}


@router.post("/processos/{processo_id}/anotacoes", status_code=201)
def anotar(
    processo: Processo,
    corpo: CorpoAnotacao,
    ator: AtorAutenticado,
    sessao: SessaoBanco,
    ctx: ContextoReq,
) -> dict[str, Any]:
    """Grava uma nota cifrada sobre um fato ou achado do processo."""
    processo_para_gravar(sessao, processo.hk_processo)
    if corpo.fato_id:
        hk = sessao.scalar(
            select(VisaoFato.hk_fato).where(
                VisaoFato.hk_processo == processo.hk_processo, VisaoFato.id == corpo.fato_id
            )
        )
        tabela = sat_fato_anotacao
        tipo = "fato"
    else:
        hk = sessao.scalar(
            select(VisaoAchado.hk_achado).where(
                VisaoAchado.hk_processo == processo.hk_processo, VisaoAchado.id == corpo.achado_id
            )
        )
        tabela = sat_achado_anotacao
        tipo = "achado"
    if hk is None:
        raise NaoEncontradoError("achado ou fato não encontrado")
    gravar_satelite(
        sessao,
        tabela,
        hk,
        {"texto": corpo.texto, "hk_usuario": ator.hk_usuario},
        "intranet.anotacao",
    )
    nota = sessao.scalars(
        select(VisaoAnotacao)
        .where(VisaoAnotacao.alvo_tipo == tipo, VisaoAnotacao.hk_alvo == hk)
        .order_by(VisaoAnotacao.criada_em.desc())
        .limit(1)
    ).one()
    resposta = _anotacao(nota)
    auditar(
        sessao,
        ctx,
        AcaoAuditoria.ANOTACAO,
        hk_usuario=ator.hk_usuario,
        hk_processo=processo.hk_processo,
        objeto_tipo="anotacao",
        objeto_id=resposta["id"],
    )
    return resposta
