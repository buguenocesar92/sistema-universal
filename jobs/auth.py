"""
auth.py — Sistema de permisos simple por rol
Roles:
  - admin:    acceso total (César)
  - empresa:  solo ve datos de SU empresa (Jonathan, Karen)
  - lector:   solo lectura (reportes, KPIs)
"""
import os, json, hashlib, secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import sqlite3

SCRIPT_DIR = Path(__file__).parent.parent
DB_PATH    = SCRIPT_DIR / "storage" / "auth.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

ROLES = {
    "admin":   {"todo": True},
    "empresa": {"ver_propia": True, "editar_propia": True},
    "lector":  {"ver_propia": True},
}

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            rol        TEXT NOT NULL DEFAULT 'lector',
            empresa    TEXT,
            token      TEXT,
            token_exp  TEXT,
            creado     TEXT NOT NULL,
            activo     INTEGER DEFAULT 1
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_email ON usuarios(email)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_token ON usuarios(token)")
    conn.commit()
    conn.close()

_init_db()


def hash_password(pwd: str) -> str:
    """Hash SHA256 con salt único. Para prod usar bcrypt."""
    salt = secrets.token_hex(8)
    h    = hashlib.sha256(f"{salt}:{pwd}".encode()).hexdigest()
    return f"{salt}:{h}"


def verificar_password(pwd: str, hash_stored: str) -> bool:
    try:
        salt, h = hash_stored.split(":", 1)
        return secrets.compare_digest(h, hashlib.sha256(f"{salt}:{pwd}".encode()).hexdigest())
    except Exception:
        return False


def crear_usuario(email: str, password: str, rol: str = "lector", empresa: str = None) -> dict:
    """Crea un usuario nuevo."""
    if rol not in ROLES:
        raise ValueError(f"Rol inválido: {rol}. Válidos: {list(ROLES)}")
    if rol in ("empresa", "lector") and not empresa:
        raise ValueError(f"Rol '{rol}' requiere especificar 'empresa'")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT INTO usuarios (email, password, rol, empresa, creado)
            VALUES (?, ?, ?, ?, ?)
        """, (email, hash_password(password), rol, empresa, datetime.now(timezone.utc).replace(tzinfo=None).isoformat()))
        conn.commit()
        return {"email": email, "rol": rol, "empresa": empresa}
    except sqlite3.IntegrityError:
        raise ValueError(f"El email {email} ya está registrado")
    finally:
        conn.close()


def login(email: str, password: str) -> Optional[dict]:
    """Genera un token de sesión válido 24h."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    usr = conn.execute(
        "SELECT * FROM usuarios WHERE email = ? AND activo = 1",
        (email,)
    ).fetchone()

    if not usr or not verificar_password(password, usr["password"]):
        conn.close()
        return None

    token     = secrets.token_urlsafe(32)
    token_exp = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24)).isoformat()
    conn.execute(
        "UPDATE usuarios SET token = ?, token_exp = ? WHERE id = ?",
        (token, token_exp, usr["id"])
    )
    conn.commit()
    conn.close()

    return {
        "token":   token,
        "email":   usr["email"],
        "rol":     usr["rol"],
        "empresa": usr["empresa"],
        "expira":  token_exp,
    }


def verificar_token(token: str) -> Optional[dict]:
    """Valida un token de sesión."""
    if not token:
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    usr = conn.execute(
        "SELECT * FROM usuarios WHERE token = ? AND activo = 1",
        (token,)
    ).fetchone()
    conn.close()

    if not usr:
        return None
    if datetime.fromisoformat(usr["token_exp"]) < datetime.now(timezone.utc).replace(tzinfo=None):
        return None

    return dict(usr)


def puede_acceder(usuario: dict, empresa: str, accion: str = "ver") -> bool:
    """Verifica si el usuario puede hacer la acción sobre la empresa."""
    if not usuario:
        return False
    if usuario["rol"] == "admin":
        return True
    if usuario["empresa"] != empresa:
        return False
    if accion == "editar" and usuario["rol"] == "lector":
        return False
    return True


def _user_por_id(user_id: int) -> Optional[dict]:
    """Busca un usuario por ID (usado por jwt_auth para refresh)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    usr = conn.execute(
        "SELECT * FROM usuarios WHERE id = ? AND activo = 1",
        (user_id,)
    ).fetchone()
    conn.close()
    return dict(usr) if usr else None
