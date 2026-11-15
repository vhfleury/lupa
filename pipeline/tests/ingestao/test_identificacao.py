"""Leitura isolada e identificação do processo antes do lacre (RF-PRO-01)."""

from pathlib import Path

import pytest

from apoio_arquivos import pdf_com_senha, pdf_minimo, zip_de
from apoio_comum import gerar_numero_cnj
from lupa_pipeline.config import Settings
from lupa_pipeline.dominio.chaves import normalizar_cnj
from lupa_pipeline.dominio.enums import ClasseProcessual, MotivoFalha, MotivoQuarentena
from lupa_pipeline.ingestao import sandbox
from lupa_pipeline.ingestao.extracao import MODULO_EXTRATOR
from lupa_pipeline.ingestao.identificacao import Leitura, LeituraRecusada, identificar, ler_capa
from lupa_pipeline.ingestao.recepcao import ArquivoRecebido, TipoArquivo
from lupa_pipeline.ingestao.sandbox import LimitesSandbox, ResultadoSandbox

A, B = gerar_numero_cnj(1), gerar_numero_cnj(2)
NA, NB = normalizar_cnj(A), normalizar_cnj(B)


@pytest.mark.parametrize(
    ("paginas", "numero", "encontrados"),
    [
        ([f"{A}\nAutos nº: {B}\nProcesso nº {A}"], NB, (NA, NB)),
        ([f"Referência {B}", f"Número do processo: {A}"], None, (NB, NA)),
        ([f"Citação {A} e {NA}"], NA, (NA,)),
        ([f"Apensos {A}, {NB}"], None, (NA, NB)),
        ([f"Autos nº {A.replace(A[8:10], '00')}"], None, ()),
        ([f"Autos nº {A.replace(A[8:10], '00')}\nApenso: {B}"], None, (NB,)),
        ([f"Apenso {A}  Processo nº: {B}"], NB, (NA, NB)),
        ([f"Processo nº:\n {A}\nApenso {B}"], NA, (NA, NB)),
        (["Sem número"], None, ()),
    ],
)
def test_identifica_numero_sem_escolher_entre_apensos(
    paginas: list[str], numero: str | None, encontrados: tuple[str, ...]
) -> None:
    """RF-PRO-01: o primeiro rótulo válido na página um prevalece sobre referências."""
    resultado = identificar(paginas)
    assert resultado.numeros_encontrados == encontrados
    assert resultado.numero_cnj == numero


@pytest.mark.parametrize(
    ("rotulo", "classe"),
    [
        ("Apelação cível", "apelacao_civel"),
        ("AGRAVO DE INSTRUMENTO", "agravo_instrumento"),
        ("embargos de declaracao", "embargos_declaracao"),
        ("Agravo interno", "agravo_interno"),
        ("Ação rescisória", "acao_originaria"),
        ("Mandado de segurança", "acao_originaria"),
        ("Reclamação", "acao_originaria"),
        ("Conflito de competência", "acao_originaria"),
        ("Apelação criminal", None),
        ("Classe inventada", None),
    ],
)
def test_classe_depende_do_rotulo_e_da_tabela(rotulo: str, classe: str | None) -> None:
    """RF-PRO-01: só uma classe integral da tabela depois de rótulo identifica os autos."""
    paginas = ["Interposta apelação cível.", f"Classe judicial: {rotulo}\nDistribuição: hoje"]
    assert identificar(paginas).classe == (ClasseProcessual(classe) if classe else None)


