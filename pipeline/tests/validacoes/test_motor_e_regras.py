"""Testes do motor, catálogo, CLI, dados versionados e regras estruturais da Etapa 2."""

import ast
import json
import re
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from lupa_pipeline.dominio.esquemas import Fato
from lupa_pipeline.logging import configurar_logging
from lupa_pipeline.validacoes import catalogo
from lupa_pipeline.validacoes.__main__ import main
from lupa_pipeline.validacoes.apoio import Coleta, FatoPendenteError
from lupa_pipeline.validacoes.calendario import (
    FeriadoCalendario,
    Periodo,
    contar_prazo_util,
    idade_em,
    somar_meses,
)
from lupa_pipeline.validacoes.catalogo import Validacao, validacoes_de
from lupa_pipeline.validacoes.dados import (
    ArquivoFeriados,
    ArquivoSuspensoes,
    cabimento_padrao,
    calendario_padrao,
    caminho_padrao,
    carregar,
    dispensas_padrao,
    prazos_recursos_padrao,
)
from lupa_pipeline.validacoes.modelo import AchadoValidacao, ConflitoDeFatosError, ModeloProcesso
from lupa_pipeline.validacoes.motor import executar_catalogo
from tests.validacoes.conftest import criar_fato, id_sintetico, modelo_de

RAIZ = Path(__file__).resolve().parents[2]
PACOTE = RAIZ / "src" / "lupa_pipeline" / "validacoes"
EXEMPLO = Path(__file__).with_name("fatos_exemplo.json")
REFERENCIA = date(2026, 10, 20)
CONSTANTES_PERMITIDAS = {"_SABADO", "_DOMINGO", "_MESES_NO_ANO"}


def _modelo_exemplo() -> ModeloProcesso:
    dados = json.loads(EXEMPLO.read_text(encoding="utf-8"))
    return ModeloProcesso(Fato.model_validate(d) for d in dados)


def test_validacoes_sao_puras_mesma_entrada_mesmo_achado() -> None:
    """Validacoes sao puras mesma entrada mesmo achado."""
    modelo = _modelo_exemplo()
    primeira = [a.model_dump() for a in executar_catalogo(modelo, "apelacao_civel", REFERENCIA)]
    segunda = [a.model_dump() for a in executar_catalogo(modelo, "apelacao_civel", REFERENCIA)]
    assert primeira == segunda


def test_achados_conclusivos_trazem_datas_com_fato_e_evidencia() -> None:
    """Achados conclusivos trazem datas com fato e evidencia."""
    modelo = _modelo_exemplo()
    achados = executar_catalogo(modelo, "apelacao_civel", REFERENCIA)
    assert all(a.resultado in ("conforme", "atencao") for a in achados)
    ids_fatos = {f.id for f in modelo.todos}
    for achado in achados:
        referencias = achado.valores["fatos"]
        assert referencias
        assert all(d["evidencia_ids"] and d["pagina_ids"] for d in referencias)
        assert {d["fato_id"] for d in referencias} == set(achado.fatos_usados) <= ids_fatos


