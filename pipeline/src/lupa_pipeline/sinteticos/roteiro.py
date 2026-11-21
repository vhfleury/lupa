"""Autos cíveis sintéticos com qualificação, marcos e documentos da classe escolhida."""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum
from typing import Any

from lupa_pipeline.dominio.enums import ClasseProcessual, OrigemPeca, QualidadeParte, TipoPeca
from lupa_pipeline.sinteticos import identidades as ids
from lupa_pipeline.sinteticos.gabarito import Composicao, TipoData, VetorInjecao
from lupa_pipeline.sinteticos.injecao import VISIVEIS, paragrafo_injecao
from lupa_pipeline.sinteticos.textos import Marca, Paragrafo, enchimento, renderizar_peca
from lupa_pipeline.validacoes.catalogo import validacoes_de
from lupa_pipeline.validacoes.civel import cabimento, preparo, representacao, tempestividade

PARAGRAFOS_POR_PAGINA = 13
_PECA_PROCURADA = {
    regra.NOME: regra.PECA_PROCURADA
    for regra in (cabimento, preparo, representacao, tempestividade)
}


class PreparoSintetico(StrEnum):
    """Documentos de preparo que serão escritos nos autos."""

    PAGO = "pago"
    AUSENTE = "ausente"
    PEDIDO = "pedido"
    DEFERIDO = "deferido"


@dataclass(frozen=True)
class Configuracao:
    """Parâmetros reprodutíveis do processo e da composição física das páginas."""

    semente: int
    paginas_alvo: int = 40
    mistura: dict[Composicao, float] = field(
        default_factory=lambda: {
            Composicao.NATIVA: 0.6,
            Composicao.DIGITALIZADA: 0.25,
            Composicao.HIBRIDA_CORPO: 0.1,
            Composicao.HIBRIDA_ASSINATURA: 0.05,
        }
    )
    classe: ClasseProcessual = ClasseProcessual.APELACAO_CIVEL
    tempestivo: bool | None = None
    preparo: PreparoSintetico = PreparoSintetico.PAGO
    qualidade: QualidadeParte = QualidadeParte.PARTICULAR
    mandato: bool = True
    injecoes: tuple[VetorInjecao, ...] = ()
    proporcao_vazias: float = 0.08
    duas_colunas: tuple[TipoPeca, ...] = ()


@dataclass
class PecaPlano:
    """Peça antes de paginar, com os valores das marcas de fatos e partes no texto."""

    tipo: TipoPeca
    origem: OrigemPeca
    titulo: str
    data: date
    tipo_data: TipoData
    paragrafos: list[Paragrafo]
    valores: dict[str, Any] = field(default_factory=dict)
    capa: bool = False
    marca_dagua: bool = False
    verso_branco: bool = False


@dataclass(frozen=True)
class Partes:
    """Identidades inventadas e dados comuns às peças do processo."""

    numero: str
    autor: str
    reu: str
    variaveis: dict[str, str]


@dataclass(frozen=True)
class Linha:
    """Marcos cronológicos usados no texto e no gabarito."""

    ajuizamento: date
    citacao: date
    contestacao: date
    decisao: date
    intimacao: date
    interposicao: date
    acordao: date
    referencia: date


@dataclass
class Roteiro:
    """Processo completo anterior à paginação."""

    configuracao: Configuracao
    partes: Partes
    linha: Linha
    pecas: list[PecaPlano]


def montar_linha(config: Configuracao, rng: random.Random) -> Linha:
    """Produz um protocolo comprovadamente dentro ou além do prazo, conforme a configuração."""
    ajuizamento = date(2026, 3, rng.randint(2, 18))
    citacao = ajuizamento + timedelta(days=rng.randint(8, 15))
    contestacao = citacao + timedelta(days=rng.randint(7, 14))
    decisao = date(2026, 7, rng.randint(1, 14))
    intimacao = decisao + timedelta(days=rng.randint(3, 9))
    no_prazo = config.tempestivo if config.tempestivo is not None else rng.choice((True, False))
    interposicao = intimacao + timedelta(days=2 if no_prazo else 60)
    acordao = max(interposicao, decisao) + timedelta(days=rng.randint(20, 30))
    return Linha(
        ajuizamento,
        citacao,
        contestacao,
        decisao,
        intimacao,
        interposicao,
        acordao,
        acordao + timedelta(days=7),
    )


