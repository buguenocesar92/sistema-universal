"""
onboarding.py — Orquestador de onboarding automático de clientes nuevos
Se activa desde el Classifier cuando se aprueba un mapeo.

Hace todo solo:
1. Guarda el JSON de la empresa
2. Crea la conexión en database.php de Laravel
3. Genera los archivos Laravel (migraciones, modelos, resources)
4. Crea el reporte automático
5. Registra la empresa en el portal de upload
6. Envía email de confirmación a César
"""
import os, sys, json, re, shutil, smtplib, subprocess
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SCRIPT_DIR   = Path(__file__).parent
EMPRESAS_DIR = SCRIPT_DIR / "empresas"
LARAVEL_DIR  = SCRIPT_DIR / "laravel_multitenant"
REPORTES_DIR = SCRIPT_DIR

EMAIL_CESAR  = os.environ.get("EMAIL_CESAR", "hola@kraftdo.cl")

# ── Paso 1: Guardar JSON ───────────────────────────────────────────────────────
def guardar_json(empresa: str, cfg: dict) -> Path:
    EMPRESAS_DIR.mkdir(exist_ok=True)
    ruta = EMPRESAS_DIR / f"{empresa}.json"
    ruta.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    print(f"  ✅ JSON guardado: {ruta}")
    return ruta

# ── Paso 2: Agregar conexión a database.php ────────────────────────────────────
def agregar_conexion_laravel(empresa: str, cfg: dict):
    db_file = LARAVEL_DIR / "config" / "database.php"
    if not db_file.exists():
        print(f"  ⚠️  {db_file} no existe — saltando")
        return

    nombre_empresa = cfg.get("empresa", {}).get("nombre", empresa)
    db_name        = f"kraftdo_{empresa}"
    contenido      = db_file.read_text()

    # No agregar si ya existe
    if f"'{empresa}'" in contenido:
        print(f"  ✅ Conexión '{empresa}' ya existe en database.php")
        return

    bloque = f"""
        // ── {nombre_empresa} ──────────────────────────────────────────────────
        '{empresa}' => [
            'driver'    => 'mysql',
            'host'      => env('DB_HOST', 'mysql'),
            'port'      => env('DB_PORT', '3306'),
            'database'  => env('DB_DATABASE_{empresa.upper()}', '{db_name}'),
            'username'  => env('DB_USERNAME_{empresa.upper()}', env('DB_USERNAME', 'kraftdo')),
            'password'  => env('DB_PASSWORD_{empresa.upper()}', env('DB_PASSWORD', '')),
            'charset'   => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix'    => '',
            'strict'    => true,
            'engine'    => null,
        ],
"""
    # Insertar antes del cierre del array de connections
    contenido = contenido.replace(
        "    ],\n\n    'migrations'",
        f"{bloque}    ],\n\n    'migrations'"
    )
    db_file.write_text(contenido)
    print(f"  ✅ Conexión '{empresa}' agregada a database.php")

