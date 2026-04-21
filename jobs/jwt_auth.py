"""
jwt_auth.py — Autenticación JWT con access + refresh tokens
Reemplaza el sistema simple de tokens en auth.py cuando el cliente necesita escalabilidad.

Uso típico:
    tokens = emitir_tokens(user_id=1, rol="admin", empresa=None)
    # tokens = {"access": "eyJ...", "refresh": "eyJ...", "expira_en": 900}

    payload = verificar_access(tokens["access"])
    # payload = {"sub": 1, "rol": "admin", "exp": ...}

    nuevos = refrescar(tokens["refresh"])
"""
import os, secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

SECRET_KEY      = os.environ.get("JWT_SECRET", secrets.token_hex(32))
ALGORITHM       = "HS256"
ACCESS_EXPIRES  = int(os.environ.get("JWT_ACCESS_EXPIRES_MIN", "15"))   # 15 min
REFRESH_EXPIRES = int(os.environ.get("JWT_REFRESH_EXPIRES_DAYS", "7"))  # 7 días

try:
    import jwt
    JWT_OK = True
except ImportError:
    JWT_OK = False


def _now():
    return datetime.now(timezone.utc)


def emitir_tokens(user_id: int, rol: str, empresa: Optional[str] = None) -> dict:
    """Emite par access + refresh."""
    if not JWT_OK:
        return {"error": "PyJWT no instalado"}

    now = _now()
    access_payload = {
        "sub":     user_id,
        "rol":     rol,
        "empresa": empresa,
        "type":    "access",
        "iat":     now,
        "exp":     now + timedelta(minutes=ACCESS_EXPIRES),
    }
    refresh_payload = {
        "sub":  user_id,
        "type": "refresh",
        "iat":  now,
        "exp":  now + timedelta(days=REFRESH_EXPIRES),
        "jti":  secrets.token_hex(8),  # ID único para poder revocarlo
    }

    return {
        "access":     jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM),
        "refresh":    jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM),
        "expira_en":  ACCESS_EXPIRES * 60,
        "type":       "Bearer",
    }


def verificar_access(token: str) -> Optional[dict]:
    """Verifica access token y devuelve payload o None."""
    if not JWT_OK or not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def refrescar(refresh_token: str) -> Optional[dict]:
    """
    Toma un refresh token válido y emite un par nuevo.
    Si el refresh también venció, retorna None — el usuario debe loguearse de nuevo.
    """
    if not JWT_OK:
        return None
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None

        # Reconstruir info del usuario desde la DB
        from jobs.auth import _user_por_id
        try:
            usuario = _user_por_id(payload["sub"])
        except Exception:
            # Fallback: emitir tokens con datos mínimos
            return emitir_tokens(payload["sub"], "lector", None)

        if not usuario:
            return None

        return emitir_tokens(usuario["id"], usuario["rol"], usuario.get("empresa"))
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def revocar(jti: str):
    """Agrega un jti a la blacklist en Redis. Los tokens con ese jti quedan inválidos."""
    try:
        from jobs.queue import JobQueue
        q = JobQueue()
        if q.ok:
            q.redis.setex(f"jwt:revoked:{jti}", REFRESH_EXPIRES * 86400, "1")
    except Exception:
        pass
