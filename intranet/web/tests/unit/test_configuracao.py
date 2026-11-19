"""Testes de `lupa_web.configuracao`: front sem banco, sessão nem administração (D4)."""

from django.conf import settings

APPS_DE_BANCO = (
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.admin",
    "django.contrib.contenttypes",
)


def test_lupa_web_nao_configura_banco() -> None:
    """RES-12 (D4): `DATABASES = {}` (o Django só põe o motor `dummy`) e nenhum app de banco."""
    motores = {apelido: banco["ENGINE"] for apelido, banco in settings.DATABASES.items()}
    assert motores == {"default": "django.db.backends.dummy"}
    assert not set(APPS_DE_BANCO) & set(settings.INSTALLED_APPS)


def test_csrf_por_cookie_seguro_e_estrito() -> None:
    """RF-INT-03 (D4): CSRF no cookie `csrftoken`, `Secure` e `SameSite=Strict`, sem sessão."""
    assert settings.CSRF_USE_SESSIONS is False
    assert settings.CSRF_COOKIE_SECURE is True
    assert settings.CSRF_COOKIE_SAMESITE == "Strict"


def test_estaticos_pelo_whitenoise_com_hash_no_nome() -> None:
    """RNF-08 (D12): estáticos pelo WhiteNoise com `CompressedManifestStaticFilesStorage`."""
    assert "whitenoise.middleware.WhiteNoiseMiddleware" in settings.MIDDLEWARE
    backend = settings.STORAGES["staticfiles"]["BACKEND"]
    assert backend == "whitenoise.storage.CompressedManifestStaticFilesStorage"