# ── Paso 3: Generar código Laravel ────────────────────────────────────────────
def generar_laravel(empresa: str) -> int:
    sys.path.insert(0, str(SCRIPT_DIR))
    from generator import generar

    output_dir = SCRIPT_DIR / f"_generated_{empresa}"
    generar(empresa, output_dir=str(output_dir))

    # Copiar al multi-tenant con namespace correcto
    empresa_cap = empresa.replace("_", " ").title().replace(" ", "")
    
    src_models = output_dir / "app" / "Models"
    dst_models = LARAVEL_DIR / "app" / "Models" / empresa_cap
    if src_models.exists():
        shutil.copytree(src_models, dst_models, dirs_exist_ok=True)
        # Agregar $connection a cada modelo
        for modelo in dst_models.glob("*.php"):
            contenido = modelo.read_text()
            contenido = re.sub(
                r'(class \w+ extends Model\s*\{)',
                f"\\1\n    protected $connection = '{empresa}';\n",
                contenido
            )
            # Actualizar namespace
            contenido = contenido.replace(
                "namespace App\\Models;",
                f"namespace App\\Models\\{empresa_cap};"
            )
            modelo.write_text(contenido)

    src_resources = output_dir / "app" / "Filament" / "Resources"
    dst_resources = LARAVEL_DIR / "app" / "Filament" / "Resources" / empresa_cap
    if src_resources.exists():
        shutil.copytree(src_resources, dst_resources, dirs_exist_ok=True)
        for resource in dst_resources.rglob("*.php"):
            contenido = resource.read_text()
            contenido = contenido.replace(
                "namespace App\\Filament\\Resources;",
                f"namespace App\\Filament\\Resources\\{empresa_cap};"
            ).replace(
                "use App\\Models\\",
                f"use App\\Models\\{empresa_cap}\\"
            )
            resource.write_text(contenido)

    src_migs = output_dir / "database" / "migrations"
    dst_migs = LARAVEL_DIR / "database" / "migrations"
    dst_migs.mkdir(parents=True, exist_ok=True)
    if src_migs.exists():
        for mig in src_migs.glob("*.php"):
            nuevo = mig.name.replace("create_", f"create_{empresa}_")
            contenido = mig.read_text()
            # Cambiar nombre de tabla para incluir empresa
            contenido = re.sub(
                r"Schema::create\('(\w+)'",
                lambda m: f"Schema::create('{empresa}_{m.group(1)}'",
                contenido
            )
            (dst_migs / nuevo).write_text(contenido)

    # Contar archivos generados
    total = sum(1 for _ in output_dir.rglob("*.php"))
    print(f"  ✅ Laravel generado: {total} archivos")

    # Limpiar directorio temporal
    shutil.rmtree(output_dir, ignore_errors=True)
    return total

# ── Paso 4: Crear reporte automático ──────────────────────────────────────────
def generar_reporte_script(empresa: str, cfg: dict) -> Path:
    nombre    = cfg.get("empresa", {}).get("nombre", empresa)
    email_var = f"EMAIL_{empresa.upper()}"
    color_p   = cfg.get("empresa", {}).get("color_primary", "1A1A2E")
    color_a   = cfg.get("empresa", {}).get("color_accent", "E94560")
    hojas     = list(cfg.get("hojas", {}).keys())
    kpi_hoja  = next((k for k, v in cfg.get("hojas", {}).items() if v.get("tipo") == "kpis"), None)

    script = f'''"""
reporte_{empresa}.py — Reporte automático de {nombre}
Generado automáticamente por KraftDo Onboarding — {datetime.now().strftime("%d/%m/%Y")}
"""
import sys, os, argparse, smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import Sistema

def fmt(v):
    try:
        return f"${{int(float(v)):,}}".replace(",", ".")
    except:
        return "—"

def generar_reporte():
    s    = Sistema('{empresa}')
    kpis = s.kpis()
    fecha = datetime.now().strftime("%d/%m/%Y")
    secciones_html = ""

    # Generar sección por cada hoja de registros
    hojas = {json.dumps(hojas)}
    for alias in hojas:
        try:
            registros = [r for r in s.registros(alias) if any(v for v in r.values() if v)]
            if not registros:
                continue
            headers = list(registros[0].keys())
            filas   = "".join(
                "<tr>" + "".join(f"<td>{{r.get(h, '')}}</td>" for h in headers) + "</tr>"
                for r in registros[:20]
            )
            secciones_html += f"""
            <h2>{{alias.replace("_", " ").title()}} ({{len(registros)}} registros)</h2>
            <table>
              <tr>{{"".join(f"<th>{{h}}</th>" for h in headers)}}</tr>
              {{filas}}
            </table>"""
        except Exception as e:
            secciones_html += f"<p style=\\'color:#888\\'>{{alias}}: {{e}}</p>"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body{{font-family:Arial,sans-serif;color:#333;max-width:740px;margin:0 auto;}}
h1{{background:#{color_p};color:#{color_a};padding:20px;margin:0;font-size:20px;}}
h2{{color:#{color_p};border-bottom:2px solid #{color_a};padding-bottom:5px;font-size:15px;margin-top:22px;}}
table{{width:100%;border-collapse:collapse;font-size:12px;margin-bottom:14px;}}
th{{background:#{color_p};color:white;padding:7px;text-align:left;}}
td{{padding:5px 7px;border-bottom:1px solid #eee;}}
tr:nth-child(even){{background:#fafafa;}}
.footer{{background:#f0f0f0;padding:12px;font-size:11px;color:#888;text-align:center;margin-top:20px;}}
</style></head><body>
<h1>{nombre} — Reporte {{fecha}}</h1>
{{secciones_html}}
<div class="footer">Generado por KraftDo Sistema Universal — {{fecha}}</div>
</body></html>"""
    return html

def enviar(html, destinatario, dry_run=False):
    if dry_run:
        with open(f"/tmp/reporte_{empresa}_preview.html", "w") as f:
            f.write(html)
        print(f"[DRY RUN] Preview → /tmp/reporte_{empresa}_preview.html")
        return
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    if not smtp_user or not smtp_pass:
        print("ERROR: Configurar SMTP_USER y SMTP_PASS")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Reporte Semanal — {nombre} {{datetime.now().strftime('%d/%m/%Y')}}"
    msg["From"]    = smtp_user
    msg["To"]      = destinatario
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(smtp_host, smtp_port) as sv:
        sv.starttls()
        sv.login(smtp_user, smtp_pass)
        sv.sendmail(smtp_user, destinatario, msg.as_string())
    print(f"✅ Reporte enviado a {{destinatario}}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--email",   default=os.environ.get("{email_var}", "hola@kraftdo.cl"))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    print(f"Generando reporte {nombre}...")
    enviar(generar_reporte(), args.email, dry_run=args.dry_run)
'''
    ruta = REPORTES_DIR / f"reporte_{empresa}.py"
    ruta.write_text(script)
    print(f"  ✅ Reporte generado: {ruta.name}")
    return ruta

