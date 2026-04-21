"""
KraftDo — api.py v9 UNIVERSAL
Una sola API que sirve a CUALQUIER empresa configurada en /empresas/*.json

Iniciar: python api.py
Docs:    http://localhost:8000/docs

Endpoints genéricos:
  GET  /empresas                          → lista empresas disponibles
  GET  /{empresa}/hojas                   → hojas configuradas
  GET  /{empresa}/catalogo                → todos los productos
  GET  /{empresa}/catalogo/{alias}        → productos de una hoja
  GET  /{empresa}/precio?sku=A01&cantidad=3
  GET  /{empresa}/buscar?q=taza
  POST /{empresa}/cotizar                 → cotización completa
  GET  /{empresa}/registros/{alias}       → filas de cualquier hoja
  GET  /{empresa}/kpis                    → métricas del dashboard
  POST /{empresa}/pdf/cotizacion          → genera PDF (si kraftdo_pdf.py está disponible)
"""

import os
import sys
import json
import time
import secrets
import hashlib
import hmac
import uvicorn
from jobs.sentry_config import init_sentry, capturar_error
from uuid import uuid4
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Query, Security, Depends, Request, UploadFile, File
from fastapi.security import APIKeyHeader
from fastapi.responses import Response, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from core import Sistema
from jobs.cache import cached, invalidar as cache_invalidar

# ── Cargar PDF si está disponible ──────────────────────────────────────────────
try:
    from kraftdo_pdf import generar_cotizacion
    PDF_OK = True
except ImportError:
    PDF_OK = False

app = FastAPI(
    title="KraftDo API Universal v9",
    description="API genérica para cualquier empresa con config JSON + Excel/Sheets.",
    version="9.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Autenticación por API Key ─────────────────────────────────────────────────
_API_KEY        = os.environ.get("API_KEY", "")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verificar_api_key(key: str = Security(_api_key_header)):
    """Valida la API key. Si API_KEY no está configurado, permite todo (modo dev)."""
    if not _API_KEY:
        return True  # Modo desarrollo — sin restricción
    if not key or not secrets.compare_digest(key, _API_KEY):
        raise HTTPException(
            status_code=401,
            detail="API key inválida. Usa el header: X-API-Key: tu_clave",
        )
    return True

# Dependency reutilizable
auth = Depends(verificar_api_key)

# ── Rate Limiting ─────────────────────────────────────────────────────────────
# Intenta usar Redis, cae a memoria si no está disponible
_rate_store = defaultdict(list)  # fallback en memoria
_RATE_LIMIT   = int(os.environ.get("RATE_LIMIT_RPM", "60"))   # requests por minuto
_RATE_WINDOW  = 60  # segundos

try:
    import redis as _redis_lib
    _redis_client = _redis_lib.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379"),
        decode_responses=True, socket_connect_timeout=1
    )
    _redis_client.ping()
    _REDIS_OK = True
except Exception:
    _redis_client = None
    _REDIS_OK     = False

def check_rate_limit(request: Request):
    """Rate limiting: max RATE_LIMIT_RPM requests por IP por minuto."""
    if _RATE_LIMIT == 0:
        return  # 0 = sin límite
    
    ip  = request.client.host if request.client else "unknown"
    now = time.time()
    key = f"rl:{ip}"

    if _REDIS_OK and _redis_client:
        # Redis: usar sliding window con sorted set
        pipe = _redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, now - _RATE_WINDOW)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, _RATE_WINDOW)
        _, _, count, _ = pipe.execute()
    else:
        # Fallback en memoria
        _rate_store[ip] = [t for t in _rate_store[ip] if now - t < _RATE_WINDOW]
        _rate_store[ip].append(now)
        count = len(_rate_store[ip])

    if count > _RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Demasiadas solicitudes. Límite: {_RATE_LIMIT}/min. Intenta en {_RATE_WINDOW}s.",
            headers={"Retry-After": str(_RATE_WINDOW), "X-RateLimit-Limit": str(_RATE_LIMIT)},
        )

rate_limit = Depends(check_rate_limit)

