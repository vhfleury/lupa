"""Esquemas pydantic do domínio: contratos de entrada e saída compartilhados entre etapas.

`Fato` e `Evidencia` são o contrato consumido pelas validações (Etapa 2).
"""

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Annotated, Any, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from lupa_pipeline.dominio.cnj import validar_numero_cnj
from lupa_pipeline.dominio.enums import (
    CenarioArquivo,
    ClasseProcessual,
    FlagPagina,
    ResultadoAchado,
    StatusFato,
    StatusProcesso,
    TipoFato,
    TipoPagina,
)

NumeroCnj = Annotated[str, AfterValidator(validar_numero_cnj)]
IdPublico = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Sujeito = Annotated[str, Field(pattern=r"^([0-9a-f]{64})?$")]
Confianca = Annotated[float, Field(ge=0.0, le=1.0)]


def _agora() -> datetime:
    return datetime.now(UTC)


def calcular_hash(texto: str) -> str:
    """Calcula o SHA-256 hexadecimal de um texto em UTF-8.

    Args:
        texto: Texto de entrada.

    Returns:
        Hash hexadecimal com 64 caracteres.
    """
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


class EsquemaBase(BaseModel):
    """Base dos esquemas: imutáveis e sem campos extras."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Processo(EsquemaBase):
    """Processo cível de gabinete único com identificador público do hub."""

    id: IdPublico
    numero_cnj: NumeroCnj
    classe: ClasseProcessual
    status: StatusProcesso = StatusProcesso.CRIADO
    criado_em: datetime = Field(default_factory=_agora)
    criado_por: IdPublico


class Arquivo(EsquemaBase):
    """Arquivo enviado (PDF dos autos); imutável."""

    id: IdPublico
    processo_id: IdPublico
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    tamanho_bytes: int = Field(gt=0)
    nome_original: str = Field(min_length=1)
    mime: str = Field(min_length=1)
    chave_storage: str = Field(min_length=1)
    enviado_por: IdPublico
    enviado_em: datetime = Field(default_factory=_agora)


class Pagina(EsquemaBase):
    """Página de um arquivo com seu texto e marcadores de ingestão."""

    id: IdPublico
    arquivo_id: IdPublico
    numero: int = Field(ge=1)
    tipo: TipoPagina
    texto: str
    hash_texto: str = ""
    flags: dict[FlagPagina, bool] = Field(default_factory=dict)
    sinais: dict[str, Any] = Field(default_factory=dict)
    coordenadas: dict[str, Any] = Field(default_factory=dict)
    texto_nativo: str | None = None
    texto_ocr: str | None = None
    versao_extrator: str | None = None
    texto_normalizado: str | None = None
    trechos_ocultos: list[dict[str, Any]] = Field(default_factory=list)
    trechos_suspeitos: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _hash_confere(self) -> Self:
        esperado = calcular_hash(self.texto)
        if not self.hash_texto:
            object.__setattr__(self, "hash_texto", esperado)
        elif self.hash_texto != esperado:
            raise ValueError("hash_texto não corresponde a sha256(texto)")
        return self


class Evidencia(EsquemaBase):
    """Trecho de página que sustenta um fato; `hash_trecho` é calculado se omitido."""

    id: IdPublico
    pagina_id: IdPublico
    trecho: str = Field(min_length=1)
    hash_trecho: str = ""
    inicio: int = Field(ge=0)
    fim: int = Field(ge=1)
    bbox: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _consistente(self) -> Self:
        if self.fim <= self.inicio:
            raise ValueError("fim deve ser maior que inicio")
        esperado = calcular_hash(self.trecho)
        if not self.hash_trecho:
            object.__setattr__(self, "hash_trecho", esperado)
        elif self.hash_trecho != esperado:
            raise ValueError("hash_trecho não corresponde a sha256(trecho)")
        return self


class Fato(EsquemaBase):
    """Fato extraído dos autos; não existe sem ao menos uma evidência."""

    id: IdPublico
    processo_id: IdPublico
    tipo: TipoFato
    sujeito: Sujeito = ""
    valor: Any
    evidencias: tuple[Evidencia, ...] = Field(min_length=1)
    extraido_por: str = Field(min_length=1)
    versao_extrator: str = Field(min_length=1)
    confianca: Confianca
    status: StatusFato = StatusFato.AUTOMATICO
    criado_em: datetime = Field(default_factory=_agora)

    @classmethod
    def de_registro(cls, registro: Mapping[str, Any]) -> Self:
        """Valida o fato lido do banco, trocando o valor antigo `{"valor": x, ...}` por `x`."""
        valor = registro.get("valor")
        if isinstance(valor, dict) and "valor" in valor:
            return cls.model_validate({**registro, "valor": valor["valor"]})
        return cls.model_validate(registro)


class Achado(EsquemaBase):
    """Resultado de uma validação, gerado só pelo motor; imutável."""

    id: IdPublico
    processo_id: IdPublico
    validacao: str = Field(min_length=1)
    sujeito: Sujeito = ""
    versao_catalogo: str = Field(min_length=1)
    resultado: ResultadoAchado
    fatos_usados: tuple[IdPublico, ...] = ()
    valores: dict[str, Any] = Field(default_factory=dict)
    explicacao: str
    criado_em: datetime = Field(default_factory=_agora)


class EventoAuditoria(EsquemaBase):
    """Evento da cadeia única com os identificadores públicos dos hubs (RF-AUD-04)."""

    id: IdPublico
    ocorrido_em: datetime
    usuario_id: IdPublico | None
    processo_id: IdPublico | None
    acao: str = Field(min_length=1)
    objeto_tipo: str | None = None
    objeto_id: str | None = None
    ip: str | None = None
    localizacao: str | None = None
    resultado: str = Field(min_length=1)
    versao_modelo: str | None = None
    versao_prompt: str | None = None
    hash_anterior: str | None = None
    hash_evento: str = Field(min_length=1)
    sequencia: int = Field(default=1, ge=1)


class EntradaManifesto(EsquemaBase):
    """Entrada do manifesto de um arquivo (uma por PDF; um ZIP tem várias).

    Attributes:
        ordem: Posição na ordem por nome, a partir de 1.
        nome: Nome da entrada (para PDF avulso, o nome original).
        tamanho_bytes: Tamanho descomprimido.
        sha256: Hash do conteúdo.
    """

    ordem: int = Field(ge=1)
    nome: str = Field(min_length=1)
    tamanho_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class DiagnosticoArquivo(EsquemaBase):
    """Diagnóstico do arquivo: cenário de empacotamento e sinais medidos."""

    arquivo_id: IdPublico
    cenario: CenarioArquivo
    total_paginas: int = Field(ge=0)
    tem_indice: bool
    sinais: dict[str, Any] = Field(default_factory=dict)
    fronteiras_origem: list[dict[str, Any]] = Field(default_factory=list)
    metadados_descartados: list[dict[str, Any]] = Field(default_factory=list)