# ── Paso 5: Registrar en portal de upload ─────────────────────────────────────
def registrar_en_portal(empresa: str, cfg: dict):
    portal = SCRIPT_DIR / "upload_portal.py"
    if not portal.exists():
        print(f"  ⚠️  upload_portal.py no existe")
        return

    nombre    = cfg.get("empresa", {}).get("nombre", empresa)
    contenido = portal.read_text()

    if f'"{empresa}"' in contenido:
        print(f"  ✅ '{empresa}' ya está en el portal")
        return

    # Agregar al diccionario EMPRESAS
    contenido = contenido.replace(
        '"kraftdo_bd":   {"nombre": "KraftDo SpA (BD Maestra)", "reporte": "reporte_kraftdo.py"},',
        f'"kraftdo_bd":   {{"nombre": "KraftDo SpA (BD Maestra)", "reporte": "reporte_kraftdo.py"}},\n'
        f'    "{empresa}":      {{"nombre": "{nombre}", "reporte": "reporte_{empresa}.py"}},'
    )

    # Agregar opción en el HTML
    contenido = contenido.replace(
        '<option value="kraftdo_bd">KraftDo SpA (BD Maestra)</option>',
        f'<option value="kraftdo_bd">KraftDo SpA (BD Maestra)</option>\n'
        f'    <option value="{empresa}">{nombre}</option>'
    )

    portal.write_text(contenido)
    print(f"  ✅ '{empresa}' registrado en el portal")

# ── Paso 6: Agregar BD a init.sql ─────────────────────────────────────────────
def agregar_bd_mysql(empresa: str):
    init_sql = SCRIPT_DIR / "docker" / "mysql" / "init.sql"
    if not init_sql.exists():
        return

    db_name  = f"kraftdo_{empresa}"
    contenido = init_sql.read_text()

    if db_name in contenido:
        print(f"  ✅ BD '{db_name}' ya existe en init.sql")
        return

    nuevo_bloque = f"""
CREATE DATABASE IF NOT EXISTS {db_name}
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON {db_name}.* TO 'kraftdo'@'%';
"""
    contenido = contenido.replace("FLUSH PRIVILEGES;", nuevo_bloque + "\nFLUSH PRIVILEGES;")
    init_sql.write_text(contenido)
    print(f"  ✅ BD '{db_name}' agregada a init.sql")

