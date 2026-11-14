"""Testes do sandbox de parsing e do parser de PDF executado dentro dele."""

import json
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from apoio_arquivos import (
    pdf_assinado,
    pdf_bomba,
    pdf_com_senha,
    pdf_corrompido,
    pdf_minimo,
    pdf_truncado,
    zip_de,
)
from lupa_pipeline.dominio.enums import MotivoFalha, MotivoQuarentena
from lupa_pipeline.ingestao import parser_pdf, sandbox
from lupa_pipeline.ingestao.inventario import LimitesZip, ZipRecusadoError
from lupa_pipeline.ingestao.sandbox import LimitesSandbox, ResultadoSandbox, inspecionar_pdf

LIMITES = LimitesSandbox(memoria_mb=512, cpu_segundos=20, tempo_segundos=30)


@pytest.mark.parametrize(
    ("dados", "motivo"),
    [
        (b"MZ executavel", "tipo_invalido"),
        (pdf_truncado(), "truncado"),
        (pdf_assinado(cobre_tudo=False), "assinatura_invalida"),
        (pdf_corrompido(), "corrompido"),
        (pdf_com_senha(), "senha"),
    ],
)
def test_parser_classifica_cada_defeito(dados: bytes, motivo: str) -> None:
    """Cada defeito estrutural vira o motivo de quarentena correspondente."""
    assert parser_pdf.inspecionar(dados) == {"ok": False, "motivo_quarentena": motivo}


def test_parser_aceita_pdf_valido_e_assinatura_que_cobre_o_arquivo() -> None:
    """PDF íntegro devolve páginas; `/ByteRange` cobrindo o arquivo todo é aceito."""
    resultado = parser_pdf.inspecionar(pdf_minimo(2))
    assert resultado["ok"] is True
    assert resultado["paginas"] == 2
    assert parser_pdf.motivo_estrutural(pdf_assinado(cobre_tudo=True)) is None


def test_parser_sem_paginas_e_corrompido() -> None:
    """Documento que abre mas não tem páginas vai para quarentena."""
    vazio = b"%PDF-1.7\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"
    assert parser_pdf.inspecionar(vazio)["motivo_quarentena"] == "corrompido"


def test_falta_de_memoria_reconhecida_por_tipo_e_texto() -> None:
    """Erros de sistema do MuPDF e mensagens de memória contam como falta de memória."""
    erro_sistema = type("FzErrorSystem", (Exception,), {})()
    assert parser_pdf._falta_memoria(erro_sistema)
    assert parser_pdf._falta_memoria(RuntimeError("malloc failed"))
    assert not parser_pdf._falta_memoria(RuntimeError("syntax error"))


