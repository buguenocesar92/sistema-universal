"""
audit.py — Sistema de logs de auditoría

Registra QUIÉN hizo QUÉ y CUÁNDO.
Guarda en SQLite local por simplicidad (fácil migrar a MySQL después).

Uso:
    from audit import log
    log("login",    user="jonathan@adille.cl", detalle="OK")
    log("upload",   user="jonathan@adille.cl", recurso="adille.xlsx")
    log("delete",   user="cesar@kraftdo.cl",   recurso="pedido/KDO-001")
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from contextlib import contextmanager

SCRIPT_DIR = Path(__file__).parent
DB_PATH    = SCRIPT_DIR / "storage" / "audit.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Init schema ───────────────────────────────────────────────────────────────
def _init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                accion      TEXT NOT NULL,
                usuario     TEXT,
                ip          TEXT,
                user_agent  TEXT,
                recurso     TEXT,
                empresa     TEXT,
                detalle     TEXT,
                exitoso     INTEGER DEFAULT 1
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_usuario   ON audit_log(usuario)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_accion    ON audit_log(accion)")

_init_db()

# ── API pública ───────────────────────────────────────────────────────────────
def log(accion: str,
        usuario: Optional[str] = None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        recurso: Optional[str] = None,
        empresa: Optional[str] = None,
        detalle: Optional[str] = None,
        exitoso: bool = True):
    """
    Registra una acción en el audit log.
    
    Acciones comunes:
    - login, logout, login_failed
    - upload, download, delete
    - create, update, read
    - permission_denied, rate_limit_exceeded
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO audit_log
                (timestamp, accion, usuario, ip, user_agent, recurso, empresa, detalle, exitoso)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                accion, usuario, ip, user_agent,
                recurso, empresa,
                json.dumps(detalle) if isinstance(detalle, dict) else detalle,
                1 if exitoso else 0,
            ))
    except Exception as e:
        # No fallar la app por un error de audit
        print(f"[AUDIT ERROR] {e}")

def query(limit: int = 100,
          usuario: Optional[str] = None,
          accion: Optional[str]  = None,
          empresa: Optional[str] = None,
          desde: Optional[str]   = None) -> list:
    """Consulta el audit log con filtros opcionales."""
    sql    = "SELECT * FROM audit_log WHERE 1=1"
    params = []
    if usuario: sql += " AND usuario = ?"; params.append(usuario)
    if accion:  sql += " AND accion = ?";  params.append(accion)
    if empresa: sql += " AND empresa = ?"; params.append(empresa)
    if desde:   sql += " AND timestamp >= ?"; params.append(desde)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

def stats(dias: int = 7) -> dict:
    """Estadísticas de actividad de los últimos N días."""
    with sqlite3.connect(DB_PATH) as conn:
        desde = datetime.now(timezone.utc).isoformat()
        # Total por acción
        por_accion = dict(conn.execute("""
            SELECT accion, COUNT(*) FROM audit_log
            WHERE timestamp >= datetime('now', ?)
            GROUP BY accion ORDER BY 2 DESC
        """, (f"-{dias} days",)).fetchall())

        # Usuarios más activos
        por_usuario = dict(conn.execute("""
            SELECT usuario, COUNT(*) FROM audit_log
            WHERE timestamp >= datetime('now', ?) AND usuario IS NOT NULL
            GROUP BY usuario ORDER BY 2 DESC LIMIT 10
        """, (f"-{dias} days",)).fetchall())

        # Errores
        errores = conn.execute("""
            SELECT COUNT(*) FROM audit_log
            WHERE timestamp >= datetime('now', ?) AND exitoso = 0
        """, (f"-{dias} days",)).fetchone()[0]

        return {
            "dias":        dias,
            "por_accion":  por_accion,
            "por_usuario": por_usuario,
            "errores":     errores,
        }

# ── Middleware FastAPI helper ─────────────────────────────────────────────────
@contextmanager
def audit_context(accion: str, **kwargs):
    """
    Context manager para loggear automáticamente éxito/fallo de una acción.
    
    Uso:
        with audit_context("upload", usuario="x@y.cl", recurso="file.xlsx"):
            procesar_archivo()
    """
    try:
        yield
        log(accion, exitoso=True, **kwargs)
    except Exception as e:
        log(accion, exitoso=False, detalle=str(e), **kwargs)
        raise
