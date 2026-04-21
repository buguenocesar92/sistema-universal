"""
reporte_base.py — Generador de reportes unificado
Reemplaza reporte_adille.py, reporte_extractores.py, reporte_kraftdo.py

Cada reporte ahora es solo una config, no un script duplicado.
Uso:
  python3 reporte_base.py adille --email jonathan@adille.cl
  python3 reporte_base.py extractores --dry-run
  python3 reporte_base.py kraftdo_bd --dry-run
"""
import sys, os, argparse, smtplib, json
from datetime import datetime
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Callable, Optional

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from core import Sistema


# ── Configuración de reportes por empresa ─────────────────────────────────────
REPORTES = {
    "adille": {
        "nombre":          "Constructora Adille",
        "email_default":   "hola@kraftdo.cl",
        "color_primary":   "0D1B3E",
        "color_accent":    "C8A951",
        "subject":         "Reporte Semanal — Constructora Adille",
        "secciones": [
            {"tipo": "kpis",       "alias": "panel_general",  "titulo": "KPIs Generales"},
            {"tipo": "registros",  "alias": "materiales",     "titulo": "Materiales por obra",    "limit": 15},
            {"tipo": "registros",  "alias": "liquidacion",    "titulo": "Liquidación de sueldos", "limit": 15},
            {"tipo": "registros",  "alias": "bencina",        "titulo": "Gastos bencina",         "limit": 10},
            {"tipo": "registros",  "alias": "facturacion",    "titulo": "Facturación",            "limit": 10},
        ],
    },
    "extractores": {
        "nombre":          "Extractores Chile Ltda",
        "email_default":   "hola@kraftdo.cl",
        "color_primary":   "1A3A5C",
        "color_accent":    "E8A020",
        "subject":         "Reporte Semanal — Extractores Chile",
        "secciones": [
            {"tipo": "kpis",      "alias": "resumen_stock",  "titulo": "Resumen de stock"},
            {"tipo": "registros", "alias": "stock",          "titulo": "Stock por modelo",    "limit": 20, "alerta_si": {"campo": "stock_actual", "op": "<", "valor": 10}},
            {"tipo": "registros", "alias": "ventas",         "titulo": "Ventas recientes",    "limit": 15},
            {"tipo": "registros", "alias": "promociones",    "titulo": "Promociones activas", "limit": 10},
            {"tipo": "registros", "alias": "ferias",         "titulo": "Próximas ferias",     "limit": 5},
        ],
    },
    "kraftdo_bd": {
        "nombre":          "KraftDo SpA",
        "email_default":   "hola@kraftdo.cl",
        "color_primary":   "1A1A2E",
        "color_accent":    "E94560",
        "subject":         "Reporte Operativo — KraftDo SpA",
        "secciones": [
            {"tipo": "kpis",      "alias": "kpis_caja",  "titulo": "Estado financiero"},
            {"tipo": "registros", "alias": "pedidos",    "titulo": "Pedidos activos",     "limit": 15},
            {"tipo": "registros", "alias": "clientes",   "titulo": "Clientes",            "limit": 10},
            {"tipo": "registros", "alias": "productos",  "titulo": "Catálogo productos",  "limit": 10, "filtro": lambda r: str(r.get("sku","")).startswith("A")},
            {"tipo": "registros", "alias": "insumos",    "titulo": "Insumos con alerta",  "limit": 10, "filtro": lambda r: "⚠️" in str(r.get("alerta",""))},
            {"tipo": "registros", "alias": "caja",       "titulo": "Movimientos de caja", "limit": 10},
        ],
    },
}


# ── Helpers ────────────────────────────────────────────────────────────────────
def _fmt_moneda(v) -> str:
    try:
        return f"${int(float(v)):,}".replace(",", ".")
    except Exception:
        return "—"

def _fmt_pct(v) -> str:
    try:
        return f"{float(v)*100:.0f}%"
    except Exception:
        return "—"

def _fmt_fecha(v) -> str:
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y")
    return str(v) if v else ""

def _fmt_celda(v):
    """Formatea un valor para HTML según el tipo detectado."""
    if v is None or v == "":
        return ""
    if isinstance(v, datetime):
        return _fmt_fecha(v)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if abs(v) > 1000:
            return _fmt_moneda(v)
        return str(v)
    return str(v)


# ── Renderers de secciones ────────────────────────────────────────────────────
def _render_kpis(s: Sistema, seccion: dict, cfg: dict) -> str:
    """Renderiza una sección de KPIs (grid de cards)."""
    try:
        kpis = s.kpis().get(seccion["alias"], {})
        if not kpis:
            return ""
    except Exception:
        return ""

    cards_html = ""
    for clave, valor in kpis.items():
        label = clave.replace("_", " ").title()
        es_negativo = isinstance(valor, (int, float)) and valor < 0
        color = "#c0392b" if es_negativo else f"#{cfg['color_primary']}"
        cards_html += f"""
        <div style="flex:1;min-width:150px;background:#f5f5f5;padding:13px;border-radius:6px;margin:4px;text-align:center">
          <div style="font-size:11px;color:#666">{label}</div>
          <div style="font-size:18px;font-weight:bold;color:{color}">{_fmt_moneda(valor) if abs(valor) > 1000 else valor}</div>
        </div>"""

    return f"""
    <h2>{seccion['titulo']}</h2>
    <div style="display:flex;flex-wrap:wrap;margin:12px 0">{cards_html}</div>
    """


