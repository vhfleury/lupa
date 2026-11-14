"""Persistência dos fatos com evidência e dos resultados do catálogo (A5, A6 e A11)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.enums import StatusFato
from lupa_pipeline.dominio.esquemas import Achado, Evidencia, Fato
from lupa_pipeline.dominio.gravacao import gravar_hub, gravar_link, gravar_satelite, travar_processo
from lupa_pipeline.dominio.tabelas import (
    hub_achado,
    hub_fato,
    link_achado_fato,
    link_fato_evidencia,
    link_processo_achado,
    link_processo_fato,
    sat_achado_resultado,
    sat_fato_evidencia_vigencia,
    sat_fato_valor,
)
from lupa_pipeline.dominio.visoes import (
    VisaoAchado,
    VisaoEvidencia,
    VisaoFato,
    VisaoPagina,
    VisaoProcesso,
    atual,
)
from lupa_pipeline.ingestao.eventos.modelo import PaginaTexto, evidencia_de
from lupa_pipeline.ingestao.repositorio_pecas import gravar_evidencia
from lupa_pipeline.validacoes.catalogo import validacoes_de
from lupa_pipeline.validacoes.modelo import ModeloProcesso

ORIGEM = "pipeline.eventos"


class ProcessoNaoEncontradoError(ValueError):
    """Processo inexistente ou descartado."""


def processo_para_gravar(session: Session, hk: bytes) -> VisaoProcesso:
    """Relê o processo sob a mesma trava usada pelo descarte."""
    processo = travar_processo(session, hk)
    if processo is None or processo.status == "descartado":
        raise ProcessoNaoEncontradoError("processo indisponível")
    return processo


def evidencia_da_pagina(session: Session, processo_id: bytes, evidencia: Evidencia) -> bytes:
    """Resolve a seleção na página do processo e grava offsets e trecho do original."""
    pagina = session.scalar(
        select(VisaoPagina).where(
            VisaoPagina.hk_processo == processo_id, VisaoPagina.id == evidencia.pagina_id
        )
    )
    if pagina is None:
        raise ValueError("página não pertence ao processo")
    texto = pagina.texto or ""
    original = evidencia
    if evidencia.fim > len(texto) or texto[evidencia.inicio : evidencia.fim] != evidencia.trecho:
        fonte = PaginaTexto(pagina.id, pagina.numero, texto, pagina.texto_normalizado or "")
        mapeada = evidencia_de(fonte, evidencia.inicio, evidencia.fim, evidencia.trecho)
        if mapeada is None:
            raise ValueError("o trecho não confere com o texto da página")
        original = mapeada
    dados = {
        "numero_cnj": pagina.numero_cnj,
        "sha256": pagina.sha256,
        "numero": pagina.numero,
        "hk_pagina": pagina.hk_pagina,
        "texto": texto,
    }
    return gravar_evidencia(
        session, dados, original.inicio, original.fim, original.trecho, evidencia.bbox
    )


def vincular_evidencia(session: Session, fato: bytes, evidencia: bytes, vigente: bool) -> None:
    """Registra a vigência do vínculo, preservando todas as versões anteriores."""
    ligacao = gravar_link(
        session, link_fato_evidencia, {"hk_fato": fato, "hk_evidencia": evidencia}, ORIGEM
    )
    gravar_satelite(session, sat_fato_evidencia_vigencia, ligacao, {"vigente": vigente}, ORIGEM)


def gravar_valor(session: Session, hk: bytes, fato: Fato, autor: bytes | None) -> bool:
    """Grava o valor e a atribuição de autoria de uma versão do fato."""
    campos = fato.model_dump(
        include={"valor", "extraido_por", "versao_extrator", "confianca", "status"}, mode="json"
    )
    return gravar_satelite(session, sat_fato_valor, hk, campos | {"hk_usuario": autor}, ORIGEM)


def salvar_fato(session: Session, fato: Fato) -> bytes:
    """Insere o fato automático e seus vínculos sem substituir uma revisão humana."""
    processo = processo_para_gravar(session, bytes.fromhex(fato.processo_id))
    evidencias = [evidencia_da_pagina(session, processo.hk_processo, e) for e in fato.evidencias]
    chave = {
        "numero_cnj": processo.numero_cnj,
        "tipo": fato.tipo.value,
        "sujeito": fato.sujeito,
        "hk_evidencia_origem": evidencias[0],
    }
    hk = gravar_hub(session, hub_fato, chave, ORIGEM)
    gravar_link(
        session, link_processo_fato, {"hk_processo": processo.hk_processo, "hk_fato": hk}, ORIGEM
    )
    anterior = session.get(VisaoFato, hk, populate_existing=True)
    if anterior and anterior.status in (StatusFato.CONFIRMADO, StatusFato.CORRIGIDO):
        return hk
    for evidencia in evidencias:
        vincular_evidencia(session, hk, evidencia, True)
    gravar_valor(session, hk, fato, None)
    return hk


def evidencias_por_id(session: Session, ids: set[bytes]) -> dict[bytes, Evidencia]:
    """Carrega os trechos das evidências de uma consulta em lote."""
    if not ids:
        return {}
    return {
        e.hk_evidencia: Evidencia.model_validate(e, from_attributes=True)
        for e in session.scalars(
            atual(select(VisaoEvidencia).where(VisaoEvidencia.hk_evidencia.in_(ids)))
        )
    }


def listar_fatos_por_processo(session: Session, processo_id: bytes) -> list[Fato]:
    """Lista fatos vigentes com todas as evidências correntes do próprio processo."""
    linhas = list(
        session.scalars(
            atual(
                select(VisaoFato)
                .where(VisaoFato.hk_processo == processo_id, VisaoFato.vigente.is_(True))
                .order_by(VisaoFato.hk_fato)
            )
        )
    )
    por_id = evidencias_por_id(session, {hk for f in linhas for hk in f.evidencias_vigentes})
    return [
        Fato.model_validate(
            {
                "id": f.id,
                "processo_id": f.processo_id,
                "tipo": f.tipo,
                "sujeito": f.sujeito,
                "valor": f.valor,
                "extraido_por": f.extraido_por,
                "versao_extrator": f.versao_extrator,
                "confianca": f.confianca,
                "status": f.status,
                "criado_em": f.atualizado_em,
                "evidencias": [por_id[hk] for hk in f.evidencias_vigentes],
            }
        )
        for f in linhas
    ]


def salvar_achado(session: Session, achado: Achado) -> bool:
    """Registra o resultado sob a chave estável da validação e do recorrente."""
    processo = processo_para_gravar(session, bytes.fromhex(achado.processo_id))
    chave = {
        "numero_cnj": processo.numero_cnj,
        "validacao": achado.validacao,
        "sujeito": achado.sujeito,
    }
    fatos = [bytes.fromhex(i) for i in achado.fatos_usados]
    if fatos:
        do_processo = set(
            session.scalars(
                select(VisaoFato.hk_fato).where(
                    VisaoFato.hk_processo == processo.hk_processo, VisaoFato.hk_fato.in_(fatos)
                )
            )
        )
        if do_processo != set(fatos):
            raise ValueError("fato não pertence ao processo")
    hk = gravar_hub(session, hub_achado, chave, ORIGEM)
    gravar_link(
        session,
        link_processo_achado,
        {"hk_processo": processo.hk_processo, "hk_achado": hk},
        ORIGEM,
    )
    for fato in fatos:
        gravar_link(session, link_achado_fato, {"hk_achado": hk, "hk_fato": fato}, ORIGEM)
    valores: dict[str, Any] = achado.model_dump(
        include={"versao_catalogo", "resultado", "valores", "explicacao"}, mode="json"
    )
    return gravar_satelite(
        session, sat_achado_resultado, hk, valores | {"fatos_usados": fatos}, ORIGEM
    )


def listar_achados(session: Session, processo_id: bytes) -> list[Achado]:
    """Lê os resultados correntes e as referências aos fatos que a regra usou."""
    processo = session.get_one(VisaoProcesso, processo_id)
    classe = processo.classe or ""
    modelo = ModeloProcesso(listar_fatos_por_processo(session, processo_id))
    sujeitos = [m.sujeito for m in modelo.recorrentes(classe)]
    regras = [r.nome for r in validacoes_de(classe)]
    consulta = (
        select(VisaoAchado)
        .where(VisaoAchado.validacao.in_(regras), VisaoAchado.sujeito.in_(sujeitos))
        .where(VisaoAchado.hk_processo == processo_id, VisaoAchado.resultado.is_not(None))
        .order_by(VisaoAchado.validacao, VisaoAchado.sujeito)
    )
    return [
        Achado.model_validate(
            {
                "id": a.id,
                "processo_id": a.processo_id,
                "sujeito": a.sujeito,
                "validacao": a.validacao,
                "versao_catalogo": a.versao_catalogo,
                "resultado": a.resultado,
                "fatos_usados": [hk.hex() for hk in a.fatos_usados or ()],
                "valores": a.valores,
                "explicacao": a.explicacao,
                "criado_em": a.criado_em,
            }
        )
        for a in session.scalars(atual(consulta))
    ]
