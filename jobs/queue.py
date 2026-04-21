"""
queue.py — Sistema de colas con Redis
Procesa tareas asíncronas: reportes, notificaciones, etc.
Reemplaza el threading.Thread directo del upload_portal.py
"""
import os, json, time, traceback
from datetime import datetime, timezone
from typing import Callable
import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

class JobQueue:
    """Cola simple de jobs en Redis con reintentos y logs."""

    def __init__(self, name: str = "kraftdo:jobs"):
        self.name  = name
        self.redis = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=3)
        try:
            self.redis.ping()
            self.ok = True
        except Exception:
            self.ok = False
            print(f"⚠️  Redis no disponible en {REDIS_URL} — modo síncrono")

    def enqueue(self, tipo: str, payload: dict, max_retries: int = 3) -> str:
        """Agrega un job a la cola. Retorna el job_id."""
        job_id = f"job_{int(time.time()*1000)}_{os.urandom(4).hex()}"
        job = {
            "id":         job_id,
            "tipo":       tipo,
            "payload":    payload,
            "intentos":   0,
            "max_retries":max_retries,
            "creado":     datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "estado":     "pendiente",
        }
        if self.ok:
            self.redis.lpush(self.name, json.dumps(job))
            self.redis.hset(f"{self.name}:status", job_id, "pendiente")
        return job_id

    def status(self, job_id: str) -> str:
        if not self.ok:
            return "sin_redis"
        return self.redis.hget(f"{self.name}:status", job_id) or "desconocido"

    def pop(self, timeout: int = 5):
        """Saca un job de la cola (bloqueante)."""
        if not self.ok:
            return None
        result = self.redis.brpop(self.name, timeout=timeout)
        if not result:
            return None
        _, data = result
        return json.loads(data)

    def requeue(self, job: dict):
        """Reinserta un job para reintentar."""
        if not self.ok:
            return
        job["intentos"] += 1
        if job["intentos"] < job["max_retries"]:
            job["estado"] = f"reintento_{job['intentos']}"
            self.redis.lpush(self.name, json.dumps(job))
            self.redis.hset(f"{self.name}:status", job["id"], job["estado"])
        else:
            job["estado"] = "fallido"
            self.redis.hset(f"{self.name}:status", job["id"], "fallido")
            self.redis.lpush(f"{self.name}:failed", json.dumps(job))

    def marcar_ok(self, job_id: str):
        if self.ok:
            self.redis.hset(f"{self.name}:status", job_id, "completado")

    def estadisticas(self) -> dict:
        if not self.ok:
            return {"error": "Redis no disponible"}
        return {
            "pendientes": self.redis.llen(self.name),
            "fallidos":   self.redis.llen(f"{self.name}:failed"),
            "estados":    self.redis.hlen(f"{self.name}:status"),
        }


# ── Registry de handlers ──────────────────────────────────────────────────────
HANDLERS: dict[str, Callable] = {}

def handler(tipo: str):
    """Decorator para registrar un handler de tipo de job."""
    def wrap(fn):
        HANDLERS[tipo] = fn
        return fn
    return wrap
