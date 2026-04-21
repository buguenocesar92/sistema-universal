"""
auth.py — Sistema de autenticación JWT con roles

Implementa:
- JWT con expiración (24h) + refresh token (7 días)
- Roles: admin, cliente, lector
- Hashing bcrypt de contraseñas
- Dependency injection para FastAPI

Uso en endpoints:
    @app.get("/protegido")
    def endpoint(user = Depends(require_auth)):
        return {"usuario": user["email"]}
    
    @app.get("/solo-admin")
    def endpoint(user = Depends(require_role("admin"))):
        ...
"""
import os
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

try:
    import bcrypt
    BCRYPT_OK = True
except ImportError:
    BCRYPT_OK = False

try:
    from jose import jwt, JWTError
    JWT_OK = True
except ImportError:
    JWT_OK = False

SCRIPT_DIR = Path(__file__).parent
USERS_FILE = SCRIPT_DIR / "storage" / "users.json"
USERS_FILE.parent.mkdir(parents=True, exist_ok=True)

# ── Configuración ─────────────────────────────────────────────────────────────
SECRET_KEY      = os.environ.get("JWT_SECRET", "")
ALGORITHM       = "HS256"
ACCESS_EXPIRE   = 24 * 60      # minutos
REFRESH_EXPIRE  = 7 * 24 * 60  # minutos

if not SECRET_KEY:
    import secrets
    SECRET_KEY = secrets.token_hex(32)
    print(f"⚠️  JWT_SECRET no configurado — generado temporal (cambiar en .env)")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# ── Roles y permisos ──────────────────────────────────────────────────────────
ROLES = {
    "admin":   ["*"],                                      # todo
    "cliente": ["read:own", "write:own", "upload:own"],    # solo sus datos
    "lector":  ["read:own"],                               # solo lectura
}

def tiene_permiso(user_rol: str, permiso_necesario: str) -> bool:
    permisos = ROLES.get(user_rol, [])
    return "*" in permisos or permiso_necesario in permisos

# ── Hashing de contraseñas ────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    if not BCRYPT_OK:
        raise RuntimeError("bcrypt no instalado: pip install bcrypt")
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verificar_password(password: str, password_hash: str) -> bool:
    if not BCRYPT_OK:
        raise RuntimeError("bcrypt no instalado")
    return bcrypt.checkpw(password.encode(), password_hash.encode())

# ── Gestión de usuarios (JSON file — para producción usar BD) ─────────────────
def cargar_usuarios() -> dict:
    if not USERS_FILE.exists():
        return {}
    try:
        return json.loads(USERS_FILE.read_text())
    except:
        return {}

def guardar_usuarios(usuarios: dict):
    USERS_FILE.write_text(json.dumps(usuarios, indent=2))

def crear_usuario(email: str, password: str, rol: str = "cliente",
                  empresa: Optional[str] = None) -> dict:
    if rol not in ROLES:
        raise ValueError(f"Rol inválido. Opciones: {list(ROLES.keys())}")
    
    usuarios = cargar_usuarios()
    if email in usuarios:
        raise ValueError(f"El usuario {email} ya existe")
    
    usuarios[email] = {
        "email":         email,
        "password_hash": hash_password(password),
        "rol":           rol,
        "empresa":       empresa,
        "creado":        datetime.now(timezone.utc).isoformat(),
        "activo":        True,
    }
    guardar_usuarios(usuarios)
    return {"email": email, "rol": rol, "empresa": empresa}

def autenticar_usuario(email: str, password: str) -> Optional[dict]:
    usuarios = cargar_usuarios()
    user     = usuarios.get(email)
    if not user or not user.get("activo"):
        return None
    if not verificar_password(password, user["password_hash"]):
        return None
    return {
        "email":   user["email"],
        "rol":     user["rol"],
        "empresa": user.get("empresa"),
    }

# ── Tokens JWT ────────────────────────────────────────────────────────────────
def crear_access_token(user_data: dict) -> str:
    if not JWT_OK:
        raise RuntimeError("python-jose no instalado: pip install python-jose")
    expire  = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_EXPIRE)
    payload = {
        **user_data,
        "exp":  expire,
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def crear_refresh_token(user_data: dict) -> str:
    if not JWT_OK:
        raise RuntimeError("python-jose no instalado")
    expire  = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_EXPIRE)
    payload = {
        **user_data,
        "exp":  expire,
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ── Dependencies FastAPI ──────────────────────────────────────────────────────
def require_auth(token: str = Depends(oauth2_scheme)) -> dict:
    if not token:
        raise HTTPException(401, "No autenticado")
    payload = decodificar_token(token)
    if payload.get("type") != "access":
        raise HTTPException(401, "Tipo de token inválido")
    return payload

def require_role(rol_necesario: str):
    def _check(user: dict = Depends(require_auth)) -> dict:
        if user.get("rol") != rol_necesario and user.get("rol") != "admin":
            raise HTTPException(403, f"Requiere rol '{rol_necesario}'")
        return user
    return _check

def require_permiso(permiso: str):
    def _check(user: dict = Depends(require_auth)) -> dict:
        if not tiene_permiso(user.get("rol", ""), permiso):
            raise HTTPException(403, f"Requiere permiso '{permiso}'")
        return user
    return _check

def optional_auth(token: str = Depends(oauth2_scheme)) -> Optional[dict]:
    """Retorna el usuario si está autenticado, None si no. No lanza error."""
    if not token:
        return None
    try:
        payload = decodificar_token(token)
        return payload if payload.get("type") == "access" else None
    except:
        return None


# ── CLI para crear usuarios ───────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Gestión de usuarios KraftDo")
    sub = p.add_subparsers(dest="cmd", required=True)

    crear = sub.add_parser("crear", help="Crear usuario nuevo")
    crear.add_argument("email")
    crear.add_argument("password")
    crear.add_argument("--rol",     default="cliente", choices=list(ROLES.keys()))
    crear.add_argument("--empresa", default=None)

    listar = sub.add_parser("listar", help="Listar usuarios")

    args = p.parse_args()

    if args.cmd == "crear":
        try:
            user = crear_usuario(args.email, args.password, args.rol, args.empresa)
            print(f"✅ Usuario creado: {user}")
        except ValueError as e:
            print(f"❌ {e}")
    elif args.cmd == "listar":
        usuarios = cargar_usuarios()
        for email, data in usuarios.items():
            activo = "✅" if data.get("activo") else "❌"
            print(f"  {activo} {email} [{data['rol']}] empresa={data.get('empresa','—')}")
