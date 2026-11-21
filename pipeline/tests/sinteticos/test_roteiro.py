"""Roteiro dos autos sintéticos: peças da classe e gabaritos reprodutíveis."""

import hashlib
import json

import pytest

from lupa_pipeline.dominio.enums import ClasseProcessual, TipoPeca
from lupa_pipeline.sinteticos.gabarito import TODOS_VETORES
from lupa_pipeline.sinteticos.gerador import gerar_conteudo
from lupa_pipeline.sinteticos.roteiro import (
    Configuracao,
    PreparoSintetico,
    fatos_procurados,
    montar_roteiro,
)
from lupa_pipeline.validacoes.catalogo import validacoes_de
from lupa_pipeline.validacoes.civel import cabimento, preparo, representacao, tempestividade

SEMENTE = 11
PAGINAS_ALVO = 12

GABARITOS_ATUAIS: dict[tuple[ClasseProcessual, PreparoSintetico], str] = {
    (ClasseProcessual.APELACAO_CIVEL, PreparoSintetico.PAGO): (
        "c96e19bcfbf5eb1d17691063be2b7f31a4bf133aadc6c5ce62e18dcbcfd18f1f"
    ),
    (ClasseProcessual.APELACAO_CIVEL, PreparoSintetico.AUSENTE): (
        "ee8f601bbdc4b5b4991a711d73e62ad197f7ebdf2bcfb0c0d6a3eb27a2eb02f7"
    ),
    (ClasseProcessual.APELACAO_CIVEL, PreparoSintetico.PEDIDO): (
        "5fe5cf24efdc7c29a9418ffad08fc589380cf629a663828698f99e55500d01ae"
    ),
    (ClasseProcessual.APELACAO_CIVEL, PreparoSintetico.DEFERIDO): (
        "810bb79eb9d351eb4fc4b47ab0e5002738f6000722fb70454d876fbd48c4c19d"
    ),
    (ClasseProcessual.AGRAVO_INSTRUMENTO, PreparoSintetico.PAGO): (
        "4d0033772f9372f3f5d528dedc7eba2386254e52d575557714168f0dcfa3b8c8"
    ),
    (ClasseProcessual.AGRAVO_INSTRUMENTO, PreparoSintetico.AUSENTE): (
        "e93f839d335a91074d3fb529e409c222f47b79ce29ecf927f957f2a9393a0957"
    ),
    (ClasseProcessual.AGRAVO_INSTRUMENTO, PreparoSintetico.PEDIDO): (
        "e158a9e523bf6a2d9f158927723387480ec91067f5487b578ac85cd1e6655711"
    ),
    (ClasseProcessual.AGRAVO_INSTRUMENTO, PreparoSintetico.DEFERIDO): (
        "5dcf739a00e37860f74cf39d2ee52b2cdda1eb32d22ea2def4f04962eab77ba9"
    ),
    (ClasseProcessual.EMBARGOS_DECLARACAO, PreparoSintetico.PAGO): (
        "0bcd9871682d2715d5552355bb3bde0cf99342dc71957ccdb24c271ad5542065"
    ),
    (ClasseProcessual.EMBARGOS_DECLARACAO, PreparoSintetico.AUSENTE): (
        "0bcd9871682d2715d5552355bb3bde0cf99342dc71957ccdb24c271ad5542065"
    ),
    (ClasseProcessual.EMBARGOS_DECLARACAO, PreparoSintetico.PEDIDO): (
        "1d5085ca35cb1e3db08567b75968c2cf9b60197ecaa9608fee072a984033997e"
    ),
    (ClasseProcessual.EMBARGOS_DECLARACAO, PreparoSintetico.DEFERIDO): (
        "e1535922f43f2f6cc1b46be6ab6e4635f542ea5afb9a3a493dba0cbed6b7fa43"
    ),
    (ClasseProcessual.AGRAVO_INTERNO, PreparoSintetico.PAGO): (
        "96de92c019f81c1a37c570aab5d8b3d2d9e16689658b90f73f6d216dcb81f060"
    ),
    (ClasseProcessual.AGRAVO_INTERNO, PreparoSintetico.AUSENTE): (
        "6e5587a15b57b0d077d72409e1cee2459c693e44dc242711dfa03f2e037caa4f"
    ),
    (ClasseProcessual.AGRAVO_INTERNO, PreparoSintetico.PEDIDO): (
        "8dbe38513d8bf6924fc1cc8577815735c31b5454ab3bc60eaa0bb41611218ead"
    ),
    (ClasseProcessual.AGRAVO_INTERNO, PreparoSintetico.DEFERIDO): (
        "e42a454a5e1b160cb52531e73c0e20ab8ce5d2da4e56a81587b4f3c43621f755"
    ),
    (ClasseProcessual.ACAO_ORIGINARIA, PreparoSintetico.PAGO): (
        "5cc91120ba31d7eb1ba8a702ede8cf303b69727cfac03c1f136e3bc401b2640d"
    ),
    (ClasseProcessual.ACAO_ORIGINARIA, PreparoSintetico.AUSENTE): (
        "5cc91120ba31d7eb1ba8a702ede8cf303b69727cfac03c1f136e3bc401b2640d"
    ),
    (ClasseProcessual.ACAO_ORIGINARIA, PreparoSintetico.PEDIDO): (
        "5cc91120ba31d7eb1ba8a702ede8cf303b69727cfac03c1f136e3bc401b2640d"
    ),
    (ClasseProcessual.ACAO_ORIGINARIA, PreparoSintetico.DEFERIDO): (
        "5cc91120ba31d7eb1ba8a702ede8cf303b69727cfac03c1f136e3bc401b2640d"
    ),
}


