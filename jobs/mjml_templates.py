"""
mjml_templates.py — Genera correos HTML responsive desde MJML
MJML se compila a HTML que funciona en Gmail, Outlook, Apple Mail, Yahoo, etc.

Sin dependencia pesada: usa la API publica de MJML (https://mjml.io/api)
o Python puro como fallback.
"""
import os, re
from typing import Optional
from pathlib import Path

MJML_APP_ID     = os.environ.get("MJML_APP_ID", "")
MJML_APP_SECRET = os.environ.get("MJML_APP_SECRET", "")

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "email"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def compilar_mjml(mjml: str) -> str:
    """
    Compila MJML a HTML.
    Si hay credenciales API, usa la API oficial.
    Si no, hace una conversion simplificada suficiente para los reportes.
    """
    # Opcion 1: API oficial (requiere cuenta gratis en mjml.io)
    if MJML_APP_ID and MJML_APP_SECRET:
        try:
            import requests
            r = requests.post(
                "https://api.mjml.io/v1/render",
                json={"mjml": mjml},
                auth=(MJML_APP_ID, MJML_APP_SECRET),
                timeout=10,
            )
            if r.status_code == 200:
                return r.json().get("html", mjml)
        except Exception:
            pass

    # Opcion 2: Conversion Python basica
    return _mjml_a_html_basico(mjml)


def _mjml_a_html_basico(mjml: str) -> str:
    """Conversion MJML->HTML basica (subset suficiente para reportes)."""
    html = mjml
    # mj-section, mj-column, mj-text, mj-button, mj-image
    html = re.sub(r'<mjml>', '<!DOCTYPE html><html><head><meta charset="utf-8">'
                             '<meta name="viewport" content="width=device-width,initial-scale=1">'
                             '<style>body{margin:0;font-family:Arial,sans-serif;}'
                             '.mj-section{padding:16px;}'
                             '.mj-column{display:block;margin:0 auto;max-width:600px;}'
                             '.mj-button{display:inline-block;padding:12px 24px;'
                             'background:#1A1A2E;color:#C8A951;text-decoration:none;border-radius:6px;}'
                             '@media(max-width:600px){.mj-column{width:100%!important;}}'
                             '</style></head><body>', html)
    html = re.sub(r'</mjml>',   '</body></html>',                 html)
    html = re.sub(r'<mj-head>.*?</mj-head>', '', html, flags=re.DOTALL)
    html = re.sub(r'<mj-body[^>]*>',  '<div style="max-width:600px;margin:0 auto">', html)
    html = re.sub(r'</mj-body>',      '</div>', html)
    html = re.sub(r'<mj-section[^>]*>',  '<div class="mj-section">', html)
    html = re.sub(r'</mj-section>',      '</div>', html)
    html = re.sub(r'<mj-column[^>]*>',   '<div class="mj-column">', html)
    html = re.sub(r'</mj-column>',       '</div>', html)
    html = re.sub(r'<mj-text[^>]*>',     '<div style="padding:10px 0;line-height:1.5">', html)
    html = re.sub(r'</mj-text>',         '</div>', html)
    html = re.sub(r'<mj-button href="([^"]*)"[^>]*>([^<]*)</mj-button>',
                  r'<a href="\1" class="mj-button">\2</a>', html)
    html = re.sub(r'<mj-image src="([^"]*)"[^>]*/>',
                  r'<img src="\1" style="max-width:100%;display:block;margin:0 auto">', html)
    html = re.sub(r'<mj-divider[^>]*/>',
                  '<hr style="border:none;border-top:1px solid #ddd;margin:16px 0">', html)
    html = re.sub(r'<mj-spacer height="(\d+)px"[^>]*/>',
                  r'<div style="height:\1px"></div>', html)

    return html


def render_template(template_name: str, **variables) -> str:
    """
    Carga una plantilla .mjml desde templates/email/ y la compila con variables.
    Variables se reemplazan con {{var}}.
    """
    path = TEMPLATES_DIR / f"{template_name}.mjml"
    if not path.exists():
        return ""

    mjml = path.read_text(encoding="utf-8")

    # Reemplazar variables {{nombre}}
    for var, valor in variables.items():
        mjml = mjml.replace(f"{{{{{var}}}}}", str(valor))

    return compilar_mjml(mjml)