def test_motor_sobrevive_a_excecao_e_devolve_as_demais(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Motor sobrevive a excecao e devolve as demais."""

    def explode(modelo: ModeloProcesso, referencia: date) -> AchadoValidacao:
        raise RuntimeError("falha sintética")

    configurar_logging(estrito=True)
    quebrada = Validacao("quebrada", "sintética", explode)
    originais = catalogo.CATALOGO["apelacao_civel"]
    monkeypatch.setitem(catalogo.CATALOGO, "apelacao_civel", (quebrada, *originais))
    achados = executar_catalogo(_modelo_exemplo(), "apelacao_civel", REFERENCIA)
    assert len(achados) == len(originais) + 1
    assert achados[0].resultado == "verificar"
    assert achados[0].explicacao == (
        "A regra quebrada não conseguiu concluir a conferência dos valores. Confira os autos."
    )
    assert all(a.resultado != "verificar" for a in achados[1:])
    assert json.loads(capsys.readouterr().out)["erro_tipo"] == "RuntimeError"


def test_achado_grava_versao_do_catalogo() -> None:
    """AchadoValidacao grava versao do catalogo."""
    achados = executar_catalogo(_modelo_exemplo(), "apelacao_civel", REFERENCIA)
    assert {a.versao_catalogo for a in achados} == {catalogo.VERSAO_CATALOGO}


def test_catalogo_de_acao_originaria_e_vazio_e_classe_desconhecida_falha() -> None:
    """RF-VAL-01: ação originária fica sem achados e uma classe fora da tabela falha."""
    assert validacoes_de("acao_originaria") == ()
    with pytest.raises(ValueError, match="classe"):
        validacoes_de("trabalhista")


def test_cli_imprime_achados_do_exemplo(capsys: pytest.CaptureFixture[str]) -> None:
    """Cli imprime achados do exemplo."""
    codigo = main(
        ["--fatos", str(EXEMPLO), "--classe", "apelacao_civel", "--referencia", "2026-10-20"]
    )
    saida = json.loads(capsys.readouterr().out)
    assert codigo == 0
    gabarito = EXEMPLO.with_name("achados_exemplo.json")
    assert saida == json.loads(gabarito.read_text(encoding="utf-8"))
    assert [(a["validacao"], a["resultado"]) for a in saida] == [
        ("tempestividade_recurso", "atencao"),
        ("preparo_recurso", "conforme"),
        ("representacao_recurso", "conforme"),
    ]
    assert saida[0]["valores"]["vencimento"] == "2026-08-24"
    assert saida[0]["valores"]["atraso_dias_uteis"] == 1
    assert len(saida[2]["valores"]["paginas_mandato"]) == 1


def test_fato_sem_evidencia_e_rejeitado() -> None:
    """Fato sem evidencia e rejeitado."""
    base = criar_fato("data_ajuizamento", "2030-01-01").model_dump()
    with pytest.raises(ValidationError):
        Fato.model_validate({**base, "evidencias": []})


def test_modelo_aceita_repeticao_com_mesmo_valor_e_acusa_conflito() -> None:
    """Modelo aceita repeticao com mesmo valor e acusa conflito."""
    modelo = modelo_de(
        criar_fato("data_ajuizamento", "2030-01-01", fato_id="a"),
        criar_fato("data_ajuizamento", "2030-01-01", fato_id="b"),
        criar_fato("data_decisao_recorrida", "2030-01-01"),
        criar_fato("data_decisao_recorrida", "2030-02-01"),
    )
    fato = modelo.fato("data_ajuizamento")
    assert fato is not None and fato.id == min(id_sintetico("a"), id_sintetico("b"))
    assert modelo.fato("inexistente") is None
    with pytest.raises(ConflitoDeFatosError):
        modelo.fato("data_decisao_recorrida")


def test_modelo_recorta_por_recorrente_e_classe() -> None:
    """RF-VAL-01: uma parte não empresta fatos a outra; recurso de outra classe fica de fora."""
    a, b = id_sintetico("a"), id_sintetico("b")
    comum = criar_fato("data_ajuizamento", "2026-06-01", sujeito="")
    modelo = modelo_de(
        comum,
        criar_fato("tipo_recurso", "apelacao_civel", sujeito=a),
        criar_fato("tipo_recurso", "agravo_interno", sujeito=b),
        criar_fato("data_interposicao", "2026-06-07", sujeito=a),
        criar_fato("data_interposicao", "2026-06-18", sujeito=b),
    )
    (recorte,) = modelo.recorrentes("apelacao_civel")
    assert recorte.sujeito == a and comum in recorte.todos
    assert {f.sujeito for f in recorte.todos} == {"", a}
    assert modelo.recorrentes("embargos_declaracao") == []
    assert {f.sujeito for f in modelo.recorrentes("agravo_interno")} == {b}


def test_prazo_util_pula_fim_de_semana_feriado_e_suspensao() -> None:
    """Prazo util pula fim de semana feriado e suspensao."""
    sexta = date(2030, 3, 1)
    resultado = contar_prazo_util(
        sexta,
        3,
        {date(2030, 3, 5): FeriadoCalendario("feriado sintético")},
        [Periodo(date(2030, 3, 6), date(2030, 3, 6), "suspensão sintética")],
    )
    assert resultado.vencimento == date(2030, 3, 8)
    assert len(resultado.dias_suspensos) == 4


def test_somar_meses_e_idade() -> None:
    """Somar meses e idade."""
    assert somar_meses(date(2028, 2, 29), 12) == date(2029, 2, 28)
    assert somar_meses(date(2030, 11, 30), 3) == date(2031, 2, 28)
    assert idade_em(date(2000, 5, 10), date(2020, 5, 9)) == 19
    assert idade_em(date(2000, 5, 10), date(2020, 5, 10)) == 20


def test_dados_empacotados_tem_versao_e_fonte_e_sao_validos() -> None:
    """Dados empacotados tem versao e fonte e sao validos."""
    _, versoes = calendario_padrao()
    assert set(versoes) == {
        "feriados/nacionais.yaml",
        "feriados/tjgo.yaml",
        "suspensoes_prazo.yaml",
    }
    for tabela in (prazos_recursos_padrao(), dispensas_padrao(), cabimento_padrao()):
        assert tabela.versao and tabela.fonte


def test_todo_yaml_de_dados_exige_versao_e_fonte() -> None:
    """Todo yaml de dados exige versao e fonte."""
    arquivos = sorted((PACOTE / "dados").rglob("*.yaml"))
    assert len(arquivos) == 6
    for arquivo in arquivos:
        texto = arquivo.read_text(encoding="utf-8")
        assert re.search(r"^versao:", texto, re.M) and re.search(r"^fonte:", texto, re.M)


def test_arquivo_sem_versao_e_rejeitado(tmp_path: Path) -> None:
    """Arquivo sem versao e rejeitado."""
    arquivo = tmp_path / "feriados.yaml"
    arquivo.write_text("fonte: x\nabrangencia: y\nferiados: []\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        carregar(arquivo, ArquivoFeriados)


def test_suspensao_com_fim_antes_do_inicio_e_rejeitada() -> None:
    """Suspensao com fim antes do inicio e rejeitada."""
    with pytest.raises(ValidationError):
        ArquivoSuspensoes.model_validate(
            {
                "versao": "1",
                "fonte": "sintética",
                "suspensoes": [
                    {
                        "inicio": "2030-01-10",
                        "fim": "2030-01-01",
                        "descricao": "x",
                        "base_legal": "y",
                    }
                ],
            }
        )


def test_caminho_padrao_aponta_para_arquivo_existente() -> None:
    """Caminho padrao aponta para arquivo existente."""
    assert caminho_padrao("feriados/tjgo.yaml").is_file()


def _arquivos_py() -> list[Path]:
    return sorted(PACOTE.rglob("*.py"))


def test_nenhuma_validacao_importa_camadas_proibidas() -> None:
    """Nenhuma validacao importa camadas proibidas; do domínio, só esquemas e enums."""
    proibidos = (
        "lupa_pipeline.dominio",
        "lupa_pipeline.ingestao",
        "lupa_api.agente",
        "lupa_api.api",
    )
    permitidos = {"lupa_pipeline.dominio.esquemas", "lupa_pipeline.dominio.enums"}
    for arquivo in _arquivos_py():
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            nomes = []
            if isinstance(no, ast.Import):
                nomes = [a.name for a in no.names]
            elif isinstance(no, ast.ImportFrom) and no.module:
                nomes = [no.module]
            assert not [
                n for n in nomes if n.startswith(proibidos) and n not in permitidos
            ], arquivo


def test_nenhum_numero_de_prazo_ou_data_em_arquivo_py() -> None:
    """Nenhum numero de prazo ou data em arquivo py."""
    for arquivo in _arquivos_py():
        texto = arquivo.read_text(encoding="utf-8")
        assert not re.search(r"\d{4}-\d{2}-\d{2}", texto), arquivo
        arvore = ast.parse(texto)
        permitidos = {
            id(no.value)
            for no in ast.walk(arvore)
            if isinstance(no, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id in CONSTANTES_PERMITIDAS for t in no.targets)
        }
        for no in ast.walk(arvore):
            if arquivo.name == "__main__.py":
                continue
            if isinstance(no, ast.Constant) and type(no.value) is int and no.value not in (0, 1):
                assert id(no) in permitidos, f"{arquivo}:{no.lineno}"


def test_dispensa_por_qualidade_le_a_tabela_de_dispensas() -> None:
    """RF-VAL-03, RF-VAL-04. Preparo e mandato dispensados vêm da tabela própria de dispensas."""
    tabela = dispensas_padrao()
    assert set(tabela.dispensas) == {"fazenda_publica", "ministerio_publico", "defensoria_publica"}
    assert all(d.preparo and d.mandato for d in tabela.dispensas.values())
    modelo = modelo_de(
        criar_fato("tipo_recurso", "apelacao_civel"),
        criar_fato("qualidade_recorrente", "defensoria_publica"),
    )
    for regra in (validacoes_de("apelacao_civel")[1], validacoes_de("apelacao_civel")[2]):
        achado = regra.executar(modelo, date(2026, 11, 1))
        assert achado.resultado == "conforme"
        assert achado.valores["versao_dados"] == tabela.versao


def test_conflito_interrompe_a_regra_e_vira_verificar() -> None:
    """RF-FAT-02, RF-VAL-01. Conflito num fato opcional interrompe a regra e vira conferência."""
    modelo = modelo_de(
        criar_fato("tipo_recurso", "apelacao_civel"),
        criar_fato("qualidade_recorrente", "particular"),
        criar_fato("gratuidade_decisao", "deferida", fato_id=id_sintetico("gratuidade-deferida")),
        criar_fato(
            "gratuidade_decisao", "indeferida", fato_id=id_sintetico("gratuidade-indeferida")
        ),
    )
    coleta = Coleta(modelo, "teste", "base")
    with pytest.raises(FatoPendenteError) as erro:
        coleta.unico("gratuidade_decisao", obrigatorio=False)
    assert erro.value.coleta is coleta
    achado = validacoes_de("apelacao_civel")[1].executar(modelo, date(2026, 11, 1))
    assert achado.resultado == "verificar"
    assert [c["tipo"] for c in achado.valores["conflitos"]] == ["gratuidade_decisao"]
