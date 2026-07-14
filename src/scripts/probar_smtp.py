#!/usr/bin/env python3
"""
Diagnóstico SMTP para el Gestor de Asistencias.

Prueba, en orden:
  1) Conexión SSL/TLS al servidor SMTP (purelymail).
  2) Autenticación con EMAIL_HOST_USER / EMAIL_HOST_PASSWORD.
  3) Envío de un correo de prueba al destinatario indicado.

Lee la configuración primero de las variables de entorno (como hace el
contenedor Docker vía `env_file`) y, si no están, del archivo `.env` del
directorio actual (entorno local). No requiere Django ni dependencias
externas: solo stdlib, para poder correrlo en cualquier sitio.

Uso:
  python scripts/probar_smtp.py                 # envía a friveroll@gmail.com
  python scripts/probar_smtp.py alguien@x.com   # envía a otro destinatario

En el servidor (contenedor ya levantado):
  docker compose exec web python scripts/probar_smtp.py
"""

import os
import sys
import ssl
import smtplib
from email.message import EmailMessage

DEFAULT_TO = "friveroll@gmail.com"

# Claves que nos interesan del .env / entorno
_EMAIL_KEYS = (
    "EMAIL_HOST", "EMAIL_PORT", "EMAIL_USE_SSL",
    "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD", "DEFAULT_FROM_EMAIL",
)


def load_env_file(path=".env"):
    """Parser mínimo de un .env (KEY=VALUE), sin dependencias externas."""
    cfg = {}
    if not os.path.exists(path):
        return cfg
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


def get_config():
    """Variables de entorno primero (contenedor); si faltan, cae al .env local."""
    cfg = {k: os.environ.get(k) for k in _EMAIL_KEYS}
    if not cfg.get("EMAIL_HOST_USER"):
        file_cfg = load_env_file()
        for k in _EMAIL_KEYS:
            if not cfg.get(k) and file_cfg.get(k):
                cfg[k] = file_cfg[k]
    return cfg


def _mask(v):
    return "<VACÍO>" if not v else f"<definido, {len(v)} caracteres>"


def main():
    to = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TO
    cfg = get_config()

    host = cfg.get("EMAIL_HOST")
    port = int(cfg.get("EMAIL_PORT") or 465)
    use_ssl = str(cfg.get("EMAIL_USE_SSL", "True")).lower() in ("true", "1", "yes")
    user = cfg.get("EMAIL_HOST_USER") or ""
    pwd = cfg.get("EMAIL_HOST_PASSWORD") or ""
    frm = cfg.get("DEFAULT_FROM_EMAIL") or user

    print("=== Configuración SMTP detectada ===")
    print(f"  HOST     = {host}")
    print(f"  PORT     = {port}  (SSL={use_ssl})")
    print(f"  USER     = {_mask(user)}  {('(' + user[:25] + '...)') if user else ''}")
    print(f"  PASSWORD = {_mask(pwd)}")
    print(f"  FROM     = {frm or _mask(frm)}")
    print(f"  DESTINO  = {to}")
    print()

    if not (host and user and pwd):
        print("[FALLO] Faltan variables EMAIL_* (HOST_USER o PASSWORD están vacíos).")
        print("   Verifica el .env (local) o el env_file del contenedor (servidor).")
        sys.exit(1)

    # 1) Conexión + autenticación
    ctx = ssl.create_default_context()
    try:
        print(f"Conectando a {host}:{port} (SSL={use_ssl}) ...")
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=25, context=ctx)
        else:
            server = smtplib.SMTP(host, port, timeout=25)
            server.starttls(context=ctx)
        print("[OK] Conexión establecida.")
        server.login(user, pwd)
        print("[OK] Autenticación correcta.")
    except smtplib.SMTPAuthenticationError as e:
        detail = e.smtp_error.decode(errors="replace") if e.smtp_error else str(e)
        print(f"[FALLO] Autenticación rechazada (SMTP {e.smtp_code}): {detail}")
        print("   -> La contraseña SMTP es inválida o está caduca. "
              "Regénerala en el panel de Purelymail (contraseña SMTP/app).")
        sys.exit(2)
    except Exception as e:  # noqa: BLE001 - diagnóstico
        print(f"[FALLO] No se pudo conectar/autenticar: {type(e).__name__}: {e}")
        sys.exit(3)

    # 2) Envío del correo de prueba
    msg = EmailMessage()
    msg["Subject"] = "Prueba SMTP - Gestor de Asistencias"
    msg["From"] = frm
    msg["To"] = to
    msg.set_content(
        "Este es un correo de prueba del sistema Gestor de Asistencias.\n\n"
        "Si lo estás leyendo, la configuración SMTP funciona correctamente.\n"
        f"Enviado desde: {frm}\n"
    )

    try:
        server.send_message(msg)
        print(f"[OK] Correo de prueba enviado a {to}.")
    except Exception as e:  # noqa: BLE001 - diagnóstico
        print(f"[FALLO] Conexión OK, pero falló el envío: {type(e).__name__}: {e}")
        sys.exit(4)
    finally:
        server.quit()

    print("\n[OK] Diagnóstico SMTP completado. Revisa la bandeja (y spam) del destinatario.")


if __name__ == "__main__":
    main()
