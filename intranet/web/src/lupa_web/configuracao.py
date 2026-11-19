"""Configuração do Django do front: sem banco, sem sessão própria, CSRF por cookie (D4).

O front não guarda estado: a sessão é o cookie da API (D3) e todos os dados vêm de
`LUPA_WEB_API_URL` (D2). Os estáticos saem do WhiteNoise com hash no nome (D12).
"""

import os
from pathlib import Path

from django.core.management.utils import get_random_secret_key

PASTA_PACOTE = Path(__file__).resolve().parent

SECRET_KEY = os.environ.get("LUPA_WEB_CHAVE_SECRETA") or get_random_secret_key()
DEBUG = False
ALLOWED_HOSTS = os.environ.get("LUPA_WEB_HOSTS", "localhost,127.0.0.1,proxy,front").split(",")

INSTALLED_APPS = ["django.contrib.staticfiles", "lupa_web"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "lupa_web.urls"
ASGI_APPLICATION = "lupa_web.asgi.application"

DATABASES: dict[str, dict[str, str]] = {}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.csrf"]},
    }
]

CSRF_USE_SESSIONS = False
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REFERRER_POLICY = "no-referrer"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

STATIC_URL = "/static/"
STATIC_ROOT = os.environ.get("LUPA_WEB_ESTATICOS", str(PASTA_PACOTE.parents[1] / "estaticos"))
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = False
USE_TZ = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"nivel": "%(levelname)s", "logger": "%(name)s", "evento": "%(message)s"}',
        }
    },
    "handlers": {"saida": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["saida"], "level": "INFO"},
}
