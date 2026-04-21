"""
upload_portal.py — Portal web para que Jonathan suba el Excel mensual
Inicia: python3 upload_portal.py
URL:    http://localhost:8002
"""
import os, sys, hashlib, secrets, smtplib, threading
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from jobs.sentry_config import init_sentry, capturar_error
from jobs.audit import log_action

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

UPLOAD_DIR = SCRIPT_DIR / "storage" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT   = {".xlsx", ".xls"}
ALLOWED_MAGIC = {
    b"PK": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    b"\xd0\xcf": "application/vnd.ms-excel",
}
MAX_MB = 10

EMPRESAS = {
    "adille":      {"nombre": "Constructora Adille",    "reporte": "reporte_adille.py"},
    "extractores": {"nombre": "Extractores Chile Ltda", "reporte": "reporte_extractores.py"},
    "kraftdo_bd":   {"nombre": "KraftDo SpA (BD Maestra)", "reporte": "reporte_kraftdo.py"},
    "gym_flo":      {"nombre": "GymFlo Rancagua", "reporte": "reporte_gym_flo.py"},
}

# Token de acceso simple — se configura en .env
ACCESS_TOKEN = os.environ.get("UPLOAD_TOKEN", "")
if not ACCESS_TOKEN:
    import secrets
    ACCESS_TOKEN = secrets.token_urlsafe(16)
    print(f"⚠️  UPLOAD_TOKEN no configurado — generado temporal: {ACCESS_TOKEN}")
    print(f"⚠️  Configúralo en .env para que sea persistente")

