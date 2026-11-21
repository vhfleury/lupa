"""Coleta fatos e evidências, localiza conflitos e preenche os modelos de frase."""

from collections.abc import Iterable
from datetime import date, datetime
from importlib.resources import files
from typing import Any

from lupa_pipeline.dominio.enums import ResultadoAchado
from lupa_pipeline.validacoes.modelo import (
    AchadoValidacao,
    ConflitoDeFatosError,
    Fato,
    ModeloProcesso,
    valor_de,
)
from lupa_pipeline.validacoes.versao import VERSAO_CATALOGO

PECAS = {
    "tipo_recurso": "petição de recurso",
    "data_intimacao": "certidão de intimação",
    "data_interposicao": "protocolo da petição de recurso",
    "qualidade_recorrente": "qualificação das partes na petição do recurso",
    "comprovante_preparo": "comprovante de preparo",
    "gratuidade_pedido": "petição do recorrente",
    "gratuidade_decisao": "decisão sobre a gratuidade",
    "advogado_subscritor": "assinatura da petição de recurso",
    "procuracao": "procuração ou substabelecimento",
    "hipotese_decisao_agravada": "decisão interlocutória agravada",
}


def data_de(fato: Fato) -> date:
    """Lê uma data civil ISO, sem truncar um instante para data."""
    valor = valor_de(fato)
    if isinstance(valor, str):
        return date.fromisoformat(valor)
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    raise ValueError(f"fato {fato.tipo} sem data válida")


def renderizar(nome: str, **campos: object) -> str:
    """Preenche o modelo de frase versionado do achado."""
    arquivo = files("lupa_pipeline.validacoes").joinpath("templates", f"{nome}.txt")
    return arquivo.read_text(encoding="utf-8").strip().format(**campos)


class Coleta:
    """Valores considerados numa validação e evidência de cada um."""

    def __init__(self, modelo: ModeloProcesso, validacao: str, base_legal: str) -> None:
        """Inicia a coleta do recorrente sem fatos utilizados."""
        self.modelo = modelo
        self.validacao = validacao
        self.base_legal = base_legal
        self.usados: dict[str, Fato] = {}
        self.faltantes: list[str] = []
        self.conflitos: list[dict[str, Any]] = []

    def registrar(self, fatos: Iterable[Fato]) -> None:
        """Inclui as fontes que sustentam a conclusão."""
        self.usados.update({str(f.id): f for f in fatos})

    def qualidade(self) -> str | None:
        """Qualidade do recorrente provada, ou ``None`` quando falta ou diverge."""
        fato = self.unico("qualidade_recorrente")
        return None if fato is None else str(valor_de(fato))

    def unico(self, tipo: str, *, obrigatorio: bool = True) -> Fato | None:
        """Seleciona o valor único ou registra sua ausência ou divergência."""
        try:
            fato = self.modelo.fato(tipo)
        except ConflitoDeFatosError as erro:
            self.conflitos.append({"tipo": tipo, "fato_ids": erro.fato_ids})
            self.registrar(self.modelo.fatos(tipo))
            return None
        if fato is not None:
            self.registrar([fato])
        elif obrigatorio:
            self.faltantes.append(tipo)
        return fato

    def concluir(self, resultado: ResultadoAchado, motivo: str, **valores: Any) -> AchadoValidacao:
        """Vincula os valores, a origem de cada um, a base legal e a frase ao resultado."""
        referencias = [
            {
                "tipo": fato.tipo.value,
                "valor": fato.model_dump(mode="json")["valor"],
                "fato_id": str(fato.id),
                "evidencia_ids": [str(e.id) for e in fato.evidencias],
                "pagina_ids": [str(e.pagina_id) for e in fato.evidencias],
            }
            for _, fato in sorted(self.usados.items())
        ]
        pecas = {tipo: PECAS[tipo] for tipo in self.faltantes}
        return AchadoValidacao(
            validacao=self.validacao,
            sujeito=self.modelo.sujeito,
            versao_catalogo=VERSAO_CATALOGO,
            resultado=resultado,
            fatos_usados=tuple(sorted(self.usados)),
            valores={
                **valores,
                "base_legal": self.base_legal,
                "motivo": motivo,
                "fatos": referencias,
                "faltantes": self.faltantes,
                "pecas_procuradas": pecas,
                "conflitos": self.conflitos,
            },
            explicacao=renderizar(
                f"{self.validacao}_{resultado.value}",
                motivo=motivo,
                base_legal=self.base_legal,
            ),
        )

    def verificar(self, motivo: str = "") -> AchadoValidacao:
        """Explica uma ausência ou cita os fatos incompatíveis na saída de conferência."""
        faltas = [f"{tipo} ({PECAS[tipo]})" for tipo in self.faltantes]
        conflitos = [f"{c['tipo']} ({', '.join(c['fato_ids'])})" for c in self.conflitos]
        razoes = [motivo] if motivo else []
        if faltas:
            razoes.append(
                "Confira os fatos ausentes nas peças indicadas (" + ", ".join(faltas) + ")."
            )
        if conflitos:
            razoes.append("Os fatos divergem em " + ", ".join(conflitos) + ".")
        return self.concluir(ResultadoAchado.VERIFICAR, " ".join(razoes))

    @property
    def pendente(self) -> bool:
        """Indica falta ou conflito em um dos valores necessários."""
        return bool(self.faltantes or self.conflitos)
