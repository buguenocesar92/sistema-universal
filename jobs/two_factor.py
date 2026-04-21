"""
two_factor.py — Autenticación en 2 pasos con TOTP
Compatible con Google Authenticator, Authy, 1Password, Microsoft Authenticator.
"""
import os, secrets, sqlite3
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).parent.parent
DB_PATH    = SCRIPT_DIR / "storage" / "auth.db"

try:
    import pyotp
    TOTP_OK = True
except ImportError:
    TOTP_OK = False


def _init_tabla():
    """Agrega columnas de 2FA a la tabla usuarios si no existen."""
    conn = sqlite3.connect(DB_PATH)
    cols = [c[1] for c in conn.execute("PRAGMA table_info(usuarios)").fetchall()]
    if "totp_secret" not in cols:
        conn.execute("ALTER TABLE usuarios ADD COLUMN totp_secret TEXT")
    if "totp_activo" not in cols:
        conn.execute("ALTER TABLE usuarios ADD COLUMN totp_activo INTEGER DEFAULT 0")
    if "backup_codes" not in cols:
        conn.execute("ALTER TABLE usuarios ADD COLUMN backup_codes TEXT")
    conn.commit()
    conn.close()


def activar_2fa(email: str) -> dict:
    """
    Genera un secret TOTP nuevo para el usuario.
    Retorna la URL del QR code que se escanea con Google Authenticator.
    """
    if not TOTP_OK:
        return {"error": "pyotp no instalado"}

    _init_tabla()
    conn = sqlite3.connect(DB_PATH)
    usr  = conn.execute("SELECT id FROM usuarios WHERE email = ?", (email,)).fetchone()
    if not usr:
        conn.close()
        return {"error": "Usuario no encontrado"}

    secret = pyotp.random_base32()
    codes  = [secrets.token_hex(4) for _ in range(8)]  # 8 códigos de recuperación

    conn.execute(
        "UPDATE usuarios SET totp_secret = ?, backup_codes = ?, totp_activo = 0 WHERE id = ?",
        (secret, ",".join(codes), usr[0])
    )
    conn.commit()
    conn.close()

    totp = pyotp.TOTP(secret)
    qr_url = totp.provisioning_uri(name=email, issuer_name="KraftDo")

    return {
        "secret":         secret,
        "qr_url":         qr_url,
        "backup_codes":   codes,
        "instrucciones": "Escanea el QR con Google Authenticator. Guarda los códigos de respaldo en un lugar seguro."
    }


def confirmar_2fa(email: str, codigo: str) -> bool:
    """
    Confirma la activación del 2FA verificando el primer código TOTP.
    Una vez activo, el usuario SIEMPRE necesitará el código para loguearse.
    """
    if not TOTP_OK:
        return False

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    usr = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    if not usr or not usr["totp_secret"]:
        conn.close()
        return False

    totp = pyotp.TOTP(usr["totp_secret"])
    if totp.verify(codigo, valid_window=1):
        conn.execute("UPDATE usuarios SET totp_activo = 1 WHERE id = ?", (usr["id"],))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False


def verificar_2fa(email: str, codigo: str) -> bool:
    """Verifica un código TOTP o un backup code durante login."""
    if not TOTP_OK:
        return False

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    usr = conn.execute(
        "SELECT * FROM usuarios WHERE email = ? AND totp_activo = 1",
        (email,)
    ).fetchone()
    if not usr:
        conn.close()
        return True  # usuario sin 2FA no necesita código

    # Intentar TOTP primero
    totp = pyotp.TOTP(usr["totp_secret"])
    if totp.verify(codigo, valid_window=1):
        conn.close()
        return True

    # Probar backup codes
    codes = (usr["backup_codes"] or "").split(",")
    if codigo in codes:
        codes.remove(codigo)
        conn.execute(
            "UPDATE usuarios SET backup_codes = ? WHERE id = ?",
            (",".join(codes), usr["id"])
        )
        conn.commit()
        conn.close()
        return True

    conn.close()
    return False


def desactivar_2fa(email: str, password_confirmacion: str) -> bool:
    """Desactiva 2FA (requiere confirmación de password)."""
    from jobs.auth import verificar_password

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    usr = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    if not usr or not verificar_password(password_confirmacion, usr["password"]):
        conn.close()
        return False

    conn.execute(
        "UPDATE usuarios SET totp_secret = NULL, totp_activo = 0, backup_codes = NULL WHERE id = ?",
        (usr["id"],)
    )
    conn.commit()
    conn.close()
    return True
