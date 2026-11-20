"""Testes de `lupa_web.configuracao`: front sem banco, sessão nem administração (D4)."""

from django.conf import settings
from django.db import connections

APPS_DE_BANCO = (
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.admin",
    "django.contrib.contenttypes",
)


def test_lupa_web_nao_configura_banco() -> None:
    """RES-12 (D4): `DATABASES = {}` (o Django só põe o motor `dummy`) e nenhum app de banco."""
    motores = {apelido: banco["ENGINE"] for apelido, banco in connections.settings.items()}
    assert motores == {"default": "django.db.backends.dummy"}
    assert not set(APPS_DE_BANCO) & set(settings.INSTALLED_APPS)


def test_csrf_por_cookie_seguro_e_estrito() -> None:
    """RF-INT-03 (D4): CSRF no cookie `csrftoken`, `Secure` e `SameSite=Strict`, sem sessão."""
    assert settings.CSRF_USE_SESSIONS is False
    assert settings.CSRF_COOKIE_SECURE is True
    assert settings.CSRF_COOKIE_SAMESITE == "Strict"


def test_referrer_policy_same_origin_mantem_a_origem_nos_formularios() -> None:
    """RF-INT-03 (D18): `same-origin`, para o POST de formulário levar a origem real ao CSRF."""
    assert settings.SECURE_REFERRER_POLICY == "same-origin"


def test_estaticos_pelo_whitenoise_com_hash_no_nome() -> None:
    """RNF-08 (D12): estáticos pelo WhiteNoise com `CompressedManifestStaticFilesStorage`."""
    assert "whitenoise.middleware.WhiteNoiseMiddleware" in settings.MIDDLEWARE
    backend = settings.STORAGES["staticfiles"]["BACKEND"]
    assert backend == "whitenoise.storage.CompressedManifestStaticFilesStorage"


def test_envio_vai_para_arquivo_temporario_no_volume_dos_pendentes() -> None:
    """RF-INT-04 (D14, D16): upload só em arquivo temporário, no volume `envios-pendentes`."""
    assert settings.FILE_UPLOAD_HANDLERS == [
        "django.core.files.uploadhandler.TemporaryFileUploadHandler"
    ]
    assert settings.FILE_UPLOAD_TEMP_DIR == "/var/lupa/envios-pendentes"