# Cache de instancias para no recargar el Excel en cada request
_cache: dict[str, Sistema] = {}

# ── Configuración de uploads seguros ─────────────────────────────────────────
UPLOAD_DIR        = Path(SCRIPT_DIR) / "storage" / "uploads"  # fuera del webroot
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".xlsx", ".xls"}
ALLOWED_MIMES      = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}
MAX_SIZE_MB   = 10
_SECRET_KEY   = os.environ.get("SECRET_KEY", secrets.token_hex(32))

def _mime_real(contenido: bytes) -> str:
    """Detecta mime type real por magic bytes, sin depender del nombre del archivo."""
    # xlsx: PK header (zip)
    if contenido[:2] == b"PK":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    # xls: D0 CF header
    if contenido[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "application/vnd.ms-excel"
    return "application/octet-stream"

def _generar_url_firmada(nombre_archivo: str, expira_minutos: int = 15) -> str:
    """Genera URL de descarga temporal firmada con HMAC — expira en N minutos."""
    expira = int((datetime.utcnow() + timedelta(minutes=expira_minutos)).timestamp())
    msg    = f"{nombre_archivo}{expira}".encode()
    token  = hmac.new(_SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()
    return f"/descargar/{nombre_archivo}?expira={expira}&token={token}"

def _verificar_url_firmada(nombre_archivo: str, expira: int, token: str) -> bool:
    """Verifica que la URL firmada sea válida y no haya expirado."""
    ahora = int(datetime.utcnow().timestamp())
    if ahora > expira:
        return False
    msg           = f"{nombre_archivo}{expira}".encode()
    token_esperado = hmac.new(_SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()
    return secrets.compare_digest(token, token_esperado)

def _sistema(empresa: str) -> Sistema:
    if empresa not in _cache:
        try:
            _cache[empresa] = Sistema(empresa)
        except FileNotFoundError as e:
            raise HTTPException(404, str(e))
        except Exception as e:
            raise HTTPException(500, f"Error cargando '{empresa}': {e}")
    return _cache[empresa]

def _empresas_disponibles() -> list[str]:
    carpeta = os.path.join(SCRIPT_DIR, "empresas")
    if not os.path.exists(carpeta):
        return []
    return [f[:-5] for f in os.listdir(carpeta) if f.endswith(".json")]


# ══════════════════════════════════════════════════════════════════════════════
# MODELOS
# ══════════════════════════════════════════════════════════════════════════════
class RegistroCreate(BaseModel):
    """Datos para crear/actualizar un registro. Acepta cualquier campo."""
    model_config = {"extra": "allow"}
    datos: dict = {}


class RegistroUpdate(BaseModel):
    datos: dict = {}


class ItemCotizacion(BaseModel):
    sku: str
    cantidad: int = Field(1, ge=1)
    descuento: float = Field(0.0, ge=0, le=1)
    obs: Optional[str] = None


class PedidoCotizacion(BaseModel):
    cliente: str
    telefono: Optional[str] = None
    numero: Optional[str] = None
    fecha: Optional[str] = None
    items: List[ItemCotizacion] = Field(..., min_length=1)
    generar_pdf: bool = False


# ══════════════════════════════════════════════════════════════════════════════
# INFO GLOBAL
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/generar-api-key", tags=["Info"], include_in_schema=False)
def generar_api_key():
    """Genera una API key segura para configurar en .env (solo en modo dev)."""
    if _API_KEY:
        raise HTTPException(403, "API key ya configurada. Deshabilitar en producción.")
    nueva = secrets.token_urlsafe(32)
    return {"api_key": nueva, "instruccion": f"Agregar al .env: API_KEY={nueva}"}



@app.get("/metrics", tags=["Info"], include_in_schema=False)
def metrics():
    """Endpoint Prometheus. Métricas básicas del sistema."""
    from jobs.cache import estadisticas as cache_stats
    from jobs.audit import stats as audit_stats

    try:
        c_stats = cache_stats()
        a_stats = audit_stats()
    except Exception:
        c_stats = {"total_keys": 0}
        a_stats = {"total": 0}

    empresas = _empresas_disponibles()
    lineas = [
        "# HELP kraftdo_empresas Número de empresas configuradas",
        "# TYPE kraftdo_empresas gauge",
        f"kraftdo_empresas {len(empresas)}",
        "# HELP kraftdo_cache_keys Total de keys en cache",
        "# TYPE kraftdo_cache_keys gauge",
        f"kraftdo_cache_keys {c_stats.get('total_keys', 0)}",
        "# HELP kraftdo_audit_events Total de eventos auditados",
        "# TYPE kraftdo_audit_events counter",
        f"kraftdo_audit_events {a_stats.get('total', 0)}",
        "# HELP kraftdo_redis_connected Redis disponible",
        "# TYPE kraftdo_redis_connected gauge",
        f"kraftdo_redis_connected {1 if _REDIS_OK else 0}",
    ]
    from fastapi.responses import Response
    return Response("\n".join(lineas), media_type="text/plain")

@app.get("/health", tags=["Info"], include_in_schema=False)
def health():
    """Healthcheck endpoint — usado por Docker."""
    empresas = _empresas_disponibles()
    return {
        "status":   "ok",
        "empresas": empresas,
        "redis":    _REDIS_OK,
        "rate_limit": _RATE_LIMIT,
    }

@app.get("/", tags=["Info"])
def root():
    empresas = _empresas_disponibles()
    return {
        "api":      "KraftDo API Universal v9",
        "empresas": empresas,
        "docs":     "/docs",
    }

@app.get("/empresas", tags=["Info"])
def listar_empresas(_=auth):
    """Lista todas las empresas configuradas."""
    empresas = _empresas_disponibles()
    resultado = []
    for nombre in empresas:
        try:
            s = _sistema(nombre)
            resultado.append({
                "id":     nombre,
                "nombre": s.cfg["empresa"]["nombre"],
                "modo":   s.modo,
                "hojas":  len(s.cfg["hojas"]),
            })
        except Exception:
            resultado.append({"id": nombre, "error": "No se pudo cargar"})
    return JSONResponse(resultado)


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS POR EMPRESA
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/{empresa}/info", tags=["Empresa"])
def info_empresa(empresa: str):
    s = _sistema(empresa)
    return JSONResponse({
        "empresa": s.cfg["empresa"],
        "fuente":  {"tipo": s.modo, "archivo": s.cfg["fuente"].get("archivo", "")},
        "hojas":   s.hojas_disponibles(),
    })

@app.get("/{empresa}/hojas", tags=["Empresa"])
def hojas(empresa: str):
    return JSONResponse(_sistema(empresa).hojas_disponibles())

# ── Catálogo ───────────────────────────────────────────────────────────────────
@app.get("/{empresa}/catalogo", tags=["Catálogo"])
@cached("catalogo", ttl=300)
def catalogo(empresa: str, solo_activos: bool = True, _rl=rate_limit):
    """Todos los catálogos de la empresa."""
    s = _sistema(empresa)
    cat = s.catalogo(solo_activos)
    totales = {k: len(v) for k, v in cat.items()}
    return JSONResponse({"totales": totales, "catalogo": cat})

@app.get("/{empresa}/catalogo/{alias}", tags=["Catálogo"])
def catalogo_hoja(empresa: str, alias: str, solo_activos: bool = True):
    """Productos de una hoja de catálogo específica."""
    s = _sistema(empresa)
    cat = s.catalogo(solo_activos)
    if alias not in cat:
        raise HTTPException(404, f"'{alias}' no es un catálogo. Disponibles: {list(cat.keys())}")
    return JSONResponse({"alias": alias, "total": len(cat[alias]), "productos": cat[alias]})

@app.get("/{empresa}/precio", tags=["Catálogo"])
def precio(empresa: str, sku: str, cantidad: int = 1, _rl=rate_limit):
    """
    Precio exacto para SKU + cantidad.
    Usado por n8n en el bot: GET /kraftdo/precio?sku=A01&cantidad=3
    """
    s = _sistema(empresa)
    r = s.precio(sku.upper(), cantidad)
    if r is None:
        raise HTTPException(404, f"SKU '{sku}' no encontrado en el catálogo de '{empresa}'.")
    return JSONResponse(r)

@app.get("/{empresa}/buscar", tags=["Catálogo"])
def buscar(empresa: str, q: str):
    """Búsqueda libre en nombre/variante de productos."""
    s = _sistema(empresa)
    resultados = s.buscar(q)
    return JSONResponse({"query": q, "total": len(resultados), "resultados": resultados})

# ── Cotizador ─────────────────────────────────────────────────────────────────
@app.post("/{empresa}/cotizar", tags=["Cotizador"])
def cotizar(empresa: str, datos: PedidoCotizacion, _=auth, _rl=rate_limit):
    """
    Calcula cotización completa con IVA, anticipo y saldo.
    Si generar_pdf=true y kraftdo_pdf.py está disponible, incluye PDF en base64.
    Usado por n8n para responder al cliente en el bot.
    """
    s = _sistema(empresa)
    items = [
        {"sku": i.sku, "cantidad": i.cantidad, "descuento": i.descuento, "obs": i.obs}
        for i in datos.items
    ]
    resultado = s.cotizar(items, datos.cliente, datos.telefono or "")
    resultado["numero"] = datos.numero or "COT-001"

    if datos.generar_pdf and PDF_OK:
        try:
            import base64
            pdf_data = {
                "cliente":       datos.cliente,
                "telefono":      datos.telefono or "",
                "numero":        resultado["numero"],
                "fecha":         resultado["fecha"],
                "productos":     [{
                    "sku":       l["sku"], "producto": l["producto"],
                    "cantidad":  l["cantidad"], "precio": l["precio_unitario"],
                    "descuento": l["descuento"], "subtotal": l["subtotal"],
                    "obs":       l.get("obs", ""),
                } for l in resultado["lineas"]],
                "subtotal_neto": resultado["subtotal_neto"],
                "iva":           resultado["iva"],
                "total":         resultado["total"],
                "anticipo":      resultado["anticipo"],
                "saldo":         resultado["saldo"],
            }
            pdf_bytes = generar_cotizacion(pdf_data)
            resultado["pdf_base64"] = base64.b64encode(pdf_bytes).decode()
            resultado["pdf_nombre"] = f"{empresa}_cotizacion_{datos.cliente[:15].replace(' ','_')}.pdf"
        except Exception as e:
            resultado["pdf_error"] = str(e)

    return JSONResponse(resultado)

@app.post("/{empresa}/pdf/cotizacion", tags=["PDFs"],
          response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def pdf_cotizacion(empresa: str, datos: PedidoCotizacion):
    """Genera y descarga PDF de cotización directamente."""
    if not PDF_OK:
        raise HTTPException(500, "kraftdo_pdf.py no disponible")
    datos.generar_pdf = True
    r = cotizar(empresa, datos)
    body = json.loads(r.body)
    if "pdf_base64" in body:
        import base64
        return Response(
            base64.b64decode(body["pdf_base64"]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{body["pdf_nombre"]}"'},
        )
    raise HTTPException(500, body.get("pdf_error", "PDF no generado"))

# ── Registros ─────────────────────────────────────────────────────────────────

@app.get("/{empresa}/registros/{alias}/paginado", tags=["Registros"])
def registros_paginados(
    empresa: str,
    alias:   str,
    page:    int = 1,
    per_page: int = 50,
    _rl = rate_limit
):
    """
    Versión paginada del endpoint /registros/{alias}.
    Devuelve los resultados en páginas de per_page elementos.
    """
    s = _sistema(empresa)
    try:
        todos = s.registros(alias)
    except Exception as e:
        raise HTTPException(404, str(e))

    total      = len(todos)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page       = max(1, min(page, total_pages))
    start      = (page - 1) * per_page
    end        = start + per_page

    return JSONResponse({
        "data":        todos[start:end],
        "pagination":  {
            "page":        page,
            "per_page":    per_page,
            "total":       total,
            "total_pages": total_pages,
            "has_next":    page < total_pages,
            "has_prev":    page > 1,
        }
    })

@app.get("/{empresa}/registros/{alias}", tags=["Registros"])
@cached("registros", ttl=120)
def registros(
    empresa: str,
    alias:   str,
    request: Request,
    solo_activos: bool = False,
    _rl=rate_limit,
):
    """
    GET con filtros dinámicos — cualquier query param es un filtro.

    Operadores: campo=valor | campo__gt=5 | campo__like=texto | campo__in=A,B
    Ejemplos:
        GET /kraftdo/registros/pedidos?estado=Confirmado
        GET /kraftdo/registros/pedidos?total__gt=50000&ciudad=Rancagua
        GET /kraftdo/registros/clientes?nombre__like=juan
    """
    s = _sistema(empresa)
    try:
        # Extraer filtros de los query params (excluyendo solo_activos)
        reservados = {"solo_activos"}
        filtros = {
            k: v for k, v in request.query_params.items()
            if k not in reservados
        }

        if filtros:
            filas = s.buscar_filtros(alias, filtros)
        else:
            filas = s.registros(alias, solo_activos)
    except KeyError as e:
        raise HTTPException(404, str(e))
    return JSONResponse({"alias": alias, "total": len(filas), "registros": filas, "filtros": filtros})


@app.post("/{empresa}/query/{alias}", tags=["Registros"])
async def query_sql(empresa: str, alias: str, request: Request, _rl=rate_limit):
    """
    SQL directo sobre cualquier hoja via DuckDB.
    
    Body JSON: {"where": "estado = 'Activo' AND total > 50000"}
    Soporta: WHERE, ORDER BY, LIMIT, expresiones, funciones de agregación.
    No requiere SELECT ni FROM — solo la condición/expresión.
    
    Ejemplos:
        {"where": "total > 50000"}
        {"where": "estado = 'Confirmado' ORDER BY fecha DESC LIMIT 10"}
        {"where": "ciudad ILIKE '%rancagua%'"}
    """
    s = _sistema(empresa)
    try:
        body = await request.json()
        sql_where = body.get("where", "TRUE")
        filas = s.query(alias, sql_where)
        return JSONResponse({"alias": alias, "total": len(filas), "registros": filas, "sql": sql_where})
    except KeyError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(400, f"Error SQL: {e}")


@app.get("/{empresa}/registros/{alias}/schema", tags=["Registros"])
def schema_hoja(empresa: str, alias: str):
    """
    Retorna el schema de una hoja — campos, tipos y restricciones.
    Usado por el formulario dinámico del classifier.
    """
    s = _sistema(empresa)
    try:
        return JSONResponse(s.schema(alias))
    except KeyError as e:
        raise HTTPException(404, str(e))


@app.get("/{empresa}/registros/{alias}/{id_valor}", tags=["Registros"])
def registro_por_id(empresa: str, alias: str, id_valor: str, _rl=rate_limit):
    """GET de un registro específico por su identificador."""
    s = _sistema(empresa)
    ident = s._cfg_hoja(alias).get("identificador")
    if not ident:
        raise HTTPException(400, f"La hoja '{alias}' no tiene campo identificador configurado")
    filas = s.buscar_filtros(alias, {ident: id_valor})
    if not filas:
        raise HTTPException(404, f"Registro '{id_valor}' no encontrado en '{alias}'")
    return JSONResponse(filas[0])


@app.post("/{empresa}/registros/{alias}", tags=["Registros"])
async def crear_registro(empresa: str, alias: str, request: Request, _=auth, _rl=rate_limit):
    """
    POST — Agrega una fila nueva al Excel o Google Sheet.
    Calcula campos derivados automáticamente (total, anticipo, saldo).
    """
    s    = _sistema(empresa)
    body = await request.json()
    try:
        resultado = s.crear(alias, body)
        # Limpiar cache de la empresa para reflejar cambios
        if empresa in _cache:
            del _cache[empresa]
        cache_invalidar("registros", empresa)
        cache_invalidar("catalogo", empresa)
        return JSONResponse(resultado, status_code=201)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))


@app.put("/{empresa}/registros/{alias}/{id_valor}", tags=["Registros"])
async def actualizar_registro(
    empresa: str, alias: str, id_valor: str,
    request: Request, _=auth, _rl=rate_limit
):
    """
    PUT — Modifica campos de un registro existente identificado por su ID.
    Solo actualiza los campos que vienen en el body.
    """
    s    = _sistema(empresa)
    body = await request.json()
    try:
        resultado = s.actualizar(alias, id_valor, body)
        if empresa in _cache:
            del _cache[empresa]
        return JSONResponse(resultado)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))


@app.delete("/{empresa}/registros/{alias}/{id_valor}", tags=["Registros"])
def eliminar_registro(empresa: str, alias: str, id_valor: str, _=auth, _rl=rate_limit):
    """
    DELETE — Elimina la fila con ese identificador del Excel o Google Sheet.
    """
    s = _sistema(empresa)
    try:
        resultado = s.eliminar(alias, id_valor)
        if empresa in _cache:
            del _cache[empresa]
        return JSONResponse(resultado)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))

