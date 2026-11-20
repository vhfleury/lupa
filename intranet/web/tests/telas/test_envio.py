"""Cadastro de processo por arquivo: envio, limite, complemento e recusa (RF-INT-04, A4, D16)."""

import re
from pathlib import Path

import pytest
import respx
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

PDF = b"%PDF-1.4\n% sintetico\n" + b"0" * 64
PROCESSO = "e5" * 32
INCOMPLETA = {
    "detail": "Complete a identificação do processo.",
    "motivo": "identificacao_incompleta",
    "lido": {"numero_cnj": "0000004-89.2026.8.07.0001", "classe": None},
    "faltando": ["classe"],
    "numeros_encontrados": ["0000004-89.2026.8.07.0001"],
}
CRIADO = {"arquivo_id": "f6" * 32, "processo_id": PROCESSO, "duplicado": False}


@pytest.fixture(autouse=True)
def pasta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Volume de pendentes numa pasta temporária."""
    monkeypatch.setenv("LUPA_WEB_ENVIOS_PENDENTES", str(tmp_path))
    return tmp_path


def _arquivo(conteudo: bytes = PDF, nome: str = "autos.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(nome, conteudo, content_type="application/pdf")


def _enviar(navegador: Client, caminho: str = "/processos/envio", **dados: object) -> str:
    resposta = navegador.post(caminho, dados, HTTP_HX_REQUEST="true")
    assert resposta.status_code == 200
    return resposta.content.decode()


def test_pdf_sem_classe_pede_a_classe_e_reenvio_usa_o_mesmo_arquivo(
    logado: respx.MockRouter, navegador: Client, pasta: Path
) -> None:
    """RF-INT-04 (A4.4, A4.5, A4.8): falta a classe; o complemento reenvia o mesmo arquivo."""
    rota = logado.post("/processos/arquivos")
    rota.side_effect = [
        respx.MockResponse(422, json=INCOMPLETA),
        respx.MockResponse(201, json=CRIADO),
    ]
    html = _enviar(navegador, arquivo=_arquivo())
    assert "Complete a identificação do processo" in html
    assert 'name="classe"' in html
    assert "0000004-89.2026.8.07.0001" in html
    codigo = re.search(r'name="codigo" value="([0-9a-f]{64})"', html)
    assert codigo is not None
    assert rota.calls.last.request.url.params["nome"] == "autos.pdf"

    resposta = navegador.post(
        "/processos/envio/complemento",
        {
            "codigo": codigo.group(1),
            "numero_cnj": "0000004-89.2026.8.07.0001",
            "classe": "apelacao_civel",
        },
        HTTP_HX_REQUEST="true",
    )
    reenvio = rota.calls.last.request
    assert reenvio.content == PDF
    assert reenvio.url.params["classe"] == "apelacao_civel"
    assert reenvio.url.params["numero_cnj"] == "0000004-89.2026.8.07.0001"
    assert reenvio.url.params["nome"] == "autos.pdf"
    assert resposta["HX-Redirect"] == f"/processos/{PROCESSO}?aviso=recebido"
    assert list(pasta.iterdir()) == []


def test_arquivo_acima_do_limite_e_recusado_sem_chamar_api(
    logado: respx.MockRouter, navegador: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RF-INT-04 (A4.2): acima de `LUPA_WEB_TAMANHO_MAXIMO_ENVIO`, motivo e nenhuma chamada."""
    monkeypatch.setenv("LUPA_WEB_TAMANHO_MAXIMO_ENVIO", "10")
    rota = logado.post("/processos/arquivos")
    html = _enviar(navegador, arquivo=_arquivo())
    assert "O arquivo passa do limite de envio." in html
    assert not rota.called


