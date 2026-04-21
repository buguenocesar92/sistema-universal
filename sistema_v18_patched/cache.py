"""
cache.py — Sistema de cache con Redis + fallback en memoria

Uso:
    from cache import cached
    
    @cached(ttl=300, key_prefix="productos")
    def get_productos(empresa):
        return s.registros('productos')
    
    # O manualmente:
    from cache import cache
    cache.set("mi_key", datos, ttl=600)
    valor = cache.get("mi_key")
"""
import os
import json
import hashlib
import pickle
import time
from functools import wraps
from typing import Any, Optional, Callable

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# ── Fallback en memoria ───────────────────────────────────────────────────────
class MemoryCache:
    def __init__(self):
        self._store: dict = {}

    def get(self, key: str) -> Optional[Any]:
        item = self._store.get(key)
        if not item:
            return None
        if item["exp"] and item["exp"] < time.time():
            del self._store[key]
            return None
        return item["val"]

    def set(self, key: str, value: Any, ttl: int = 300):
        exp = time.time() + ttl if ttl > 0 else 0
        self._store[key] = {"val": value, "exp": exp}

    def delete(self, key: str):
        self._store.pop(key, None)

    def delete_pattern(self, pattern: str):
        # Soporte simple de wildcard con * al final
        prefix = pattern.rstrip("*")
        for k in list(self._store.keys()):
            if k.startswith(prefix):
                del self._store[k]

    def clear(self):
        self._store.clear()


class RedisCache:
    def __init__(self, url: str):
        self.client = redis.from_url(url, decode_responses=False,
                                      socket_connect_timeout=2)
        self.client.ping()  # verifica conexión

    def get(self, key: str) -> Optional[Any]:
        raw = self.client.get(key)
        if not raw:
            return None
        try:
            return pickle.loads(raw)
        except:
            return None

    def set(self, key: str, value: Any, ttl: int = 300):
        raw = pickle.dumps(value)
        if ttl > 0:
            self.client.setex(key, ttl, raw)
        else:
            self.client.set(key, raw)

    def delete(self, key: str):
        self.client.delete(key)

    def delete_pattern(self, pattern: str):
        for k in self.client.scan_iter(pattern):
            self.client.delete(k)

    def clear(self):
        self.client.flushdb()


# ── Singleton ─────────────────────────────────────────────────────────────────
def _init_cache():
    url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    if REDIS_AVAILABLE:
        try:
            return RedisCache(url)
        except Exception as e:
            print(f"⚠️  Redis no disponible ({e}), usando cache en memoria")
    return MemoryCache()

cache = _init_cache()

# ── Decorator ─────────────────────────────────────────────────────────────────
def cached(ttl: int = 300, key_prefix: str = "cache"):
    """
    Decorator que cachea el resultado de una función.
    La key se genera del prefix + hash de los argumentos.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            raw_key = f"{fn.__name__}:{args}:{sorted(kwargs.items())}"
            key     = f"{key_prefix}:{hashlib.md5(raw_key.encode()).hexdigest()[:12]}"

            valor = cache.get(key)
            if valor is not None:
                return valor

            resultado = fn(*args, **kwargs)
            cache.set(key, resultado, ttl=ttl)
            return resultado
        return wrapper
    return decorator

def invalidar(pattern: str):
    """Invalida todas las keys que empiezan con un patrón."""
    cache.delete_pattern(f"{pattern}*")
