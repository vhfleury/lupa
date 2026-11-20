"""Telas de acesso: login com TOTP, MFA com QR, troca de senha e logout (A1, A3, D3, D11)."""

import json

import respx
from django.test import Client

from lupa_web import cliente_api
from tests.telas.conftest import sessao_da_api

URI_SINTETICA = "otpauth://totp/Lupa:assessor.sintetico?secret=JBSWY3DPEHPK3PXP&issuer=Lupa"
COOKIE_NOVO = "sessao-sintetica-nova"
RECUSA = "Não foi possível entrar com os dados informados."


def _corpo(rota: respx.Route) -> dict[str, object]:
    resultado: dict[str, object] = json.loads(rota.calls.last.request.content)
    return resultado


def test_login_mostra_formulario_de_usuario_e_senha() -> None:
    """RF-INT-02 (A3): `/login` mostra o primeiro passo com o token CSRF."""
    resposta = Client().get("/login")
    html = resposta.content.decode()
    assert resposta.status_code == 200
    assert "Bem-vindo ao Lupa" in html
    assert 'name="nome_usuario"' in html
    assert "csrfmiddlewaretoken" in html


def test_senha_aceita_pede_o_codigo_do_autenticador(api_simulada: respx.MockRouter) -> None:
    """RF-INT-02 (A3.1): a senha aceita leva ao pedido do código TOTP com o desafio."""
    rota = api_simulada.post("/auth/login").respond(
        200, json={"etapa": "mfa", "desafio": "desafio-sintetico"}
    )
    resposta = Client().post("/login", {"nome_usuario": " assessor ", "senha": "senha-sintetica"})
    html = resposta.content.decode()
    assert _corpo(rota) == {"nome_usuario": "assessor", "senha": "senha-sintetica"}
    assert "Verificação em duas etapas" in html
    assert 'value="desafio-sintetico"' in html
    assert "senha-sintetica" not in html


def test_login_com_senha_errada_mostra_recusa_generica(api_simulada: respx.MockRouter) -> None:
    """RF-INT-02 (A3.3): senha recusada mostra a recusa sem dizer o campo."""
    api_simulada.post("/auth/login").respond(401, json={"detail": "usuário ou senha inválidos"})
    resposta = Client().post("/login", {"nome_usuario": "assessor", "senha": "errada"})
    html = resposta.content.decode()
    assert resposta.status_code == 401
    assert RECUSA in html
    assert "senha inválidos" not in html


def test_login_com_codigo_errado_mostra_recusa_generica(api_simulada: respx.MockRouter) -> None:
    """RF-INT-02 (A3.3): código TOTP recusado mostra a mesma recusa, sem dizer o campo."""
    api_simulada.post("/auth/mfa").respond(401, json={"detail": "código inválido"})
    resposta = Client().post(
        "/login/codigo", {"etapa": "mfa", "desafio": "desafio-sintetico", "codigo": "123456"}
    )
    html = resposta.content.decode()
    assert resposta.status_code == 401
    assert RECUSA in html
    assert "código inválido" not in html
    assert 'value="desafio-sintetico"' in html
    assert "123456" not in html


def test_login_bloqueado_mostra_aviso_de_tentativas(api_simulada: respx.MockRouter) -> None:
    """RF-INT-03 (A3.3): o bloqueio por tentativas aparece com status 429."""
    api_simulada.post("/auth/login").respond(429, json={"detail": "muitas tentativas"})
    resposta = Client().post("/login", {"nome_usuario": "assessor", "senha": "x"})
    assert resposta.status_code == 429
    assert "Muitas tentativas." in resposta.content.decode()


