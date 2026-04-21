"""
sentry_config.py — Monitoreo de errores en producción
Integra Sentry para capturar errores automáticamente y notificarlos.
"""
import os, sys, traceback, smtplib
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
ENVIRONMENT = os.environ.get("APP_ENV", "production")
EMAIL_CESAR = os.environ.get("EMAIL_CESAR", "hola@kraftdo.cl")

_sentry_ok = False

def init_sentry():
    """Inicializa Sentry si hay DSN configurado. No bloquea si falla."""
    global _sentry_ok
    if not SENTRY_DSN:
        print("⚠️  SENTRY_DSN no configurado — usando fallback de email")
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.redis import RedisIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=ENVIRONMENT,
            traces_sample_rate=0.1,   # 10% de las requests
            profiles_sample_rate=0.1,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                RedisIntegration(),
            ],
            before_send=_filtrar_evento,
        )
        _sentry_ok = True
        print(f"✅ Sentry activo — entorno: {ENVIRONMENT}")
        return True
    except ImportError:
        print("⚠️  sentry-sdk no instalado")
        return False
    except Exception as e:
        print(f"⚠️  Sentry no se pudo inicializar: {e}")
        return False


def _filtrar_evento(event, hint):
    """Filtra eventos antes de enviarlos a Sentry (evita logs sensibles)."""
    # No mandar requests con datos de upload (Excel del cliente)
    if "request" in event:
        if event["request"].get("url", "").endswith("/subir"):
            event["request"]["data"] = "[FILTRADO]"
    return event


def capturar_error(exc: Exception, contexto: dict = None):
    """Captura un error — a Sentry si está disponible, si no a email."""
    if _sentry_ok:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            if contexto:
                for k, v in contexto.items():
                    scope.set_extra(k, v)
            sentry_sdk.capture_exception(exc)
    else:
        # Fallback: email directo a César
        _enviar_email_error(exc, contexto)


def _enviar_email_error(exc: Exception, contexto: dict = None):
    """Envía un email con el traceback si falla Sentry."""
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    if not smtp_user or not smtp_pass:
        return

    try:
        tb  = traceback.format_exception(type(exc), exc, exc.__traceback__)
        cx  = "\n".join(f"  {k}: {v}" for k, v in (contexto or {}).items())
        msg = MIMEText(f"""Error en KraftDo Sistema — {datetime.now()}

Tipo: {type(exc).__name__}
Mensaje: {exc}

Contexto:
{cx}

Traceback:
{''.join(tb)}
""")
        msg["Subject"] = f"🚨 Error en {ENVIRONMENT} — {type(exc).__name__}"
        msg["From"] = smtp_user
        msg["To"] = EMAIL_CESAR

        with smtplib.SMTP(os.environ.get("SMTP_HOST","smtp.gmail.com"), 587) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, EMAIL_CESAR, msg.as_string())
    except Exception:
        pass  # Nunca romper la app porque falló el log del error


# Inicializar automáticamente al importar — idempotente
_initialized = False
def _ensure_init():
    global _initialized
    if not _initialized:
        init_sentry()
        _initialized = True

_ensure_init()
