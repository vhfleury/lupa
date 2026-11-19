"""Gravação de eventos na cadeia única de auditoria e verificação da cadeia (A15).

O evento é uma linha de `link_evento_auditoria` (link não historizado, D8), gravada na transação
da ação auditada. `pg_advisory_xact_lock` serializa as gravações; a unicidade de `sequencia` é a
última barreira contra dois eventos com o mesmo antecessor.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from lupa_api.auditoria.eventos import CAMPOS_CANONICOS, NovoEvento, calcular_hash_evento
from lupa_api.auditoria.eventos import hash_confere as hash_do_evento_confere
from lupa_pipeline.dominio.chaves import chave_hash
from lupa_pipeline.dominio.tabelas import link_evento_auditoria
from lupa_pipeline.dominio.visoes import VisaoAuditoria

TRAVA_CADEIA = 0x4C555041
ORIGEM = "api.auditoria"
LOTE_VERIFICACAO = 2000


@dataclass(frozen=True)
class ResultadoVerificacao:
    """Resultado da verificação da cadeia.

    Attributes:
        integra: Verdadeiro se todos os elos conferem.
        total: Quantidade de eventos percorridos.
        primeira_sequencia_quebrada: `sequencia` do primeiro evento com problema, se houver.
        motivo: Descrição do problema (`hash`, `encadeamento` ou `sequencia`).
    """

    integra: bool
    total: int
    primeira_sequencia_quebrada: int | None = None
    motivo: str | None = None


def _ultimo(session: Session) -> tuple[int, str | None]:
    consulta = select(VisaoAuditoria.sequencia, VisaoAuditoria.hash_evento)
    linha = session.execute(consulta.order_by(VisaoAuditoria.sequencia.desc()).limit(1)).first()
    if linha is None:
        return 0, None
    return int(linha.sequencia), str(linha.hash_evento)


def registrar(session: Session, evento: NovoEvento) -> dict[str, Any]:
    """Grava o evento no fim da cadeia, na transação da sessão (A15, passos 2 a 5).

    Args:
        session: Sessão com transação aberta (sob `lupa_app`).
        evento: Evento a registrar.

    Returns:
        As colunas gravadas, com `sequencia`, `hash_anterior` e `hash_evento`.
    """
    session.execute(select(func.pg_advisory_xact_lock(TRAVA_CADEIA)))
    anterior, hash_anterior = _ultimo(session)
    campos: dict[str, Any] = evento.model_dump(mode="python")
    campos.update(
        acao=evento.acao.value,
        resultado=evento.resultado.value,
        sequencia=anterior + 1,
        ocorrido_em=datetime.now(UTC),
        hash_anterior=hash_anterior,
    )
    campos["hash_evento"] = calcular_hash_evento(hash_anterior, campos)
    campos["hk_evento"] = chave_hash([campos["sequencia"]])
    session.execute(insert(link_evento_auditoria).values(record_source=ORIGEM, **campos))
    return campos


def _eventos(session: Session) -> Iterator[dict[str, Any]]:
    colunas = [VisaoAuditoria.hash_anterior, VisaoAuditoria.hash_evento]
    colunas += [getattr(VisaoAuditoria, nome) for nome in CAMPOS_CANONICOS]
    consulta = (
        select(*colunas)
        .order_by(VisaoAuditoria.sequencia)
        .execution_options(yield_per=LOTE_VERIFICACAO)
    )
    for linha in session.execute(consulta):
        yield dict(linha._mapping)


def _problema(evento: Mapping[str, Any], anterior: str | None, esperada: int) -> str | None:
    if evento["sequencia"] != esperada:
        return "sequencia"
    if evento["hash_anterior"] != anterior:
        return "encadeamento"
    if not hash_do_evento_confere(evento):
        return "hash"
    return None


def verificar_cadeia(session: Session) -> ResultadoVerificacao:
    """Percorre a cadeia em ordem de `sequencia` e aponta o primeiro evento quebrado (A15, 6).

    Args:
        session: Sessão do banco.

    Returns:
        Resultado com integridade, total e, se houver, a primeira `sequencia` inconsistente.
    """
    anterior: str | None = None
    total = 0
    for evento in _eventos(session):
        total += 1
        motivo = _problema(evento, anterior, total)
        if motivo is not None:
            return ResultadoVerificacao(False, total, int(evento["sequencia"]), motivo)
        anterior = evento["hash_evento"]
    return ResultadoVerificacao(True, total)
