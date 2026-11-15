"""RNF-04. Autos com peças, partes, evidências e conclusões de cada classe cível."""

from pathlib import Path

import pytest

from lupa_pipeline.dominio.enums import ClasseProcessual, Polo, TipoFato
from lupa_pipeline.sinteticos.empacotamento import exportar
from lupa_pipeline.sinteticos.gabarito import Cenario, Composicao, Gabarito
from lupa_pipeline.sinteticos.gerador import gerar_conteudo
from lupa_pipeline.sinteticos.roteiro import Configuracao


@pytest.mark.parametrize(
    ("classe", "peca_recurso", "validacoes"),
    [
        (
            "apelacao_civel",
            "apelacao",
            {"tempestividade_recurso", "preparo_recurso", "representacao_recurso"},
        ),
        (
            "agravo_instrumento",
            "agravo_instrumento",
            {
                "tempestividade_recurso",
                "preparo_recurso",
                "representacao_recurso",
                "cabimento_agravo",
            },
        ),
        (
            "agravo_interno",
            "agravo_interno",
            {"tempestividade_recurso", "preparo_recurso", "representacao_recurso"},
        ),
        (
            "embargos_declaracao",
            "embargos_declaracao",
            {"tempestividade_recurso", "representacao_recurso"},
        ),
        ("acao_originaria", None, set()),
    ],
)
def test_gabarito_de_cada_classe(
    classe: str, peca_recurso: str | None, validacoes: set[str], tmp_path: Path
) -> None:
    """Relê o arquivo exportado e confere as evidências contra o texto realmente emitido."""
    config = Configuracao(
        classe=ClasseProcessual(classe),
        semente=19,
        paginas_alvo=15,
        tempestivo=True,
        mistura={Composicao.NATIVA: 1.0},
        proporcao_vazias=0,
    )
    conteudo = gerar_conteudo(config)
    try:
        (arquivo,) = exportar(conteudo, tmp_path, (Cenario.PDF_LISO,))
    finally:
        conteudo.documento.close()
    gabarito = Gabarito.model_validate_json(arquivo.gabarito.read_bytes())
    assert gabarito.processo.classe == classe
    assert {p.polo for p in gabarito.partes} == {Polo.ATIVO, Polo.PASSIVO}
    assert len({p.nome for p in gabarito.partes}) == 2
    for registro in (*gabarito.partes, *gabarito.eventos):
        pagina = gabarito.pagina(registro.pagina)
        assert pagina.texto[registro.inicio : registro.fim] == registro.trecho
    for parte in gabarito.partes:
        assert parte.nome in parte.trecho
    assert set(a.validacao for a in gabarito.resultado_esperado) == validacoes
    tipos = {p.tipo for p in gabarito.pecas}
    assert {"peticao_inicial", "contestacao", "replica"} <= tipos
    if peca_recurso:
        assert peca_recurso in tipos
        (recurso,) = [e for e in gabarito.eventos if e.tipo == TipoFato.TIPO_RECURSO]
        assert recurso.valor == classe
        assert recurso.sujeito in {p.nome for p in gabarito.partes}
        assert all(a.resultado == "conforme" for a in gabarito.resultado_esperado)
    else:
        assert all(e.tipo != TipoFato.TIPO_RECURSO for e in gabarito.eventos)
