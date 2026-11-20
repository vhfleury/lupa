"""Chat e histórico do usuário autenticado sobre os autos de um único processo (A16)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from lupa_api.acesso.autorizacao import (
    AtorAutenticado,
    ContextoReq,
    SessaoBanco,
    exige_processo,
)
from lupa_api.acesso.erros import DadosInvalidosError
from lupa_api.agente import repositorio
from lupa_api.agente.cliente import ClienteAgente
from lupa_api.agente.servico import ContextoChat, limites_de, perguntar
from lupa_api.api.middleware import auditar_rota
from lupa_api.auditoria.eventos import AcaoAuditoria
from lupa_pipeline.config import Settings, get_settings
from lupa_pipeline.dominio.visoes import VisaoProcesso

router = APIRouter()

Processo = Annotated[VisaoProcesso, Depends(exige_processo)]
Configuracao = Annotated[Settings, Depends(get_settings)]


class CorpoPergunta(BaseModel):
    """Pergunta do assessor."""

    model_config = ConfigDict(extra="forbid")

    pergunta: str = Field(min_length=1, max_length=20_000)


def cliente_agente(request: Request) -> ClienteAgente:
    """Cliente do modelo da aplicação (substituível nos testes).

    Args:
        request: Requisição.

    Returns:
        Cliente.
    """
    cliente: ClienteAgente = request.app.state.cliente_agente
    return cliente


Cliente = Annotated[ClienteAgente, Depends(cliente_agente)]


def contexto_chat(
    processo: Processo,
    ator: AtorAutenticado,
    sessao: SessaoBanco,
    ctx: ContextoReq,
    cliente: Cliente,
    settings: Configuracao,
) -> ContextoChat:
    """Monta o contexto do caso de uso do chat.

    Args:
        processo: Processo autorizado.
        ator: Quem pergunta.
        sessao: Sessão da requisição.
        ctx: Contexto (IP, localização, instante).
        cliente: Cliente do modelo.
        settings: Configuração.

    Returns:
        Contexto.
    """
    return ContextoChat(
        session=sessao,
        processo=processo,
        hk_usuario=ator.hk_usuario,
        ctx=ctx,
        cliente=cliente,
        limites=limites_de(settings),
        referencia=ctx.agora.date(),
    )


Chat = Annotated[ContextoChat, Depends(contexto_chat)]


@router.post("/processos/{processo_id}/chat")
def perguntar_ao_chat(chat: Chat, corpo: CorpoPergunta, settings: Configuracao) -> dict[str, Any]:
    """Responde uma pergunta sobre o processo.

    Args:
        chat: Contexto do chat.
        corpo: Pergunta.
        settings: Configuração (tamanho máximo da pergunta).

    Returns:
        Mensagem do agente com citações conferidas, recusa ou teto.

    Raises:
        DadosInvalidosError: Pergunta acima do tamanho máximo.
    """
    pergunta = corpo.pergunta.strip()
    if not pergunta or len(pergunta) > settings.agente_max_caracteres_pergunta:
        raise DadosInvalidosError(
            f"a pergunta deve ter de 1 a {settings.agente_max_caracteres_pergunta} caracteres"
        )
    return perguntar(chat, pergunta)


@router.get("/processos/{processo_id}/chat")
@auditar_rota(AcaoAuditoria.PROCESSO_ABERTO, conteudo=True)
def historico_do_chat(
    processo: Processo, ator: AtorAutenticado, sessao: SessaoBanco
) -> dict[str, Any]:
    """Histórico das conversas do usuário no processo.

    Args:
        processo: Processo autorizado.
        ator: Usuário.
        sessao: Sessão da requisição.

    Returns:
        `{processo_id, conversas: [...]}`.
    """
    return {
        "processo_id": str(processo.id),
        "conversas": repositorio.historico(sessao, processo.hk_processo, ator.hk_usuario),
    }
