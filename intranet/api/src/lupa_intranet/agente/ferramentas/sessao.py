"""Contexto das ferramentas limitado ao processo da conversa pelo servidor."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from lupa_intranet.agente.contexto import Delimitador
from lupa_intranet.auditoria.eventos import AcaoAuditoria
from lupa_pipeline.dominio.visoes import VisaoArquivo, VisaoPagina, VisaoPeca

Registrador = Callable[[AcaoAuditoria, str, str], None]
"""Grava um evento de auditoria: `(acao, objeto_tipo, objeto_id)`."""


@dataclass
class SessaoAgente:
    """Contexto de uma chamada; criado por requisição.

    Attributes:
        session: Sessão do banco da requisição.
        processo_id: Processo da conversa.
        classe: Classe do processo (catálogo de validações).
        numero_cnj: Número do processo.
        delimitador: Delimitador aleatório da chamada.
        registrar: Grava evento de auditoria.
        referencia: Data de referência das validações.
        limite_paginas_originais: Máximo de `ler_pagina_original` por conversa.
        paginas_originais: Quantas já foram usadas na conversa.
        saidas: Saídas das ferramentas nesta chamada.
    """

    session: Session
    processo_id: bytes
    classe: str
    numero_cnj: str
    delimitador: Delimitador
    registrar: Registrador
    referencia: date
    limite_paginas_originais: int = 20
    paginas_originais: int = 0
    saidas: list[str] = field(default_factory=list)


class PaginaForaDoProcessoError(LookupError):
    """Página inexistente ou de outro processo."""


def _id(valor: Any) -> str:
    if (
        not isinstance(valor, str)
        or len(valor) != 64
        or any(c not in "0123456789abcdefABCDEF" for c in valor)
    ):
        raise PaginaForaDoProcessoError("identificador inválido")
    return valor.lower()


def arquivos_do_processo(sessao: SessaoAgente) -> list[str]:
    """Arquivos do processo em ordem de envio.

    Args:
        sessao: Sessão do agente.

    Returns:
        Ids.
    """
    consulta = (
        select(VisaoArquivo.id)
        .where(VisaoArquivo.hk_processo == sessao.processo_id)
        .order_by(VisaoArquivo.criado_em, VisaoArquivo.id)
    )
    return list(sessao.session.scalars(consulta))


def _por_id(sessao: SessaoAgente, pagina_id: str) -> VisaoPagina:
    consulta = select(VisaoPagina).where(
        VisaoPagina.id == pagina_id, VisaoPagina.hk_processo == sessao.processo_id
    )
    pagina = sessao.session.scalar(consulta)
    if pagina is None:
        raise PaginaForaDoProcessoError("página não pertence a este processo")
    return pagina


def _por_numero(sessao: SessaoAgente, numero: int, arquivo: str | None) -> VisaoPagina:
    arquivos = arquivos_do_processo(sessao)
    if arquivo is None:
        if len(arquivos) != 1:
            raise PaginaForaDoProcessoError("informe arquivo_id: o processo tem mais de um arquivo")
        arquivo = arquivos[0]
    if arquivo not in arquivos:
        raise PaginaForaDoProcessoError("arquivo não pertence a este processo")
    consulta = select(VisaoPagina).where(
        VisaoPagina.arquivo_id == arquivo, VisaoPagina.numero == numero
    )
    pagina = sessao.session.scalar(consulta)
    if pagina is None:
        raise PaginaForaDoProcessoError("página não encontrada neste processo")
    return pagina


def resolver_pagina(sessao: SessaoAgente, argumentos: dict[str, Any]) -> VisaoPagina:
    """Página pedida pelo modelo, sempre dentro do processo da sessão.

    Args:
        sessao: Sessão do agente.
        argumentos: `pagina_id`, ou `numero` (com `arquivo_id` se houver mais de um arquivo).

    Returns:
        A página.

    Raises:
        PaginaForaDoProcessoError: Página de outro processo, inexistente ou pedido ambíguo.
    """
    if argumentos.get("pagina_id"):
        return _por_id(sessao, _id(argumentos["pagina_id"]))
    numero = argumentos.get("numero")
    if not isinstance(numero, int) or isinstance(numero, bool):
        raise PaginaForaDoProcessoError("informe pagina_id ou numero")
    arquivo = _id(argumentos["arquivo_id"]) if argumentos.get("arquivo_id") else None
    return _por_numero(sessao, numero, arquivo)


def peca_da_pagina(sessao: SessaoAgente, pagina: VisaoPagina) -> tuple[str, str]:
    """Tipo e origem da peça vigente que contém a página.

    Args:
        sessao: Sessão do agente.
        pagina: Página.

    Returns:
        `(tipo, origem)`; `("desconhecido", "desconhecida")` sem peça.
    """
    consulta = (
        select(VisaoPeca.tipo, VisaoPeca.origem)
        .where(
            VisaoPeca.arquivo_id == pagina.arquivo_id,
            VisaoPeca.vigente.is_(True),
            VisaoPeca.pagina_inicial <= pagina.numero,
            VisaoPeca.pagina_final >= pagina.numero,
        )
        .order_by(VisaoPeca.confianca.desc(), VisaoPeca.id)
        .limit(1)
    )
    linha = sessao.session.execute(consulta).first()
    return (str(linha[0]), str(linha[1])) if linha else ("desconhecido", "desconhecida")


def flags_ligadas(flags: dict[str, Any]) -> list[str]:
    """Flags de saneamento ligadas na página.

    Args:
        flags: `pagina.flags`.

    Returns:
        Nomes em ordem.
    """
    return sorted(k for k, v in (flags or {}).items() if v)
