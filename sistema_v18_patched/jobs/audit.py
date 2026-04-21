"""
audit.py — Logs de auditoría
Registra quién hizo qué y cuándo. Crítico si hay disputas con clientes.
"""
import os, json, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent.parent
DB_PATH    = SCRIPT_DIR / "storage" / "audit.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _init_db():
    """Crea la tabla audit_log si no existe."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  TEXT NOT NULL,
            usuario    TEXT,
            empresa    TEXT,
            accion     TEXT NOT NULL,
            recurso    TEXT,
            detalle    TEXT,
            ip         TEXT,
            user_agent TEXT,
            resultado  TEXT DEFAULT 'ok'
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_usuario   ON audit_log(usuario)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_empresa   ON audit_log(empresa)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_accion    ON audit_log(accion)")
    conn.commit()
    conn.close()

_init_db()


def log_action(
    accion:   str,
    usuario:  str = None,
    empresa:  str = None,
    recurso:  str = None,
    detalle:  Optional[dict] = None,
    ip:       str = None,
    user_agent: str = None,
    resultado: str = "ok",
):
    """
    Registra una acción en el audit log.

    Ejemplos:
      log_action("upload_excel", empresa="adille", ip="1.2.3.4",
                 detalle={"archivo": "marzo.xlsx", "size_kb": 256})
      log_action("crear_registro", empresa="extractores",
                 recurso="ventas", detalle={"sku": "EXT-60W"})
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO audit_log
            (timestamp, usuario, empresa, accion, recurso, detalle, ip, user_agent, resultado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            usuario or "anonimo",
            empresa,
            accion,
            recurso,
            json.dumps(detalle, default=str) if detalle else None,
            ip,
            user_agent,
            resultado,
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        # Nunca dejar que el audit rompa la aplicación
        print(f"⚠️  audit log falló: {e}")


def query_logs(
    usuario: str = None,
    empresa: str = None,
    accion:  str = None,
    desde:   str = None,
    hasta:   str = None,
    limit:   int = 100,
) -> list[dict]:
    """Consulta logs con filtros."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM audit_log WHERE 1=1"
    params = []

    if usuario:
        query  += " AND usuario = ?"
        params.append(usuario)
    if empresa:
        query  += " AND empresa = ?"
        params.append(empresa)
    if accion:
        query  += " AND accion = ?"
        params.append(accion)
    if desde:
        query  += " AND timestamp >= ?"
        params.append(desde)
    if hasta:
        query  += " AND timestamp <= ?"
        params.append(hasta)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return rows


def stats() -> dict:
    """Estadísticas del audit log."""
    conn = sqlite3.connect(DB_PATH)
    total   = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    empresas= conn.execute("SELECT empresa, COUNT(*) FROM audit_log GROUP BY empresa").fetchall()
    acciones= conn.execute("SELECT accion, COUNT(*) FROM audit_log GROUP BY accion").fetchall()
    conn.close()
    return {
        "total":    total,
        "empresas": dict(empresas),
        "acciones": dict(acciones),
    }