# ── KPIs ──────────────────────────────────────────────────────────────────────
@app.get("/{empresa}/kpis", tags=["Dashboard"])
def kpis(empresa: str):
    """Métricas del dashboard (celdas de resumen configuradas en el JSON)."""
    s = _sistema(empresa)
    return JSONResponse(s.kpis())


# ── Upload seguro ─────────────────────────────────────────────────────────────
@app.post("/upload/{empresa}", tags=["Upload"], dependencies=[auth])
async def upload_excel(empresa: str, file: UploadFile = File(...)):
    """
    Sube un Excel de forma segura para una empresa.
    - Valida extensión y mime type real (magic bytes)
    - Límite de 10MB
    - Nombre aleatorio — nunca el original
    - Guardado en /storage/uploads/, fuera del webroot
    - Retorna URL firmada temporal (15 min) para descarga
    """
    # 1. Validar extensión
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Solo se aceptan archivos .xlsx o .xls")

    # 2. Leer contenido
    contenido = await file.read()

    # 3. Validar tamaño
    if len(contenido) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"Archivo demasiado grande. Máximo: {MAX_SIZE_MB}MB")

    # 4. Validar mime real por magic bytes (no por nombre)
    mime_real = _mime_real(contenido)
    if mime_real not in ALLOWED_MIMES:
        raise HTTPException(400, "El contenido del archivo no corresponde a un Excel válido")

    # 5. Guardar con nombre aleatorio en carpeta privada
    nombre_seguro = f"{empresa}_{uuid4().hex}{ext}"
    destino       = UPLOAD_DIR / nombre_seguro
    destino.write_bytes(contenido)

    # 6. Retornar URL firmada temporal
    url_firmada = _generar_url_firmada(nombre_seguro, expira_minutos=15)
    return JSONResponse({
        "archivo":    nombre_seguro,
        "empresa":    empresa,
        "size_kb":    round(len(contenido) / 1024, 1),
        "url_descarga": url_firmada,
        "expira_en":  "15 minutos",
    }, status_code=201)


@app.get("/descargar/{nombre_archivo}", tags=["Upload"])
def descargar_excel(nombre_archivo: str, expira: int, token: str):
    """
    Descarga un archivo Excel via URL firmada temporal.
    La URL expira en 15 minutos y no es reutilizable indefinidamente.
    """
    if not _verificar_url_firmada(nombre_archivo, expira, token):
        raise HTTPException(403, "URL inválida o expirada")

    ruta = UPLOAD_DIR / nombre_archivo
    if not ruta.exists():
        raise HTTPException(404, "Archivo no encontrado")

    return FileResponse(
        ruta,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=nombre_archivo,
    )


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    empresas = _empresas_disponibles()
    print(f"""
╔══════════════════════════════════════════════════════╗
║       KraftDo API Universal v9 — Iniciando          ║
╚══════════════════════════════════════════════════════╝

📁 Empresas cargadas: {', '.join(empresas) or 'ninguna'}
🐍 Python: {sys.version.split()[0]}
📄 PDF:    {'OK' if PDF_OK else 'Sin kraftdo_pdf.py'}

🚀 http://localhost:8000
📚 http://localhost:8000/docs
""")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