def test_main_escreve_json_e_sai_com_codigo_de_memoria(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`main` escreve um único objeto JSON; MemoryError vira `EXIT_MEMORIA`."""
    import socket

    original = socket.socket, socket.create_connection
    caminho = tmp_path / "a.pdf"
    caminho.write_bytes(pdf_minimo())
    try:
        parser_pdf.main([str(caminho)])
        assert json.loads(capsys.readouterr().out)["paginas"] == 1

        def _estourar(_dados: bytes) -> dict[str, object]:
            raise MemoryError

        monkeypatch.setattr(parser_pdf, "inspecionar", _estourar)
        with pytest.raises(SystemExit) as saida:
            parser_pdf.main([str(caminho)])
        assert saida.value.code == parser_pdf.EXIT_MEMORIA
    finally:
        socket.socket, socket.create_connection = original  # type: ignore[misc]


def test_filho_nao_cria_sockets() -> None:
    """Depois de `bloquear_rede`, criar socket no processo filho falha."""
    codigo = (
        "from lupa_pipeline.ingestao.parser_pdf import bloquear_rede; bloquear_rede(); "
        "import socket; socket.socket()"
    )
    processo = subprocess.run(  # noqa: S603
        [sys.executable, "-c", codigo], capture_output=True, text=True, check=False
    )
    assert processo.returncode != 0
    assert "rede desabilitada" in processo.stderr


def test_ambiente_do_filho_nao_tem_variaveis_do_lupa(monkeypatch: pytest.MonkeyPatch) -> None:
    """O filho não recebe URL do banco nem credenciais."""
    monkeypatch.setenv("LUPA_DATABASE_URL", "postgresql://segredo")
    ambiente = sandbox._ambiente_minimo("/tmp/x")  # noqa: S108
    assert not any(chave.startswith("LUPA_") for chave in ambiente)
    assert set(ambiente) == {"PATH", "HOME", "LANG", "TMPDIR"}


def test_pdf_valido_no_sandbox(tmp_path: Path) -> None:
    """Execução real no subprocesso devolve o JSON do parser."""
    caminho = tmp_path / "a.pdf"
    caminho.write_bytes(pdf_minimo(2))
    resultado = inspecionar_pdf(caminho, LIMITES)
    assert resultado.ok
    assert resultado.dados["paginas"] == 2


def test_stream_descomprimido_gigante_e_morto_pelo_limite_de_memoria(tmp_path: Path) -> None:
    """768 MB descomprimidos com 512 MB de limite: o filho morre e o motivo é memória."""
    caminho = tmp_path / "bomba.pdf"
    pdf_bomba(caminho, 768)
    assert caminho.stat().st_size < 2 * 1024 * 1024
    resultado = inspecionar_pdf(caminho, LIMITES)
    assert not resultado.ok
    assert resultado.motivo_falha is MotivoFalha.LIMITE_MEMORIA


def test_tempo_esgotado(tmp_path: Path) -> None:
    """Tempo de parede curto demais termina em `tempo_esgotado`."""
    caminho = tmp_path / "a.pdf"
    caminho.write_bytes(pdf_minimo())
    resultado = inspecionar_pdf(caminho, LimitesSandbox(512, 20, 0.001))
    assert resultado.motivo_falha is MotivoFalha.TEMPO_ESGOTADO


def test_erro_do_filho_vira_erro_parser(tmp_path: Path) -> None:
    """Arquivo inexistente: o filho termina com erro e nada de JSON."""
    resultado = inspecionar_pdf(tmp_path / "nao-existe.pdf", LIMITES)
    assert resultado == ResultadoSandbox(motivo_falha=MotivoFalha.ERRO_PARSER)


def test_codigos_de_saida_mapeados() -> None:
    """Sinal de CPU e código de memória têm motivos próprios."""
    assert sandbox._motivo_por_codigo(-signal.SIGXCPU) is MotivoFalha.LIMITE_CPU
    assert sandbox._motivo_por_codigo(-signal.SIGKILL) is MotivoFalha.LIMITE_CPU
    assert sandbox._motivo_por_codigo(parser_pdf.EXIT_MEMORIA) is MotivoFalha.LIMITE_MEMORIA
    assert sandbox._motivo_por_codigo(1) is MotivoFalha.ERRO_PARSER


def test_saida_que_nao_e_objeto_json_vira_erro_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    """Saída ilegível ou JSON que não é objeto não é aceita."""
    for saida in (b"nao-json", b"[1, 2]"):
        concluido = subprocess.CompletedProcess(args=[], returncode=0, stdout=saida, stderr=b"")
        monkeypatch.setattr(subprocess, "run", lambda *_a, c=concluido, **_k: c)
        assert sandbox.executar("x", [], LIMITES).motivo_falha is MotivoFalha.ERRO_PARSER


@pytest.mark.parametrize("escrita", [0, 4096])
def test_limites_aplicados_no_filho(escrita: int) -> None:
    """O preexec define os rlimits pedidos (conferido num filho real)."""
    codigo = (
        "import resource; print(resource.getrlimit(resource.RLIMIT_AS)[0], "
        "resource.getrlimit(resource.RLIMIT_CPU)[0], resource.getrlimit(resource.RLIMIT_FSIZE)[0])"
    )
    processo = subprocess.run(  # noqa: S603
        [sys.executable, "-c", codigo],
        capture_output=True,
        text=True,
        check=True,
        preexec_fn=sandbox._aplicar_limites(LimitesSandbox(300, 7, 1), escrita),  # noqa: PLW1509
    )
    assert processo.stdout.split() == [str(300 * 1024 * 1024), "7", str(escrita)]


def test_erro_ao_decodificar_pagina(monkeypatch: pytest.MonkeyPatch) -> None:
    """Erro comum vira `corrompido`; erro de memória sobe como MemoryError."""
    import fitz

    def _quebrar(_pagina: object) -> bytes:
        raise RuntimeError("syntax error in content stream")

    monkeypatch.setattr(fitz.Page, "read_contents", _quebrar)
    assert parser_pdf.inspecionar(pdf_minimo())["motivo_quarentena"] == "corrompido"

    def _sem_memoria(_pagina: object) -> bytes:
        raise RuntimeError("malloc of 1 GB failed")

    monkeypatch.setattr(fitz.Page, "read_contents", _sem_memoria)
    with pytest.raises(MemoryError):
        parser_pdf.inspecionar(pdf_minimo())


def test_varios_pdfs_num_unico_filho(tmp_path: Path) -> None:
    """Entradas de ZIP são inspecionadas num filho só, na ordem recebida (4E.0)."""
    caminhos = []
    for n in (1, 3):
        caminho = tmp_path / f"{n}.pdf"
        caminho.write_bytes(pdf_minimo(n))
        caminhos.append(caminho)
    resultados = sandbox.inspecionar_pdfs(caminhos, LIMITES)
    assert [r.dados["paginas"] for r in resultados] == [1, 3]


def test_grupo_com_bomba_reinspeciona_cada_entrada(tmp_path: Path) -> None:
    """Falha do filho do grupo: cada entrada é reinspecionada e o motivo fica com a culpada."""
    boa = tmp_path / "boa.pdf"
    boa.write_bytes(pdf_minimo(2))
    bomba = tmp_path / "bomba.pdf"
    pdf_bomba(bomba, 768)
    resultados = sandbox.inspecionar_pdfs([boa, bomba], LIMITES)
    assert resultados[0].dados["paginas"] == 2
    assert resultados[1].motivo_falha is MotivoFalha.LIMITE_MEMORIA


def test_grupo_de_um_pdf_usa_a_inspecao_simples(tmp_path: Path) -> None:
    """Um caminho só devolve o resultado direto, sem envelope `itens`."""
    caminho = tmp_path / "a.pdf"
    caminho.write_bytes(pdf_minimo(1))
    assert sandbox.inspecionar_pdfs([caminho], LIMITES)[0].dados["paginas"] == 1


@pytest.mark.parametrize(
    "limites_zip",
    [LimitesZip(max_entradas=1), LimitesZip(max_razao=1.1), LimitesZip(max_descomprimido_bytes=70)],
)
def test_zip_recusado_no_filho_por_limites_globais(tmp_path: Path, limites_zip: LimitesZip) -> None:
    """Duas entradas pequenas juntas excedem o teto, ainda que cada uma caiba sozinha."""
    original = tmp_path / "autos.zip"
    original.write_bytes(zip_de({"1.pdf": b"x" * 40, "2.pdf": b"y" * 40}))
    with pytest.raises(ZipRecusadoError) as capturado:
        sandbox.inventariar_zip(original, tmp_path, limites_zip, LIMITES)
    assert capturado.value.motivo == MotivoQuarentena.ZIP_MALICIOSO
    assert list(tmp_path.iterdir()) == [original]


def test_esgotamento_no_subprocesso_zip_devolve_falha_tecnica(tmp_path: Path) -> None:
    """O timeout da descompactação deve ir para o motivo de falha do job."""
    original = tmp_path / "autos.zip"
    original.write_bytes(zip_de({"1.pdf": b"teste"}))
    with pytest.raises(sandbox.FalhaSandboxError) as erro:
        sandbox.inventariar_zip(original, tmp_path, LimitesZip(), LimitesSandbox(512, 20, 0.001))
    assert erro.value.motivo == MotivoFalha.TEMPO_ESGOTADO


@pytest.mark.parametrize("campo", ["caminho", "link", "ordem", "permissao", "tamanho"])
def test_manifesto_de_zip_nao_autoriza_arquivo_externo_ou_inconsistente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, campo: str
) -> None:
    """O pai reconstrói o nome conhecido e rejeita substituições por path ou link."""
    privado = tmp_path / "trabalho"
    privado.mkdir()
    original = tmp_path / "autos.zip"
    original.write_bytes(b"segredo-sintetico")
    destino = privado / "entrada-00001"
    if campo == "link":
        destino.symlink_to(original)
    else:
        destino.touch(mode=0o644 if campo == "permissao" else 0o600)
    item = {
        "nome": "1.pdf",
        "ordem": 2 if campo == "ordem" else 1,
        "tamanho_bytes": 99 if campo == "tamanho" else 0,
        "sha256": "1" * 64,
    }
    if campo == "caminho":
        item["caminho"] = str(original)
    monkeypatch.setattr(
        sandbox, "_executar", lambda *a, **kw: ResultadoSandbox({"entradas": [item]})
    )
    with pytest.raises(sandbox.FalhaSandboxError) as erro:
        sandbox.inventariar_zip(original, privado, LimitesZip(), LIMITES)
    assert erro.value.motivo == MotivoFalha.ERRO_PARSER
    assert original.read_bytes() == b"segredo-sintetico"