def montar_partes(config: Configuracao, rng: random.Random, ano: int) -> Partes:
    """Cria partes, subscritor e signatários com dados de teste."""
    autor, reu = ids.gerar_partes(rng, config.qualidade)
    variaveis = {
        "autor": autor,
        "reu": reu,
        "advogado": ids.gerar_nome(rng),
        "oab": str(rng.randint(11000, 99000)),
        "qualidade": config.qualidade.value,
        "juiz": ids.gerar_nome(rng),
        "perito": ids.gerar_nome(rng),
        "promotor": ids.gerar_nome(rng),
    }
    return Partes(ids.gerar_numero_cnj(rng, ano), autor, reu, variaveis)


# A mesma chave determina o template e o tipo, salvo os nomes descritivos dos anexos.
_TIPOS_ANEXOS = {
    "certidao_publicacao": TipoPeca.CERTIDAO,
    "certidao_intimacao": TipoPeca.CERTIDAO,
    "juntada": TipoPeca.OUTROS,
    "laudo": TipoPeca.LAUDO_PERICIAL,
}
_SIGNATARIOS = {
    OrigemPeca.JUIZO: ("juiz", "Juiz de Direito"),
    OrigemPeca.PARTE: ("advogado", "Advogado"),
    OrigemPeca.MP: ("promotor", "Promotor de Justiça"),
    OrigemPeca.TERCEIRO: ("perito", "Perito judicial"),
}


class _Fabrica:
    def __init__(self, partes: Partes, rng: random.Random, config: Configuracao) -> None:
        self.partes = partes
        self.rng = rng
        self.config = config

    def peca(
        self,
        nome: str,
        dia: date,
        origem: OrigemPeca,
        valores: dict[str, Any] | None = None,
        extra: dict[str, str] | None = None,
        volume: int = 0,
    ) -> PecaPlano:
        tipo = _TIPOS_ANEXOS.get(nome) or TipoPeca(nome)
        variaveis = {**self.partes.variaveis, "data": dia.strftime("%d/%m/%Y"), **(extra or {})}
        titulo, paragrafos = renderizar_peca(nome, variaveis, self.rng)
        paragrafos.extend(enchimento(variaveis, self.rng, volume))
        chave, cargo = _SIGNATARIOS[origem]
        assinatura = (
            f"Documento assinado eletronicamente por {variaveis[chave]}, {cargo}, "
            f"em {variaveis['data']}."
        )
        paragrafos.append(Paragrafo(assinatura, papel="assinatura"))
        tipo_data = {
            OrigemPeca.JUIZO: TipoData.ASSINATURA,
            OrigemPeca.PARTE: TipoData.PROTOCOLO,
            OrigemPeca.MP: TipoData.PROTOCOLO,
            OrigemPeca.TERCEIRO: TipoData.JUNTADA,
        }[origem]
        return PecaPlano(
            tipo,
            origem,
            titulo,
            dia,
            tipo_data,
            paragrafos,
            dict(valores or {}),
            marca_dagua=nome in ("laudo", "juntada"),
            verso_branco=self.rng.random() < self.config.proporcao_vazias,
        )


def fatos_procurados(classe: ClasseProcessual) -> frozenset[str]:
    """Reúne os tipos de fato que as validações da classe procuram nos autos.

    Args:
        classe: Classe processual do roteiro.

    Returns:
        União das chaves de ``PECA_PROCURADA`` das regras de ``validacoes_de(classe)``.
    """
    return frozenset(
        tipo for validacao in validacoes_de(classe) for tipo in _PECA_PROCURADA[validacao.nome]
    )