def _render_registros(s: Sistema, seccion: dict, cfg: dict) -> str:
    """Renderiza una sección de tabla de registros."""
    try:
        registros = s.registros(seccion["alias"])
    except Exception:
        return ""

    # Filtrar vacíos
    registros = [r for r in registros if any(v for v in r.values() if v not in (None, "", False))]

    # Filtro custom opcional
    filtro = seccion.get("filtro")
    if filtro:
        registros = [r for r in registros if filtro(r)]

    if not registros:
        return f"""
        <h2>{seccion['titulo']}</h2>
        <p style='color:#888;font-size:13px'>Sin registros disponibles.</p>
        """

    limit = seccion.get("limit", 20)
    headers = list(registros[0].keys())

    # Construir filas
    filas_html = ""
    alerta_cfg = seccion.get("alerta_si")
    for r in registros[:limit]:
        es_alerta = False
        if alerta_cfg:
            try:
                val = r.get(alerta_cfg["campo"])
                if alerta_cfg["op"] == "<" and val is not None and float(val) < alerta_cfg["valor"]:
                    es_alerta = True
            except Exception:
                pass

        bg = "background:#fff3cd;" if es_alerta else ""
        celdas = "".join(f"<td style='padding:6px 8px;border-bottom:1px solid #eee'>{_fmt_celda(r.get(h))}</td>" for h in headers)
        filas_html += f"<tr style='{bg}'>{celdas}</tr>"

    headers_html = "".join(f"<th style='background:#{cfg['color_primary']};color:white;padding:8px;text-align:left;font-size:12px'>{h.replace('_',' ').title()}</th>" for h in headers)

    extras = ""
    if len(registros) > limit:
        extras = f"<p style='font-size:12px;color:#888'>Se muestran {limit} de {len(registros)} registros.</p>"

    return f"""
    <h2>{seccion['titulo']} ({len(registros)} registros)</h2>
    <table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:14px">
      <tr>{headers_html}</tr>
      {filas_html}
    </table>
    {extras}
    """


# ── Generador principal ───────────────────────────────────────────────────────
RENDERERS: dict[str, Callable] = {
    "kpis":      _render_kpis,
    "registros": _render_registros,
}


def generar_reporte(empresa: str) -> str:
    """Genera el HTML completo del reporte según la config de la empresa."""
    if empresa not in REPORTES:
        raise ValueError(f"Empresa '{empresa}' no tiene configuración de reporte. Agrégala a REPORTES en reporte_base.py")

    cfg = REPORTES[empresa]
    s   = Sistema(empresa)
    fecha = datetime.now().strftime("%d/%m/%Y")

    # Renderizar cada sección
    secciones_html = ""
    for seccion in cfg["secciones"]:
        renderer = RENDERERS.get(seccion["tipo"])
        if renderer:
            secciones_html += renderer(s, seccion, cfg)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body{{font-family:Arial,sans-serif;color:#333;max-width:740px;margin:0 auto}}
h1{{background:#{cfg['color_primary']};color:#{cfg['color_accent']};padding:20px;margin:0;font-size:20px}}
h2{{color:#{cfg['color_primary']};border-bottom:2px solid #{cfg['color_accent']};padding-bottom:5px;font-size:15px;margin-top:22px}}
table tr:nth-child(even){{background:#fafafa}}
.footer{{background:#f0f0f0;padding:12px;font-size:11px;color:#888;text-align:center;margin-top:20px}}
</style></head><body>
<h1>{cfg['nombre']} — Reporte {fecha}</h1>
{secciones_html}
<div class="footer">Generado automáticamente por KraftDo Sistema Universal — {fecha}</div>
</body></html>"""


def enviar_reporte(empresa: str, destinatario: Optional[str] = None, dry_run: bool = False) -> bool:
    """Genera y envía el reporte por email."""
    cfg  = REPORTES.get(empresa)
    if not cfg:
        print(f"ERROR: Empresa '{empresa}' no configurada")
        return False

    destinatario = destinatario or os.environ.get(
        f"EMAIL_{empresa.upper()}",
        cfg["email_default"]
    )

    try:
        html = generar_reporte(empresa)
    except Exception as e:
        print(f"ERROR generando reporte: {e}")
        return False

    if dry_run:
        preview = Path(f"/tmp/reporte_{empresa}_preview.html")
        preview.write_text(html, encoding="utf-8")
        print(f"[DRY RUN] Preview → {preview}")
        print(f"[DRY RUN] Se enviaría a: {destinatario}")
        return True

    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    if not smtp_user or not smtp_pass:
        print("ERROR: SMTP_USER y SMTP_PASS deben estar configurados en .env")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{cfg['subject']} {datetime.now().strftime('%d/%m/%Y')}"
    msg["From"]    = smtp_user
    msg["To"]      = destinatario
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(os.environ.get("SMTP_HOST", "smtp.gmail.com"),
                          int(os.environ.get("SMTP_PORT", "587"))) as sv:
            sv.starttls()
            sv.login(smtp_user, smtp_pass)
            sv.sendmail(smtp_user, destinatario, msg.as_string())
        print(f"✅ Reporte enviado a {destinatario}")
        return True
    except Exception as e:
        print(f"ERROR enviando: {e}")
        return False


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="KraftDo - Generador de reportes unificado")
    p.add_argument("empresa",   help=f"Empresa: {', '.join(REPORTES.keys())}")
    p.add_argument("--email",   help="Destinatario (override)")
    p.add_argument("--dry-run", action="store_true", help="Solo generar preview sin enviar")
    args = p.parse_args()

    enviar_reporte(args.empresa, args.email, args.dry_run)
