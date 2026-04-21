"""
cache.py — Cache de respuestas de API con Redis + TTL
Reduce carga del VPS hasta 80% cacheando lecturas.
"""
import os, json, hashlib, functools
from typing import Callable
import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
CACHE_TTL = int(os.environ.get("CACHE_TTL", "300"))  # 5 minutos por defecto

try:
    _cache = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=3)
    _cache.ping()
    CACHE_OK = True
except Exception:
    _cache   = None
    CACHE_OK = False


def cache_key(prefix: str, *args, **kwargs) -> str:
    """Genera una key única para la combinación de args."""
    data = json.dumps({"a": args, "k": kwargs}, sort_keys=True, default=str)
    hash_ = hashlib.md5(data.encode()).hexdigest()[:12]
    return f"kraftdo:cache:{prefix}:{hash_}"


def cached(prefix: str, ttl: int = None):
    """Decorator para cachear el resultado de una función."""
    if ttl is None:
        ttl = CACHE_TTL

    def wrap(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not CACHE_OK:
                return fn(*args, **kwargs)

            key = cache_key(prefix, *args, **kwargs)
            try:
                cached_val = _cache.get(key)
                if cached_val is not None:
                    return json.loads(cached_val)
            except Exception:
                pass

            resultado = fn(*args, **kwargs)
            try:
                _cache.setex(key, ttl, json.dumps(resultado, default=str))
            except Exception:
                pass
            return resultado
        return wrapper
    return wrap


def invalidar(prefix: str = None, empresa: str = None):
    """Invalida cache. Si no hay prefix, invalida todo."""
    if not CACHE_OK:
        return 0
    pattern = f"kraftdo:cache:{prefix or '*'}"
    if empresa:
        pattern = f"kraftdo:cache:{prefix or '*'}:*{empresa}*"

    count = 0
    for key in _cache.scan_iter(match=pattern):
        _cache.delete(key)
        count += 1
    return count


def estadisticas() -> dict:
    """Devuelve métricas del cache."""
    if not CACHE_OK:
        return {"error": "Redis no disponible"}
    keys = list(_cache.scan_iter(match="kraftdo:cache:*"))
    return {
        "total_keys": len(keys),
        "ttl_default": CACHE_TTL,
        "memoria": _cache.info("memory").get("used_memory_human", "?"),
    }
