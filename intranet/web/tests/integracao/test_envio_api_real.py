"""Envio de PDF sintético pelo front à API real do compose (RF-INT-04, A4, D16).

Exige um assessor recém-criado em `LUPA_WEB_TESTE_USUARIO` e `LUPA_WEB_TESTE_SENHA` (o
`scripts/verificar.sh` cria um com `e2e_processos.py`). O PDF não traz número nem classe: o
cadastro passa pelo complemento com o arquivo guardado no volume de pendentes.
"""

import base64
import hashlib
import hmac
import os
import re
import secrets
import struct
import time

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

pytestmark = pytest.mark.integracao

PASSO_TOTP = 30
DIGITOS_TOTP = 6
MODULO_CNJ = 97


def _credenciais() -> tuple[str, str]:
    usuario = os.environ.get("LUPA_WEB_TESTE_USUARIO", "")
    senha = os.environ.get("LUPA_WEB_TESTE_SENHA", "")
    if usuario and senha:
        return usuario, senha
    motivo = "sem LUPA_WEB_TESTE_USUARIO e LUPA_WEB_TESTE_SENHA"
    if os.environ.get("LUPA_EXIGIR_INTEGRACAO") == "1":
        pytest.fail(motivo, pytrace=False)
    pytest.skip(motivo)


def _totp(segredo: str) -> str:
    chave = base64.b32decode(segredo + "=" * (-len(segredo) % 8))
    contador = struct.pack(">Q", int(time.time()) // PASSO_TOTP)
    resumo = hmac.new(chave, contador, hashlib.sha1).digest()
    deslocamento = resumo[-1] & 0x0F
    valor = struct.unpack(">I", resumo[deslocamento : deslocamento + 4])[0] & 0x7FFFFFFF
    return str(valor % 10**DIGITOS_TOTP).zfill(DIGITOS_TOTP)


def _numero_cnj() -> str:
    sequencial = f"{secrets.randbelow(10**7):07d}"
    ano, segmento, tribunal, origem = "2026", "8", "07", "0001"
    resto = int(f"{sequencial}{ano}{segmento}{tribunal}{origem}00") % MODULO_CNJ
    return f"{sequencial}-{98 - resto:02d}.{ano}.{segmento}.{tribunal}.{origem}"


def _pdf_sintetico() -> bytes:
    texto = b"BT /F1 12 Tf 72 720 Td (Documento sintetico de teste) Tj ET"
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(texto), texto),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    corpo = b"%PDF-1.4\n"
    posicoes = []
    for numero, objeto in enumerate(objetos, start=1):
        posicoes.append(len(corpo))
        corpo += b"%d 0 obj\n%s\nendobj\n" % (numero, objeto)
    xref = len(corpo)
    corpo += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    corpo += b"".join(b"%010d 00000 n \n" % posicao for posicao in posicoes)
    corpo += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objetos) + 1,
        xref,
    )
    return corpo


def _campo(html: str, nome: str) -> str:
    achado = re.search(rf'name="{nome}" value="([^"]*)"', html)
    assert achado is not None, nome
    return achado.group(1).replace("&amp;", "&")


def _entrar(navegador: Client, usuario: str, senha: str) -> None:
    html = navegador.post("/login", {"nome_usuario": usuario, "senha": senha}).content.decode()
    campos = {nome: _campo(html, nome) for nome in ("etapa", "desafio", "segredo", "uri_qr")}
    resposta = navegador.post("/login/codigo", campos | {"codigo": _totp(campos["segredo"])})
    assert resposta.status_code == 303
    assert resposta["Location"] == "/trocar-senha"
    nova = f"frase-sintetica-{secrets.token_hex(8)}"
    resposta = navegador.post(
        "/trocar-senha", {"senha_atual": senha, "nova_senha": nova, "confirmacao": nova}
    )
    assert resposta.status_code == 303


def test_envio_de_pdf_sintetico_cria_processo_pela_api() -> None:
    """RF-INT-04: PDF sem identificação, complemento com número e classe, processo criado."""
    usuario, senha = _credenciais()
    navegador = Client()
    _entrar(navegador, usuario, senha)

    arquivo = SimpleUploadedFile("sintetico.pdf", _pdf_sintetico(), "application/pdf")
    html = navegador.post(
        "/processos/envio", {"arquivo": arquivo}, HTTP_HX_REQUEST="true"
    ).content.decode()
    assert "Complete a identificação do processo" in html, html
    numero = _numero_cnj()
    resposta = navegador.post(
        "/processos/envio/complemento",
        {"codigo": _campo(html, "codigo"), "numero_cnj": numero, "classe": "apelacao_civel"},
        HTTP_HX_REQUEST="true",
    )
    destino = resposta["HX-Redirect"]
    assert re.fullmatch(r"/processos/[0-9a-f]{64}\?aviso=criado", destino)
    assert numero in navegador.get(destino).content.decode()
