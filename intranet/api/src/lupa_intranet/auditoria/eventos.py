"""Ações auditadas, esquema do evento novo e serialização canônica usada no hash.

O evento só tem campos fixos: identificadores, IP, localização, ação, resultado e versões.
Não existe campo livre; por isso conteúdo dos autos, senhas e perguntas não têm onde entrar.
"""

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from lupa_pipeline.dominio.esquemas import calcular_hash


class AcaoAuditoria(StrEnum):
    """Ações registradas na trilha de auditoria."""

    LOGIN_OK = "login_ok"
    LOGIN_FALHA = "login_falha"
    LOGIN_BLOQUEADO = "login_bloqueado"
    MFA_OK = "mfa_ok"
    MFA_FALHA = "mfa_falha"
    LOGOUT = "logout"
    SENHA_TROCADA = "senha_trocada"
    SENHA_RESETADA = "senha_resetada"
    MFA_RESETADO = "mfa_resetado"
    USUARIO_CRIADO = "usuario_criado"
    USUARIO_DESATIVADO = "usuario_desativado"
    USUARIO_REATIVADO = "usuario_reativado"
    PROCESSO_CRIADO = "processo_criado"
    RESPONSAVEL_ADICIONADO = "responsavel_adicionado"
    RESPONSAVEL_REMOVIDO = "responsavel_removido"
    UPLOAD = "upload"
    PROCESSO_ABERTO = "processo_aberto"
    PAGINA_VISTA = "pagina_vista"
    BUSCA = "busca"
    PERGUNTA_CHAT = "pergunta_chat"
    ANOTACAO = "anotacao"
    FATO_CORRIGIDO = "fato_corrigido"
    PECA_RECLASSIFICADA = "peca_reclassificada"
    VALIDACAO_EXECUTADA = "validacao_executada"
    CHAMADA_MODELO = "chamada_modelo"
    CITACAO_DESCARTADA = "citacao_descartada"
    AUDITORIA_CONSULTADA = "auditoria_consultada"
    AUDITORIA_EXPORTADA = "auditoria_exportada"
    PROCESSO_EM_REVISAO = "processo_em_revisao"
    REVISAO_LIBERADA = "revisao_liberada"
    IDENTIDADE_LIDA = "identidade_lida"
    PROCESSO_DESCARTADO = "processo_descartado"
    DESCARTE_OBJETOS_PENDENTE = "descarte_objetos_pendente"


class ResultadoEvento(StrEnum):
    """Desfecho da ação auditada."""

    OK = "ok"
    FALHA = "falha"
    NEGADO = "negado"
    BLOQUEADO = "bloqueado"


class NovoEvento(BaseModel):
    """Evento a registrar; hash, sequência e instante são preenchidos pelo registrador.

    Attributes:
        acao: Ação auditada.
        resultado: Desfecho.
        hk_usuario: Quem agiu (None se desconhecido, como em login de usuário inexistente).
        hk_processo: Processo envolvido, se houver.
        objeto_tipo: Tipo do objeto (`usuario`, `pagina`, `fato`...), nunca conteúdo.
        objeto_id: Identificador do objeto (hex do `hk`, D12).
        ip: IP de origem.
        localizacao: Localização aproximada derivada do IP.
        versao_modelo: Versão do modelo, quando há chamada ao agente.
        versao_prompt: Versão do prompt, quando há chamada ao agente.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    acao: AcaoAuditoria
    resultado: ResultadoEvento = ResultadoEvento.OK
    hk_usuario: bytes | None = None
    hk_processo: bytes | None = None
    objeto_tipo: str | None = Field(default=None, max_length=40)
    objeto_id: str | None = Field(default=None, max_length=200)
    ip: str | None = Field(default=None, max_length=64)
    localizacao: str | None = Field(default=None, max_length=200)
    versao_modelo: str | None = Field(default=None, max_length=100)
    versao_prompt: str | None = Field(default=None, max_length=100)


CAMPOS_CANONICOS = (
    "sequencia",
    "ocorrido_em",
    "hk_usuario",
    "hk_processo",
    "acao",
    "objeto_tipo",
    "objeto_id",
    "ip",
    "localizacao",
    "resultado",
    "versao_modelo",
    "versao_prompt",
)


def _normalizar(valor: Any) -> Any:
    if isinstance(valor, datetime):
        return valor.astimezone(UTC).isoformat(timespec="microseconds")
    if isinstance(valor, bytes):
        return valor.hex()
    return valor


def serializar_canonico(campos: Mapping[str, Any]) -> str:
    """Serializa os campos canônicos em JSON com chaves ordenadas e sem espaços.

    Args:
        campos: Mapeamento com ao menos as chaves de `CAMPOS_CANONICOS`.

    Returns:
        JSON canônico.
    """
    dados = {nome: _normalizar(campos[nome]) for nome in CAMPOS_CANONICOS}
    return json.dumps(dados, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def calcular_hash_evento(hash_anterior: str | None, campos: Mapping[str, Any]) -> str:
    """Calcula `sha256(hash_anterior + JSON canônico)` (A15, passo 4).

    Args:
        hash_anterior: Hash do evento anterior da cadeia, ou None no primeiro.
        campos: Campos canônicos do evento.

    Returns:
        Hash hexadecimal.
    """
    return calcular_hash((hash_anterior or "") + serializar_canonico(campos))


def hash_confere(campos: Mapping[str, Any]) -> bool:
    """Recalcula o hash de um evento gravado e compara com o `hash_evento` dele.

    Args:
        campos: Colunas do evento lido do banco (`hash_anterior`, `hash_evento` e as canônicas).

    Returns:
        Verdadeiro se o hash gravado corresponde aos campos.
    """
    gravado: str = campos["hash_evento"]
    return calcular_hash_evento(campos["hash_anterior"], campos) == gravado
