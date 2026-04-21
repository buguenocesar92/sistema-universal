"""
rate_limit_smart.py — Rate limiting adaptativo por tipo de usuario
Reemplaza el rate limit simple de 60 req/min con diferenciación:
  - Anónimo:          60 req/min
  - Autenticado:     600 req/min
  - Admin:          3000 req/min
  - IP sospechosa:    10 req/min + log + alerta

Bloqueo automático si una IP hace 5 requests 429 seguidos.
"""
import os, time
from typing import Optional
from fastapi import Request, HTTPException

try:
    import redis
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
    _r = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=3)
    _r.ping()
    REDIS_OK = True
except Exception:
    _r = None
    REDIS_OK = False


LIMITES = {
    "anonimo":        int(os.environ.get("RATE_LIMIT_ANON",  "60")),
    "autenticado":    int(os.environ.get("RATE_LIMIT_AUTH", "600")),
    "admin":          int(os.environ.get("RATE_LIMIT_ADMIN","3000")),
    "sospechoso":     10,
}

VENTANA_SEGUNDOS = 60


def obtener_tipo_usuario(request: Request) -> tuple[str, str]:
    """
    Clasifica al cliente y devuelve (tipo, identificador).
    """
    # 1. ¿Tiene JWT válido?
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            from jobs.jwt_auth import verificar_access
            payload = verificar_access(token)
            if payload:
                tipo = "admin" if payload.get("rol") == "admin" else "autenticado"
                return tipo, f"user:{payload['sub']}"
        except Exception:
            pass

    # 2. ¿IP marcada como sospechosa?
    ip = request.client.host if request.client else "desconocido"
    if REDIS_OK and _r.exists(f"ratelimit:sospechoso:{ip}"):
        return "sospechoso", f"ip:{ip}"

    # 3. Anónimo
    return "anonimo", f"ip:{ip}"


async def rate_limit_inteligente(request: Request):
    """
    Dependency de FastAPI que aplica rate limiting según tipo de usuario.
    Uso:
        @app.get("/endpoint")
        def mi_endpoint(_rl = Depends(rate_limit_inteligente)):
            ...
    """
    if not REDIS_OK:
        return  # Sin Redis, no podemos limitar — mejor dejar pasar

    tipo, identificador = obtener_tipo_usuario(request)
    limite = LIMITES.get(tipo, LIMITES["anonimo"])

    key = f"ratelimit:{tipo}:{identificador}:{int(time.time() // VENTANA_SEGUNDOS)}"

    try:
        count = _r.incr(key)
        if count == 1:
            _r.expire(key, VENTANA_SEGUNDOS + 1)

        if count > limite:
            # Si es anónimo y ya excedió varias veces, marcar como sospechoso
            if tipo == "anonimo":
                violaciones = _r.incr(f"ratelimit:violaciones:{identificador}")
                _r.expire(f"ratelimit:violaciones:{identificador}", 3600)
                if violaciones >= 5:
                    _r.setex(f"ratelimit:sospechoso:{identificador.split(':',1)[1]}",
                             3600, "1")  # 1 hora como sospechoso
                    # Log + alerta
                    try:
                        from jobs.audit import log_action
                        log_action(
                            accion="rate_limit_bloqueado",
                            ip=identificador.split(":", 1)[1],
                            detalle={"tipo": tipo, "violaciones": violaciones},
                            resultado="bloqueado",
                        )
                    except Exception:
                        pass

            raise HTTPException(
                status_code=429,
                detail=f"Rate limit excedido ({limite} req/min). Tipo: {tipo}",
                headers={
                    "X-RateLimit-Limit":     str(limite),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After":           str(VENTANA_SEGUNDOS),
                }
            )
    except HTTPException:
        raise
    except Exception:
        pass  # Fallo de Redis no debe tumbar el endpoint
