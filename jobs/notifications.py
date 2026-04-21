"""
notifications.py — Notificaciones multi-canal
Soporta: WhatsApp (Twilio), Email (SMTP), Telegram, Webhook genérico
"""
import os, json, smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False


def enviar_whatsapp(telefono: str, mensaje: str) -> dict:
    """Envía WhatsApp vía Twilio."""
    sid   = os.environ.get("TWILIO_SID", "")
    token = os.environ.get("TWILIO_TOKEN", "")
    from_ = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

    if not sid or not token:
        return {"ok": False, "error": "TWILIO_SID / TWILIO_TOKEN no configurados"}

    if not telefono.startswith("whatsapp:"):
        telefono = f"whatsapp:{telefono}"

    try:
        r = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={"From": from_, "To": telefono, "Body": mensaje},
            timeout=10,
        )
        return {"ok": r.status_code == 201, "status": r.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def enviar_email(destinatario: str, asunto: str, html: str, texto: str = None) -> dict:
    """Envía email por SMTP."""
    user = os.environ.get("SMTP_USER", "")
    pwd  = os.environ.get("SMTP_PASS", "")
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))

    if not user or not pwd:
        return {"ok": False, "error": "SMTP_USER / SMTP_PASS no configurados"}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"]    = user
        msg["To"]      = destinatario
        if texto:
            msg.attach(MIMEText(texto, "plain"))
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(host, port, timeout=15) as s:
            s.starttls()
            s.login(user, pwd)
            s.sendmail(user, destinatario, msg.as_string())
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def enviar_telegram(chat_id: str, mensaje: str) -> dict:
    """Envía mensaje por Telegram Bot."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN no configurado"}

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"},
            timeout=10,
        )
        return {"ok": r.status_code == 200}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def enviar_webhook(url: str, payload: dict) -> dict:
    """Webhook genérico — útil para Slack, Discord, n8n, etc."""
    try:
        r = requests.post(url, json=payload, timeout=10)
        return {"ok": r.status_code < 300, "status": r.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def notificar(
    evento:   str,
    mensaje:  str,
    asunto:   Optional[str] = None,
    canales:  list = None,
    destinatarios: dict = None,
):
    """
    Envía una notificación por múltiples canales.

    Ejemplo:
        notificar(
            evento="stock_bajo",
            asunto="Stock bajo en Extractores",
            mensaje="El producto EXT-60W tiene solo 3 unidades",
            canales=["email", "whatsapp"],
            destinatarios={
                "email":    "jonathan@extractoreschile.cl",
                "whatsapp": "+56912345678",
            }
        )
    """
    if canales is None:
        canales = ["email"]
    if destinatarios is None:
        destinatarios = {
            "email":    os.environ.get("EMAIL_CESAR", "hola@kraftdo.cl"),
            "whatsapp": os.environ.get("WHATSAPP_CESAR", ""),
            "telegram": os.environ.get("TELEGRAM_CHAT_ID", ""),
        }

    asunto = asunto or f"KraftDo — {evento}"
    html = f"""<!DOCTYPE html><html><body style="font-family:Arial">
<h2 style="color:#1A1A2E">{asunto}</h2>
<p>{mensaje}</p>
<hr><small style="color:#888">KraftDo Sistema — {datetime.now().strftime('%d/%m/%Y %H:%M')}</small>
</body></html>"""

    resultados = {}
    for canal in canales:
        dest = destinatarios.get(canal, "")
        if not dest:
            resultados[canal] = {"ok": False, "error": f"Sin destinatario para {canal}"}
            continue

        if canal == "email":
            resultados["email"]    = enviar_email(dest, asunto, html, mensaje)
        elif canal == "whatsapp":
            resultados["whatsapp"] = enviar_whatsapp(dest, f"*{asunto}*\n{mensaje}")
        elif canal == "telegram":
            resultados["telegram"] = enviar_telegram(dest, f"*{asunto}*\n{mensaje}")

    # Log de auditoría
    try:
        from jobs.audit import log_action
        log_action(
            accion="notificacion",
            detalle={"evento": evento, "canales": canales, "resultados": resultados},
        )
    except Exception:
        pass

    return resultados