def _hash_gabarito(classe: ClasseProcessual, preparo: PreparoSintetico) -> str:
    config = Configuracao(
        semente=SEMENTE, paginas_alvo=PAGINAS_ALVO, classe=classe, preparo=preparo,
        injecoes=TODOS_VETORES,
    )  # fmt: skip
    conteudo = gerar_conteudo(config)
    partes = {
        "pecas": [p.model_dump(mode="json") for p in conteudo.pecas],
        "paginas": [p.model_dump(mode="json") for p in conteudo.paginas],
        "partes": [p.model_dump(mode="json") for p in conteudo.partes],
        "eventos": [e.model_dump(mode="json") for e in conteudo.eventos],
        "resultado_esperado": [r.model_dump(mode="json") for r in conteudo.resultado_esperado],
        "injecoes": [i.model_dump(mode="json") for i in conteudo.injecoes],
    }
    texto = json.dumps(partes, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


@pytest.mark.parametrize("chave", sorted(GABARITOS_ATUAIS))
def test_gabaritos_gerados_iguais_aos_atuais(
    chave: tuple[ClasseProcessual, PreparoSintetico],
) -> None:
    """RNF-04: o gabarito de cada classe e preparo, com semente fixa, não muda na refatoração."""
    assert _hash_gabarito(*chave) == GABARITOS_ATUAIS[chave]


PECAS_PROCURADAS = {
    regra.NOME: set(regra.PECA_PROCURADA)
    for regra in (cabimento, preparo, representacao, tempestividade)
}
RECURSOS = {
    TipoPeca.APELACAO, TipoPeca.AGRAVO_INSTRUMENTO, TipoPeca.AGRAVO_INTERNO,
    TipoPeca.EMBARGOS_DECLARACAO,
}  # fmt: skip


@pytest.mark.parametrize("classe", list(ClasseProcessual))
def test_pecas_do_roteiro_seguem_o_catalogo_da_classe(classe: ClasseProcessual) -> None:
    """RNF-04: as peças do roteiro saem dos fatos que as regras da classe procuram."""
    esperados = set().union(*(PECAS_PROCURADAS[v.nome] for v in validacoes_de(classe)))
    roteiro = montar_roteiro(
        Configuracao(semente=SEMENTE, paginas_alvo=PAGINAS_ALVO, classe=classe)
    )
    tipos = {p.tipo for p in roteiro.pecas}
    assert fatos_procurados(classe) == esperados
    assert (TipoPeca.COMPROVANTE_PREPARO in tipos) == ("comprovante_preparo" in esperados)
    assert bool(tipos & RECURSOS) == bool(esperados)