app = FastAPI(title="KraftDo Upload Portal")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── HTML del portal ────────────────────────────────────────────────────────────
PORTAL_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KraftDo — Subir Excel</title>
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#1A1A2E">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black">
<script>
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js"));
}
</script>
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:Arial,sans-serif;background:#f0f2f5;min-height:100vh;display:flex;align-items:center;justify-content:center;}}
  .card{{background:white;border-radius:12px;padding:40px;width:100%;max-width:480px;box-shadow:0 4px 20px rgba(0,0,0,0.08);}}
  .logo{{background:#0D1B3E;color:#C8A951;padding:16px 20px;border-radius:8px;margin-bottom:28px;text-align:center;}}
  .logo h1{{font-size:18px;margin-bottom:4px;}}
  .logo p{{font-size:12px;opacity:0.8;}}
  label{{display:block;font-size:13px;font-weight:bold;color:#333;margin-bottom:6px;margin-top:16px;}}
  select,input[type=text],input[type=password]{{width:100%;padding:10px 12px;border:1px solid #ddd;border-radius:6px;font-size:14px;}}
  .drop-zone{{border:2px dashed #ddd;border-radius:8px;padding:32px;text-align:center;cursor:pointer;transition:all .2s;margin-top:8px;background:#fafafa;}}
  .drop-zone:hover,.drop-zone.drag-over{{border-color:#0D1B3E;background:#f0f4ff;}}
  .drop-zone .icon{{font-size:32px;margin-bottom:8px;}}
  .drop-zone p{{font-size:13px;color:#666;}}
  .drop-zone .file-name{{font-size:13px;color:#0D1B3E;font-weight:bold;margin-top:8px;}}
  input[type=file]{{display:none;}}
  button{{width:100%;padding:13px;background:#0D1B3E;color:#C8A951;border:none;border-radius:8px;font-size:15px;font-weight:bold;cursor:pointer;margin-top:20px;transition:opacity .2s;}}
  button:hover{{opacity:0.9;}}
  button:disabled{{opacity:0.5;cursor:not-allowed;}}
  .status{{margin-top:16px;padding:12px;border-radius:6px;font-size:13px;display:none;}}
  .status.ok{{background:#d4edda;color:#155724;display:block;}}
  .status.error{{background:#f8d7da;color:#721c24;display:block;}}
  .status.loading{{background:#e2e3e5;color:#383d41;display:block;}}
  .progress{{width:100%;height:4px;background:#eee;border-radius:2px;margin-top:8px;display:none;}}
  .progress-bar{{height:4px;background:#0D1B3E;border-radius:2px;width:0%;transition:width .3s;}}
</style></head><body>
<div class="card">
  <div class="logo">
    <h1>KraftDo</h1>
    <p>Portal de carga de reportes mensuales</p>
  </div>

  <label>Empresa</label>
  <select id="empresa">
    <option value="">— Seleccionar —</option>
    <option value="adille">Constructora Adille</option>
    <option value="extractores">Extractores Chile Ltda</option>
    <option value="kraftdo_bd">KraftDo SpA (BD Maestra)</option>
    <option value="gym_flo">GymFlo Rancagua</option>
  </select>

  <label>Código de acceso</label>
  <input type="password" id="token" placeholder="Ingresa el código que te dio KraftDo">

  <label>Archivo Excel del mes</label>
  <div class="drop-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
    <div class="icon">📊</div>
    <p>Arrastra el archivo aquí o haz clic para seleccionar</p>
    <p style="font-size:11px;color:#aaa;margin-top:4px">Solo archivos .xlsx o .xls — máximo 10MB</p>
    <div class="file-name" id="fileName"></div>
  </div>
  <input type="file" id="fileInput" accept=".xlsx,.xls">

  <div class="progress" id="progress"><div class="progress-bar" id="progressBar"></div></div>

  <button id="btn" onclick="subir()" disabled>Subir y generar reporte</button>

  <div class="status" id="status"></div>
</div>

<script>
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileName  = document.getElementById('fileName');
const btn       = document.getElementById('btn');
let selectedFile = null;

function checkReady() {
  btn.disabled = !(selectedFile && document.getElementById('empresa').value && document.getElementById('token').value);
}

fileInput.addEventListener('change', e => {
  selectedFile = e.target.files[0];
  fileName.textContent = selectedFile ? selectedFile.name : '';
  dropZone.style.borderColor = selectedFile ? '#0D1B3E' : '#ddd';
  checkReady();
});

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  selectedFile = e.dataTransfer.files[0];
  fileName.textContent = selectedFile ? selectedFile.name : '';
  checkReady();
});

document.getElementById('empresa').addEventListener('change', checkReady);
document.getElementById('token').addEventListener('input', checkReady);

async function subir() {
  const empresa = document.getElementById('empresa').value;
  const token   = document.getElementById('token').value;
  const status  = document.getElementById('status');
  const progress= document.getElementById('progress');
  const bar     = document.getElementById('progressBar');

  status.className = 'status loading';
  status.textContent = 'Subiendo archivo y procesando...';
  progress.style.display = 'block';
  bar.style.width = '30%';
  btn.disabled = true;

  try {
    const form = new FormData();
    form.append('file', selectedFile);
    form.append('empresa', empresa);
    form.append('token', token);

    bar.style.width = '60%';
    const res  = await fetch('/subir', { method: 'POST', body: form });
    const data = await res.json();
    bar.style.width = '100%';

    if (res.ok) {
      status.className = 'status ok';
      status.innerHTML = `✅ <strong>${data.mensaje}</strong><br><small>${data.detalle}</small>`;
    } else {
      status.className = 'status error';
      status.textContent = '❌ ' + (data.detail || 'Error al procesar el archivo');
      btn.disabled = false;
    }
  } catch(e) {
    status.className = 'status error';
    status.textContent = '❌ Error de conexión. Intenta de nuevo.';
    btn.disabled = false;
  }
  setTimeout(() => { bar.style.width = '0%'; progress.style.display = 'none'; }, 1000);
}
</script>
</body></html>"""

# ── Endpoints ──────────────────────────────────────────────────────────────────


@app.get("/shepherd-tour.js")
def shepherd_tour():
    from fastapi.responses import FileResponse, Response
    path = SCRIPT_DIR / "storage" / "pwa" / "shepherd-tour.js"
    if path.exists():
        return FileResponse(path, media_type="application/javascript")
    return Response("// tour not found", media_type="application/javascript", status_code=404)

@app.get("/manifest.json")
def manifest():
    from fastapi.responses import FileResponse
    return FileResponse(SCRIPT_DIR / "storage" / "pwa" / "manifest.json",
                        media_type="application/manifest+json")

@app.get("/sw.js")
def service_worker():
    from fastapi.responses import FileResponse, Response
    path = SCRIPT_DIR / "storage" / "pwa" / "sw.js"
    if path.exists():
        return FileResponse(path, media_type="application/javascript")
    return Response("// SW not found", media_type="application/javascript", status_code=404)

@app.get("/", response_class=HTMLResponse)
def index():
    return PORTAL_HTML

@app.post("/subir")
async def subir(
    file:    UploadFile = File(...),
    empresa: str        = Form(...),
    token:   str        = Form(...),
):
    # 1. Validar token
    if not secrets.compare_digest(token.strip(), ACCESS_TOKEN):
        raise HTTPException(403, "Código de acceso incorrecto")

    # 2. Validar empresa
    if empresa not in EMPRESAS:
        raise HTTPException(400, f"Empresa no reconocida: {empresa}")

    # 3. Validar extensión
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "Solo se aceptan archivos .xlsx o .xls")

    # 4. Leer contenido
    contenido = await file.read()

    # 5. Validar tamaño
    if len(contenido) > MAX_MB * 1024 * 1024:
        raise HTTPException(400, f"El archivo supera los {MAX_MB}MB permitidos")

    # 6. Validar magic bytes
    magic_ok = any(contenido[:2] == k or contenido[:8].startswith(k) for k in ALLOWED_MAGIC)
    if not magic_ok:
        raise HTTPException(400, "El contenido no corresponde a un Excel válido")

    # 7. Guardar con nombre seguro
    nombre_seguro = f"{empresa}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}{ext}"
    destino       = UPLOAD_DIR / nombre_seguro
    destino.write_bytes(contenido)

    # 8.5 Auditoría — registrar la subida
    log_action(
        accion="upload_excel",
        empresa=empresa,
        recurso=nombre_seguro,
        detalle={"size_kb": round(len(contenido)/1024, 1)},
    )

    # 8. Reemplazar el Excel activo de la empresa
    excel_activo = SCRIPT_DIR / f"Control_de_{empresa.capitalize()}.xlsx"
    excel_activo.write_bytes(contenido)

    # 9. Encolar el reporte en Redis (o fallback a thread si Redis no está)
    from jobs.queue import JobQueue
    queue = JobQueue()
    if queue.ok:
        job_id = queue.enqueue("reporte", {
            "empresa": empresa,
            "email":   os.environ.get(f"EMAIL_{empresa.upper()}",
                       os.environ.get("SMTP_USER", "hola@kraftdo.cl")),
        })
        print(f"[{empresa}] Reporte encolado: {job_id}")
    else:
        # Fallback: thread directo si Redis no está disponible
        threading.Thread(
            target=_procesar_reporte,
            args=(empresa, nombre_seguro),
            daemon=True
        ).start()

    nombre_empresa = EMPRESAS[empresa]["nombre"]
    return JSONResponse({
        "mensaje": f"Archivo recibido correctamente",
        "detalle": f"El reporte de {nombre_empresa} se generará y enviará por correo en los próximos minutos.",
        "archivo": nombre_seguro,
    })

def _procesar_reporte(empresa: str, archivo: str):
    """Genera y envía el reporte en un thread separado. Llamada directa, sin subprocess."""
    from reporte_base import enviar_reporte

    email = os.environ.get(
        f"EMAIL_{empresa.upper()}",
        os.environ.get("SMTP_USER", "hola@kraftdo.cl")
    )
    # Mapear IDs del portal a IDs de reporte_base
    empresa_interna = {"adille": "adille", "extractores": "extractores"}.get(empresa, empresa)
    try:
        ok = enviar_reporte(empresa_interna, email)
        print(f"[{empresa}] Reporte {'enviado OK' if ok else 'falló'} → {email}")
    except Exception as e:
        print(f"[{empresa}] Excepción al generar reporte: {e}")

@app.get("/health")
def health():
    return {
        "status": "ok",
        "empresas": list(EMPRESAS.keys()),
        "uploads": len(list(UPLOAD_DIR.glob("*.xlsx"))) + len(list(UPLOAD_DIR.glob("*.xls"))),
    }

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════╗
║       KraftDo Upload Portal — Iniciando             ║
╚══════════════════════════════════════════════════════╝

🌐 http://localhost:8002
🔑 Token: {ACCESS_TOKEN}
📁 Uploads: {UPLOAD_DIR}

Empresas configuradas:
  • adille      → reporte_adille.py
  • extractores → reporte_extractores.py
""")
    uvicorn.run("upload_portal:app", host="0.0.0.0", port=8002, reload=False)
