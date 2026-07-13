# asistencias/settings_test.py
"""Settings para correr la suite de tests sobre SQLite en memoria.

Permite verificar la lógica de la app sin levantar PostgreSQL ni definir .env.
NO usar en producción.
"""
import os

os.environ.setdefault("SECRET_KEY", "django-test-secret-key-for-tests-only-9f3a7c2e")

from .settings import *  # noqa: F401,F403,E402

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "test@test.test"

# Hasher rápido para acelerar la creación de usuarios en tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Las migraciones de `core` contienen SQL específico de PostgreSQL; en tests
# creamos las tablas directamente desde los modelos (run_syncdb).
MIGRATION_MODULES = {"core": None}