# ── Paso 7: Email de confirmación a César ─────────────────────────────────────
def enviar_confirmacion(empresa: str, cfg: dict, archivos_generados: int):
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    if not smtp_user or not smtp_pass:
        print(f"  ⚠️  SMTP no configurado — saltando email de confirmación")
        return

    nombre = cfg.get("empresa", {}).get("nombre", empresa)
    hojas  = list(cfg.get("hojas", {}).keys())
    fecha  = datetime.now().strftime("%d/%m/%Y %H:%M")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body{{font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto;}}
h1{{background:#1A1A2E;color:#E94560;padding:16px 20px;margin:0;font-size:18px;}}
.item{{padding:8px 0;border-bottom:1px solid #eee;font-size:14px;}}
.item span{{color:#888;font-size:12px;display:block;}}
.ok{{color:#27ae60;font-weight:bold;}}
.footer{{background:#f5f5f5;padding:12px;font-size:11px;color:#888;margin-top:20px;}}
</style></head><body>
<h1>✅ Cliente activado — {nombre}</h1>
<div style="padding:20px">
<div class="item"><strong>Empresa:</strong> {nombre}<span>ID: {empresa}</span></div>
<div class="item"><strong>Fecha activación:</strong> {fecha}</div>
<div class="item"><strong>Hojas configuradas:</strong> {len(hojas)}<span>{", ".join(hojas)}</span></div>
<div class="item"><strong>Archivos Laravel generados:</strong> {archivos_generados}</div>
<div class="item"><strong>Reporte automático:</strong> <span class="ok">reporte_{empresa}.py ✅</span></div>
<div class="item"><strong>Portal de upload:</strong> <span class="ok">agregado ✅</span></div>
<div class="item"><strong>Base de datos:</strong> <span class="ok">kraftdo_{empresa} ✅</span></div>
<h3 style="margin-top:20px">Próximos pasos</h3>
<ol style="font-size:14px;line-height:1.8">
  <li>Agregar <code>EMAIL_{empresa.upper()}=correo@cliente.cl</code> al .env</li>
  <li>Reconstruir Docker: <code>docker compose up -d --build laravel</code></li>
  <li>Correr migraciones: <code>docker compose exec laravel php artisan migrate</code></li>
  <li>Probar reporte: <code>python3 reporte_{empresa}.py --dry-run</code></li>
</ol>
</div>
<div class="footer">KraftDo Sistema Universal — generado automáticamente</div>
</body></html>"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"✅ Nuevo cliente activado — {nombre}"
        msg["From"]    = smtp_user
        msg["To"]      = EMAIL_CESAR
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(os.environ.get("SMTP_HOST","smtp.gmail.com"),
                          int(os.environ.get("SMTP_PORT","587"))) as sv:
            sv.starttls()
            sv.login(smtp_user, smtp_pass)
            sv.sendmail(smtp_user, EMAIL_CESAR, msg.as_string())
        print(f"  ✅ Email de confirmación enviado a {EMAIL_CESAR}")
    except Exception as e:
        print(f"  ⚠️  Email falló: {e}")

# ── Orquestador principal (delega a onboarding_steps) ────────────────────────
def onboarding(empresa: str, cfg: dict) -> dict:
    """
    Ejecuta el onboarding completo de una empresa nueva.
    Internamente delega a onboarding_steps.py (pasos tipados con interface común).

    Args:
        empresa: slug de la empresa (ej: "gym_flo", "clinica_alemana")
        cfg:     dict con la configuración JSON del Classifier

    Returns:
        dict con el resumen del onboarding
    """
    from onboarding_steps import ejecutar_onboarding
    return ejecutar_onboarding(empresa, cfg)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="KraftDo Onboarding")
    p.add_argument("empresa", help="Slug de la empresa (ej: gym_flo)")
    p.add_argument("--json",  help="Ruta al JSON de configuración")
    args = p.parse_args()

    if args.json:
        cfg = json.loads(Path(args.json).read_text())
    else:
        # Cargar desde empresas/
        cfg_path = EMPRESAS_DIR / f"{args.empresa}.json"
        if not cfg_path.exists():
            print(f"ERROR: No se encontró {cfg_path}")
            sys.exit(1)
        cfg = json.loads(cfg_path.read_text())

    onboarding(args.empresa, cfg)