def _capa(partes: Partes, linha: Linha, classe: ClasseProcessual) -> PecaPlano:
    classe_na_capa = {
        ClasseProcessual.APELACAO_CIVEL: "Apelação cível",
        ClasseProcessual.AGRAVO_INSTRUMENTO: "Agravo de instrumento",
        ClasseProcessual.AGRAVO_INTERNO: "Agravo interno",
        ClasseProcessual.EMBARGOS_DECLARACAO: "Embargos de declaração",
        ClasseProcessual.ACAO_ORIGINARIA: "Ação rescisória",
    }
    texto = [
        Paragrafo("AUTUAÇÃO", papel="titulo"),
        Paragrafo(f"Processo nº {partes.numero}"),
        Paragrafo(f"Classe processual: {classe_na_capa[classe]}"),
        Paragrafo(f"Autuado em {linha.ajuizamento:%d/%m/%Y}."),
    ]
    distribuicao = linha.ajuizamento + timedelta(days=1)
    campos = {
        "relator": ("Relator", partes.variaveis["juiz"]),
        "orgao_julgador": ("Órgão julgador", "Terceira Câmara Cível"),
        "assunto": ("Assunto", "Reparação por defeitos no imóvel"),
        "valor_causa": ("Valor da causa", "R$ 1.234,56"),
        "juizo_origem": ("Juízo de origem", f"Vara Cível da {ids.COMARCA}"),
        "data_distribuicao": ("Distribuição", distribuicao.strftime("%d/%m/%Y")),
    }
    for tipo, (rotulo, literal) in campos.items():
        linha_capa = f"{rotulo}: {literal}"
        texto.append(Paragrafo(linha_capa, [Marca(tipo, len(rotulo) + 2, len(linha_capa))]))
    valores = {tipo: literal for tipo, (_, literal) in campos.items()}
    valores.update(valor_causa="1234.56", data_distribuicao=distribuicao.isoformat())
    return PecaPlano(
        TipoPeca.OUTROS,
        OrigemPeca.JUIZO,
        "Autuação",
        linha.ajuizamento,
        TipoData.JUNTADA,
        texto,
        valores,
        capa=True,
    )


def _nucleo(fab: _Fabrica, linha: Linha) -> list[PecaPlano]:
    parte, juizo = OrigemPeca.PARTE, OrigemPeca.JUIZO
    config, partes = fab.config, fab.partes
    classe = config.classe
    fatos = fatos_procurados(classe)
    pecas = [
        fab.peca(
            "peticao_inicial",
            linha.ajuizamento,
            parte,
            {
                "parte_autora": partes.autor,
                "parte_re": partes.reu,
                "data_ajuizamento": linha.ajuizamento,
            },
        ),
        fab.peca("certidao_publicacao", linha.citacao, juizo, {"data_citacao": linha.citacao}),
        fab.peca("contestacao", linha.contestacao, parte, {"data_contestacao": linha.contestacao}),
        fab.peca("replica", linha.contestacao + timedelta(days=8), parte),
        fab.peca("laudo", linha.contestacao + timedelta(days=12), OrigemPeca.TERCEIRO),
        fab.peca("parecer_mp", linha.contestacao + timedelta(days=19), OrigemPeca.MP),
    ]
    marco = (
        "{{data_decisao_recorrida:Decisão recorrida proferida em "
        + f"{linha.decisao:%d/%m/%Y}"
        + "}}."
    )
    agravo = classe in (ClasseProcessual.AGRAVO_INSTRUMENTO, ClasseProcessual.AGRAVO_INTERNO)
    hipotese = "{{hipotese_decisao_agravada:Hipótese do art. 1.015, inciso I}}."
    if agravo:
        pecas.append(
            fab.peca(
                "decisao_interlocutoria",
                linha.decisao,
                juizo,
                {"data_decisao_recorrida": linha.decisao, "hipotese_decisao_agravada": "I"},
                {
                    "marco_decisao": marco,
                    "hipotese": hipotese if "hipotese_decisao_agravada" in fatos else "",
                },
            )
        )
    recorre_sentenca = not agravo and bool(fatos)
    pecas.append(
        fab.peca(
            "sentenca",
            linha.interposicao + timedelta(days=5) if agravo else linha.decisao,
            juizo,
            {"data_decisao_recorrida": linha.decisao},
            {"marco_decisao": marco if recorre_sentenca else ""},
        )
    )
    if not fatos:
        pecas.append(fab.peca("acordao", linha.acordao, juizo, {"data_acordao": linha.acordao}))
        return pecas
    pecas.append(
        fab.peca("certidao_intimacao", linha.intimacao, juizo, {"data_intimacao": linha.intimacao})
    )
    advogado = {"nome": partes.variaveis["advogado"], "oab": "GO" + partes.variaveis["oab"]}
    if config.mandato:
        pecas.append(
            fab.peca(
                "procuracao",
                linha.ajuizamento,
                parte,
                {
                    "procuracao": {
                        "tipo": "procuracao",
                        "outorgante": partes.autor,
                        "advogado": advogado,
                    },
                },
            )
        )
    if config.preparo == PreparoSintetico.PAGO and "comprovante_preparo" in fatos:
        pecas.append(
            fab.peca(
                "comprovante_preparo",
                linha.interposicao,
                parte,
                {"comprovante_preparo": linha.interposicao},
            )
        )
    pedido = config.preparo in (PreparoSintetico.PEDIDO, PreparoSintetico.DEFERIDO)
    tipo_peca = "apelacao" if classe == ClasseProcessual.APELACAO_CIVEL else classe.value
    pecas.append(
        fab.peca(
            tipo_peca,
            linha.interposicao,
            parte,
            {
                "tipo_recurso": classe.value,
                "data_interposicao": linha.interposicao,
                "qualidade_recorrente": config.qualidade.value,
                "advogado_subscritor": advogado,
                "gratuidade_pedido": True,
            },
            {"pedido": "{{gratuidade_pedido:Requer a gratuidade da justiça}}." if pedido else ""},
        )
    )
    if config.preparo == PreparoSintetico.DEFERIDO:
        pecas.append(
            fab.peca(
                "decisao_interlocutoria",
                linha.interposicao + timedelta(days=1),
                juizo,
                {"gratuidade_decisao": "deferida"},
                {
                    "marco_decisao": f"Recorrente: {partes.autor}",
                    "hipotese": "{{gratuidade_decisao:Defiro a gratuidade da justiça}}.",
                },
            )
        )
    pecas.extend(
        [
            fab.peca("contrarrazoes", linha.interposicao + timedelta(days=9), parte),
            fab.peca("acordao", linha.acordao, juizo, {"data_acordao": linha.acordao}),
        ]
    )
    return pecas