def test_configuracao_de_mfa_mostra_qr_em_svg(api_simulada: respx.MockRouter) -> None:
    """RF-INT-02 (D11): MFA sem autenticador mostra o QR em SVG do `segno` e a chave."""
    api_simulada.post("/auth/login").respond(
        200,
        json={
            "etapa": "configurar_mfa",
            "desafio": "desafio-sintetico",
            "segredo": "JBSWY3DPEHPK3PXP",
            "uri_qr": URI_SINTETICA,
        },
    )
    resposta = Client().post("/login", {"nome_usuario": "assessor", "senha": "x"})
    html = resposta.content.decode()
    assert "Cadastre o autenticador" in html
    assert "<svg" in html
    assert 'class="segno"' in html
    assert "style=" not in html
    assert "JBSWY3DPEHPK3PXP" in html
    assert 'action="/login/codigo"' in html
    assert 'value="configurar_mfa"' in html


def test_confirmacao_do_autenticador_cria_sessao_e_vai_aos_processos(
    api_simulada: respx.MockRouter,
) -> None:
    """RF-INT-02 (A3.4, A3.2): o código confirma o MFA, o cookie volta e vai a `/processos`."""
    rota = api_simulada.post("/auth/mfa/confirmar").respond(
        200,
        json={"troca_senha_obrigatoria": False},
        headers={"set-cookie": f"lupa_sessao={COOKIE_NOVO}; HttpOnly; Path=/; Secure"},
    )
    resposta = Client().post(
        "/login/codigo",
        {"etapa": "configurar_mfa", "desafio": "d", "codigo": " 654321 "},
    )
    assert _corpo(rota) == {"desafio": "d", "codigo": "654321"}
    assert resposta.status_code == 303
    assert resposta["Location"] == "/processos"
    assert resposta.cookies[cliente_api.NOME_COOKIE].value == COOKIE_NOVO


def test_codigo_aceito_com_troca_obrigatoria_vai_a_troca_de_senha(
    api_simulada: respx.MockRouter,
) -> None:
    """RF-INT-03 (A1.7): com senha temporária, o login termina na troca de senha."""
    api_simulada.post("/auth/mfa").respond(200, json={"troca_senha_obrigatoria": True})
    resposta = Client().post("/login/codigo", {"etapa": "mfa", "desafio": "d", "codigo": "1"})
    assert resposta.status_code == 303
    assert resposta["Location"] == "/trocar-senha"