@pytest.mark.parametrize("zipado", [True, False])
def test_le_primeiro_pdf_ate_o_limite_de_paginas(
    tmp_path: Path, settings_ficticias: Settings, zipado: bool
) -> None:
    """RF-PRO-01: o primeiro PDF ordenado é inspecionado e a extração só lê o intervalo."""
    original = tmp_path / "original"
    pdf = pdf_minimo(4)
    original.write_bytes(zip_de({"02.pdf": b"invalido", "01.pdf": pdf}) if zipado else pdf)
    tipo = TipoArquivo.ZIP if zipado else TipoArquivo.PDF
    recebido = ArquivoRecebido(original, "a" * 64, original.stat().st_size, tipo)
    settings_ficticias.ingestao_dir_temporario = tmp_path

    def extrair(modulo: str, args: list[str], limites: LimitesSandbox) -> ResultadoSandbox:
        assert modulo == MODULO_EXTRATOR
        assert Path(args[0]).read_bytes() == pdf
        assert args[1:] == ["1", "3"]
        assert 0 < limites.tempo_segundos <= 30
        paginas = [{"numero": i, "texto_normalizado": str(i)} for i in range(1, 4)]
        return ResultadoSandbox({"ok": True, "paginas": paginas})

    assert ler_capa(recebido, settings_ficticias, executor=extrair) == Leitura(("1", "2", "3"))
    assert list(tmp_path.iterdir()) == [original]


@pytest.mark.parametrize(
    ("tipo", "dados", "motivo"),
    [
        (TipoArquivo.PDF, pdf_com_senha(), MotivoQuarentena.SENHA),
        (TipoArquivo.ZIP, zip_de({"../x": b"x"}), MotivoQuarentena.ZIP_MALICIOSO),
        (TipoArquivo.DESCONHECIDO, b"x", MotivoQuarentena.TIPO_INVALIDO),
    ],
    ids=["senha", "zip_malicioso", "tipo_invalido"],
)
def test_recusa_defeito_estrutural(
    tmp_path: Path,
    settings_ficticias: Settings,
    tipo: TipoArquivo,
    dados: bytes,
    motivo: MotivoQuarentena,
) -> None:
    """RF-ING-02: defeito do ZIP, PDF ou tipo desconhecido é recusa definitiva."""
    original = tmp_path / "original"
    original.write_bytes(dados)
    recebido = ArquivoRecebido(original, "a" * 64, len(dados), tipo)
    assert ler_capa(recebido, settings_ficticias) == LeituraRecusada(motivo)


def test_tempo_esgotado_na_extracao_permite_complemento(
    tmp_path: Path, settings_ficticias: Settings
) -> None:
    """RF-PRO-01: limite de recurso produz leitura vazia para o complemento."""
    original = tmp_path / "original"
    original.write_bytes(pdf_minimo())
    recebido = ArquivoRecebido(original, "b" * 64, original.stat().st_size, TipoArquivo.PDF)

    def esgotar(modulo: str, args: list[str], limites: LimitesSandbox) -> ResultadoSandbox:
        return ResultadoSandbox(motivo_falha=MotivoFalha.TEMPO_ESGOTADO)

    assert ler_capa(recebido, settings_ficticias, executor=esgotar) == Leitura(())


@pytest.mark.integracao
def test_extrator_da_identificacao_sem_rede_nem_credenciais(
    tmp_path: Path, settings_ficticias: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RF-ING-04: a tentativa no próprio filho comprova bloqueio de rede e ausência de segredo."""
    original = tmp_path / "original"
    original.write_bytes(pdf_minimo())
    recebido = ArquivoRecebido(original, "c" * 64, original.stat().st_size, TipoArquivo.PDF)
    monkeypatch.setenv("LUPA_CREDENCIAL_TESTE", "marcador")
    comando_original = sandbox._comando

    def comando(modulo: str, args: list[str]) -> list[str]:
        cmd = comando_original(modulo, args)
        if modulo == MODULO_EXTRATOR:
            sonda = (
                "import os, socket\n"
                "def extrair(*args):\n"
                "    assert 'LUPA_CREDENCIAL_TESTE' not in os.environ\n"
                "    try: socket.create_connection(('127.0.0.1', 9))\n"
                "    except PermissionError:\n"
                "        pagina = {'numero': 1, 'texto_normalizado': 'isolado'}\n"
                "        return {'ok': True, 'paginas': [pagina]}\n"
                "    raise AssertionError('rede habilitada')\n"
            )
            cmd[3] = cmd[3].replace(
                "main()",
                "exec("
                + repr(sonda)
                + "); main.__globals__['extrair_intervalo'] = extrair; main()",
            )
        return cmd

    monkeypatch.setattr(sandbox, "_comando", comando)
    assert ler_capa(recebido, settings_ficticias) == Leitura(("isolado",))