def _volume(fab: _Fabrica, linha: Linha, pecas: list[PecaPlano], alvo: int) -> None:
    estimado = sum(len(p.paragrafos) // PARAGRAFOS_POR_PAGINA + 1 for p in pecas)
    while estimado < alvo:
        folhas = min(alvo - estimado, fab.rng.choice((1, 2, 5, 8, 15, 30)))
        dia = linha.citacao + timedelta(
            days=fab.rng.randint(1, (linha.acordao - linha.citacao).days)
        )
        anexo = fab.peca(
            fab.rng.choice(("juntada", "laudo")),
            dia,
            OrigemPeca.TERCEIRO,
            volume=max(0, folhas * PARAGRAFOS_POR_PAGINA - 3),
        )
        pecas.append(anexo)
        estimado += len(anexo.paragrafos) // PARAGRAFOS_POR_PAGINA + 1


def montar_roteiro(config: Configuracao, alvo: int | None = None) -> Roteiro:
    """Monta a capa e as peças da classe na ordem cronológica, com os vetores solicitados."""
    rng = random.Random(config.semente)  # noqa: S311
    linha = montar_linha(config, rng)
    partes = montar_partes(config, rng, linha.ajuizamento.year)
    fab = _Fabrica(partes, rng, config)
    pecas = _nucleo(fab, linha)
    if config.injecoes:
        pecas.append(fab.peca("juntada", linha.citacao + timedelta(days=2), OrigemPeca.TERCEIRO))
    _volume(fab, linha, pecas, (alvo or config.paginas_alvo) - 1)
    pecas.sort(key=lambda p: p.data)
    for vetor in config.injecoes:
        if vetor in VISIVEIS:
            alvo_visivel = next(p for p in pecas if p.tipo == VISIVEIS[vetor])
            alvo_visivel.paragrafos.insert(-1, paragrafo_injecao(vetor))
    return Roteiro(config, partes, linha, [_capa(partes, linha, config.classe), *pecas])