def test_sessao_expirada_redireciona_para_login(
    api_simulada: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-03 (A1.5): tela autenticada com 401 da API vira 303 para `/login`."""
    api_simulada.get("/auth/sessao").respond(401)
    resposta = navegador.get("/trocar-senha")
    assert resposta.status_code == 303
    assert resposta["Location"] == "/login"


def test_pedido_htmx_com_sessao_expirada_recebe_hx_redirect(
    api_simulada: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-03 (A1.5): em pedido HTMX o 401 vira `HX-Redirect: /login`."""
    api_simulada.get("/auth/sessao").respond(401)
    resposta = navegador.get("/trocar-senha", HTTP_HX_REQUEST="true")
    assert resposta.status_code == 200
    assert resposta["HX-Redirect"] == "/login"


def test_troca_obrigatoria_vem_antes_de_qualquer_tela(
    api_simulada: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-03 (A1.7): com troca pendente, a tela autenticada redireciona à troca."""
    api_simulada.get("/auth/sessao").respond(200, json=sessao_da_api(troca=True))
    resposta = navegador.get("/")
    assert resposta.status_code == 303
    assert resposta["Location"] == "/trocar-senha"


def test_troca_de_senha_mostra_aviso_quando_obrigatoria(
    api_simulada: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-03: a troca obrigatória explica por que o usuário está ali, sem o menu."""
    api_simulada.get("/auth/sessao").respond(200, json=sessao_da_api(troca=True))
    html = navegador.get("/trocar-senha").content.decode()
    assert "Antes de continuar, defina uma senha pessoal" in html
    assert 'aria-label="Menu principal"' not in html


def test_troca_de_senha_confere_a_confirmacao_sem_chamar_a_api(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-03: nova senha e confirmação diferentes são recusadas antes da API."""
    rota = logado.post("/auth/trocar-senha")
    resposta = navegador.post(
        "/trocar-senha",
        {"senha_atual": "a", "nova_senha": "frase-longa-um", "confirmacao": "frase-longa-dois"},
    )
    assert resposta.status_code == 422
    assert "A confirmação não confere com a nova senha." in resposta.content.decode()
    assert not rota.called


def test_troca_de_senha_aceita_vai_aos_processos(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-03: a troca aceita pela API leva a `/processos`."""
    rota = logado.post("/auth/trocar-senha").respond(204)
    resposta = navegador.post(
        "/trocar-senha",
        {"senha_atual": "a", "nova_senha": "frase-longa", "confirmacao": "frase-longa"},
    )
    assert _corpo(rota) == {"senha_atual": "a", "nova_senha": "frase-longa"}
    assert resposta.status_code == 303
    assert resposta["Location"] == "/processos"


def test_troca_com_senha_atual_errada_fica_no_formulario(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-03: o 401 da senha atual não encerra a sessão; vira mensagem no formulário."""
    logado.post("/auth/trocar-senha").respond(401, json={"detail": "senha atual inválida"})
    resposta = navegador.post(
        "/trocar-senha", {"senha_atual": "a", "nova_senha": "b" * 12, "confirmacao": "b" * 12}
    )
    assert resposta.status_code == 401
    assert "Senha atual incorreta." in resposta.content.decode()


def test_troca_com_sessao_expirada_vai_ao_login(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-03 (A1.5): outro 401 na troca é sessão expirada e vai a `/login`."""
    logado.post("/auth/trocar-senha").respond(401, json={"detail": "sessão expirada"})
    resposta = navegador.post(
        "/trocar-senha", {"senha_atual": "a", "nova_senha": "b" * 12, "confirmacao": "b" * 12}
    )
    assert resposta.status_code == 303
    assert resposta["Location"] == "/login"


def test_troca_com_senha_fraca_mostra_a_mensagem_da_api(
    logado: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-03 (A1.8): 422 da API aparece no formulário com o mesmo status."""
    logado.post("/auth/trocar-senha").respond(422, json={"detail": "senha muito comum"})
    resposta = navegador.post(
        "/trocar-senha", {"senha_atual": "a", "nova_senha": "b" * 12, "confirmacao": "b" * 12}
    )
    assert resposta.status_code == 422
    assert "Senha muito comum." in resposta.content.decode()


def test_logout_revoga_na_api_e_volta_ao_login(
    api_simulada: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-03 (D3): sair chama a API, copia o cookie apagado e vai a `/login`."""
    rota = api_simulada.post("/auth/logout").respond(
        204, headers={"set-cookie": "lupa_sessao=; Max-Age=0; Path=/"}
    )
    resposta = navegador.post("/sair")
    assert rota.called
    assert resposta.status_code == 303
    assert resposta["Location"] == "/login"
    assert resposta.cookies[cliente_api.NOME_COOKIE]["max-age"] == "0"


def test_raiz_leva_aos_processos(logado: respx.MockRouter, navegador: Client) -> None:
    """RF-INT-02 (A3.2): a raiz, com sessão válida, leva à lista de processos."""
    resposta = navegador.get("/")
    assert resposta.status_code == 303
    assert resposta["Location"] == "/processos"


def test_cabecalho_mostra_usuario_papel_e_sair(
    api_simulada: respx.MockRouter, navegador: Client
) -> None:
    """RF-INT-02: a moldura mostra usuário, papel, o menu do papel e o botão Sair."""
    api_simulada.get("/auth/sessao").respond(200, json=sessao_da_api("desembargador"))
    html = navegador.get("/trocar-senha").content.decode()
    assert "desembargador.sintetico" in html
    assert "Desembargador" in html
    assert 'action="/sair"' in html
    assert 'href="/auditoria"' in html
    assert 'href="/usuarios"' in html