def test_complemento_expirado_pede_o_arquivo_de_novo_sem_chamar_api(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-04 (A4.6): código inexistente ou de outra sessão não chega à API."""
    rota = logado.post("/processos/arquivos")
    html = _enviar(
        navegador,
        "/processos/envio/complemento",
        codigo="a" * 64,
        numero_cnj="0000004-89.2026.8.07.0001",
        classe="apelacao_civel",
    )
    assert "Envio expirado, selecione o arquivo de novo." in html
    assert not rota.called


def test_arquivo_recusado_mostra_o_motivo_e_apaga_o_pendente(
    logado: respx.MockRouter, navegador: Client, pasta: Path
) -> None:
    """RF-INT-04 (A4.7): a recusa da API aparece com o motivo, sem pendente guardado."""
    logado.post("/processos/arquivos").respond(
        422, json={"detail": "Arquivo recusado: senha", "motivo": "senha"}
    )
    html = _enviar(navegador, arquivo=_arquivo())
    assert "Arquivo recusado: senha." in html
    assert list(pasta.iterdir()) == []


def test_envio_sem_arquivo_ou_vazio_ou_de_outro_tipo_e_recusado_no_front(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-04: sem arquivo, vazio ou que não é PDF/ZIP: motivo sem chamar a API."""
    rota = logado.post("/processos/arquivos")
    assert "Escolha um arquivo PDF ou ZIP." in _enviar(navegador)
    assert "O arquivo está vazio." in _enviar(navegador, arquivo=_arquivo(b""))
    assert "Envie um arquivo PDF ou ZIP." in _enviar(navegador, arquivo=_arquivo(nome="a.txt"))
    assert not rota.called


def test_anexo_ao_processo_redireciona_para_ele(
    logado: respx.MockRouter, navegador: Client, pasta: Path
) -> None:
    """RF-INT-04 (A4.3, A4.8): o anexo vai a `POST /processos/<id>/arquivos` e volta ao processo."""
    rota = logado.post(f"/processos/{PROCESSO}/arquivos").respond(201, json=CRIADO)
    resposta = navegador.post(
        f"/processos/{PROCESSO}/envio", {"arquivo": _arquivo()}, HTTP_HX_REQUEST="true"
    )
    assert rota.calls.last.request.content == PDF
    assert resposta["HX-Redirect"] == f"/processos/{PROCESSO}?aviso=recebido"


@pytest.mark.parametrize(
    ("extra", "aviso"),
    [
        ({"processo_criado": True}, "criado"),
        ({"processo_criado": False}, "anexado"),
        ({"processo_criado": False, "duplicado": True}, "duplicado"),
    ],
)
def test_cadastro_avisa_criacao_anexo_ou_duplicata(
    logado: respx.MockRouter,
    navegador: Client,
    pasta: Path,
    extra: dict[str, bool],
    aviso: str,
) -> None:
    """RF-INT-04 (A4.8): o destino diz se o processo foi criado, anexado ou já tinha o arquivo."""
    logado.post("/processos/arquivos").respond(200, json=CRIADO | extra)
    resposta = navegador.post("/processos/envio", {"arquivo": _arquivo()}, HTTP_HX_REQUEST="true")
    assert resposta["HX-Redirect"] == f"/processos/{PROCESSO}?aviso={aviso}"


def test_complemento_que_a_api_ainda_recusa_mantem_o_pendente(
    logado: respx.MockRouter, navegador: Client, pasta: Path
) -> None:
    """RF-INT-04 (A4.4): número inválido no complemento volta ao formulário com o mesmo código."""
    rota = logado.post("/processos/arquivos")
    rota.side_effect = [
        respx.MockResponse(422, json=INCOMPLETA),
        respx.MockResponse(422, json={"detail": "número CNJ inválido"}),
    ]
    codigo = re.search(
        r'name="codigo" value="([0-9a-f]{64})"', _enviar(navegador, arquivo=_arquivo())
    )
    assert codigo is not None
    html = _enviar(
        navegador,
        "/processos/envio/complemento",
        codigo=codigo.group(1),
        numero_cnj="1",
        classe="apelacao_civel",
    )
    assert "Número CNJ inválido." in html
    assert codigo.group(1) in html
    assert len(list(pasta.glob(f"{codigo.group(1)}*"))) == 2


def test_falha_da_api_sem_json_mostra_mensagem_generica(
    logado: respx.MockRouter, navegador: Client, pasta: Path
) -> None:
    """RF-INT-04 (A1.8): erro da API sem corpo JSON vira a mensagem genérica, sem pendente."""
    logado.post("/processos/arquivos").respond(500, text="falha")
    assert "Algo deu errado. Tente novamente." in _enviar(navegador, arquivo=_arquivo())
    assert list(pasta.iterdir()) == []
