"""Extração das partes e dos fatos e execução do catálogo do processo (A5 e A6)."""

from collections import Counter, defaultdict
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from lupa_pipeline.dominio.chaves import hmac_processo
from lupa_pipeline.dominio.enums import StatusFato, TipoPeca
from lupa_pipeline.dominio.esquemas import Achado
from lupa_pipeline.dominio.gravacao import chave_do_hub, gravar_hub, gravar_link, gravar_satelite
from lupa_pipeline.dominio.repositorios import (
    evidencia_da_pagina,
    listar_fatos_por_processo,
    processo_para_gravar,
    salvar_fato,
    vincular_evidencia,
)
from lupa_pipeline.dominio.tabelas import (
    hub_achado,
    hub_parte,
    link_processo_parte,
    sat_parte_identidade,
)
from lupa_pipeline.dominio.visoes import VisaoPagina, VisaoPeca, VisaoProcesso, atual
from lupa_pipeline.ingestao.eventos.fatos import ORIGEM, VERSAO, candidatos_da_peca, confirmar
from lupa_pipeline.ingestao.eventos.modelo import PaginaTexto, PecaTexto, evidencia_de
from lupa_pipeline.ingestao.eventos.partes import chave_nome, extrair_partes
from lupa_pipeline.ingestao.repositorio_eventos import gravar_achados
from lupa_pipeline.seguranca.contexto import dek_para_gravar
from lupa_pipeline.validacoes.adaptador import para_dominio, para_modelo
from lupa_pipeline.validacoes.motor import executar_catalogo


def pecas_do_processo(session: Session, processo_id: bytes) -> list[PecaTexto]:
    """Agrupa as páginas do processo nos intervalos das peças vigentes."""
    consulta = (
        select(VisaoPagina)
        .where(VisaoPagina.hk_processo == processo_id)
        .order_by(VisaoPagina.hk_arquivo, VisaoPagina.numero)
    )
    paginas: dict[bytes, dict[int, PaginaTexto]] = defaultdict(dict)
    for p in session.scalars(atual(consulta)):
        if p.texto is None:
            continue
        intervalos = tuple(
            (int(t.get("inicio_original", t["inicio"])), int(t.get("fim_original", t["fim"])))
            for t in [*(p.trechos_ocultos or ()), *(p.trechos_suspeitos or ())]
            if t.get("inicio") is not None and t.get("fim") is not None
        )
        paginas[p.hk_arquivo][p.numero] = PaginaTexto(
            p.id,
            p.numero,
            p.texto,
            p.texto_normalizado if p.texto_normalizado is not None else p.texto,
            intervalos,
        )
    resultado = []
    for peca in session.scalars(
        atual(
            select(VisaoPeca)
            .where(VisaoPeca.hk_processo == processo_id, VisaoPeca.vigente.is_(True))
            .order_by(VisaoPeca.hk_arquivo, VisaoPeca.pagina_inicial)
        )
    ):
        arquivo = paginas[peca.hk_arquivo]
        if peca.tipo and peca.pagina_final is not None:
            resultado.append(
                PecaTexto(
                    TipoPeca(peca.tipo),
                    tuple(
                        arquivo[n]
                        for n in range(peca.pagina_inicial, peca.pagina_final + 1)
                        if n in arquivo
                    ),
                )
            )
    return resultado


def _gravar_partes(
    session: Session, processo: VisaoProcesso, pecas: list[PecaTexto]
) -> dict[str, str]:
    sujeitos: dict[str, str] = {}
    for peca in pecas:
        for parte in extrair_partes(peca):
            nome = chave_nome(parte.nome)
            if nome in sujeitos:
                continue
            evidencia = evidencia_de(parte.pagina, parte.inicio, parte.fim, parte.nome)
            if evidencia is None:
                continue
            referencia = evidencia_da_pagina(session, processo.hk_processo, evidencia)
            chave = {
                "numero_cnj": processo.numero_cnj,
                "chave_nome": hmac_processo(dek_para_gravar()[1], nome),
            }
            hk = gravar_hub(session, hub_parte, chave, ORIGEM)
            gravar_link(
                session,
                link_processo_parte,
                {"hk_processo": processo.hk_processo, "hk_parte": hk},
                ORIGEM,
            )
            gravar_satelite(
                session,
                sat_parte_identidade,
                hk,
                {
                    "nome": parte.nome,
                    "polo": parte.polo.value,
                    "qualidade": parte.qualidade.value,
                    "hk_evidencia": referencia,
                },
                ORIGEM,
            )
            sujeitos[nome] = hk.hex()
    return sujeitos


def achados_do_processo(
    session: Session, processo_id: bytes, classe: str, referencia: date
) -> list[Achado]:
    """Executa as regras para cada recorrente, usando somente as versões atuais dos fatos."""
    processo = session.get_one(VisaoProcesso, processo_id)
    modelo = para_modelo(listar_fatos_por_processo(session, processo_id))
    resultado = []
    for calculo in executar_catalogo(modelo, classe, referencia):
        chave = {
            "numero_cnj": processo.numero_cnj,
            "validacao": calculo.validacao,
            "sujeito": calculo.sujeito,
        }
        resultado.append(para_dominio(calculo, processo.id, chave_do_hub(hub_achado, chave).hex()))
    return resultado


def processar_eventos(session: Session, processo_id: bytes, referencia: date) -> dict[str, Any]:
    """Recalcula o processo inteiro a partir das páginas e peças, respeitando revisões humanas."""
    processo = processo_para_gravar(session, processo_id)
    pecas = pecas_do_processo(session, processo_id)
    sujeitos = _gravar_partes(session, processo, pecas)
    gravados: set[bytes] = set()
    rejeitados = 0
    for peca in pecas:
        for candidato in candidatos_da_peca(peca, sujeitos):
            fato = confirmar(candidato, processo.id)
            if fato is None:
                rejeitados += 1
                continue
            gravados.add(salvar_fato(session, fato))
    for anterior in listar_fatos_por_processo(session, processo_id):
        hk = bytes.fromhex(anterior.id)
        if (
            anterior.extraido_por == ORIGEM
            and anterior.status == StatusFato.AUTOMATICO
            and hk not in gravados
        ):
            for evid in anterior.evidencias:
                vincular_evidencia(session, hk, bytes.fromhex(evid.id), False)
    achados = achados_do_processo(session, processo_id, processo.classe or "", referencia)
    return {
        "versao_extrator": VERSAO,
        "partes": len(sujeitos),
        "fatos": len(gravados),
        "sem_trecho": rejeitados,
        "achados_gravados": gravar_achados(session, processo_id, achados),
        "achados": dict(Counter(a.resultado.value for a in achados)),
    }
