"""
crypto.py — Cifrado simétrico AES para datos sensibles en la BD
Usa Fernet (AES-128-CBC + HMAC-SHA256 + timestamp).

Uso:
    from jobs.crypto import cifrar, descifrar

    rut_cifrado = cifrar("12345678-9")  # "gAAAAABh..."
    rut_original = descifrar(rut_cifrado)  # "12345678-9"
"""
import os, base64
from functools import lru_cache

try:
    from cryptography.fernet import Fernet, InvalidToken
    CRYPTO_OK = True
except ImportError:
    CRYPTO_OK = False


@lru_cache(maxsize=1)
def _fernet():
    """Carga la clave de cifrado desde env. Si no existe, genera una (SOLO DEV)."""
    if not CRYPTO_OK:
        return None

    key = os.environ.get("ENCRYPTION_KEY", "")
    if not key:
        # En desarrollo generamos una temporal. En producción DEBE venir del .env
        print("⚠️  ENCRYPTION_KEY no configurada — usando clave temporal")
        print("⚠️  En producción: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
        key = Fernet.generate_key().decode()

    # La clave debe ser 32 bytes base64url. Si vino como string simple, la derivamos
    try:
        # Verificar que es una clave válida
        Fernet(key.encode() if isinstance(key, str) else key)
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        # Derivar clave válida desde el string
        import hashlib
        derivada = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
        return Fernet(derivada)


def cifrar(texto: str) -> str:
    """Cifra un string. Devuelve string base64url."""
    if not texto:
        return ""
    f = _fernet()
    if not f:
        return texto  # Sin crypto disponible, pasa plano (para desarrollo)
    return f.encrypt(str(texto).encode()).decode()


def descifrar(texto_cifrado: str) -> str:
    """Descifra un string previamente cifrado."""
    if not texto_cifrado:
        return ""
    f = _fernet()
    if not f:
        return texto_cifrado
    try:
        return f.decrypt(texto_cifrado.encode()).decode()
    except InvalidToken:
        # Si no está cifrado (datos legacy), devolver tal cual
        return texto_cifrado
    except Exception:
        return ""


# ── Campos que SIEMPRE deben cifrarse ──────────────────────────────────────────
CAMPOS_SENSIBLES = {
    "rut", "run", "dni", "cedula", "nif",
    "tarjeta", "cvv", "iban", "cuenta_bancaria",
    "token_api", "password_cliente",
    "salario", "liquido_pagar",  # datos de RR.HH.
}


def cifrar_dict(datos: dict) -> dict:
    """Cifra automáticamente los campos sensibles de un diccionario."""
    resultado = {}
    for k, v in datos.items():
        k_lower = k.lower().strip()
        if any(campo in k_lower for campo in CAMPOS_SENSIBLES) and v:
            resultado[k] = cifrar(str(v))
        else:
            resultado[k] = v
    return resultado


def descifrar_dict(datos: dict) -> dict:
    """Descifra automáticamente los campos sensibles de un diccionario."""
    resultado = {}
    for k, v in datos.items():
        k_lower = k.lower().strip()
        if any(campo in k_lower for campo in CAMPOS_SENSIBLES) and v:
            resultado[k] = descifrar(str(v))
        else:
            resultado[k] = v
    return resultado
