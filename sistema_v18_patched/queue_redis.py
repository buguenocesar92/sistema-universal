"""
queue.py — Queue de Redis para procesamiento asíncrono de tareas

Reemplaza los threading.Thread que hay ahora en upload_portal.
Permite que si fallan 10 uploads simultáneos, se procesen en orden.

Uso:
    from queue_redis import enqueue
    
    enqueue("generar_reporte", {"empresa": "adille", "email": "x@y.cl"})
    
Worker (correr aparte):
    python3 queue_redis.py worker
"""
import os
import json
import time
import traceback
from datetime import datetime, timezone
from typing import Optional, Callable
from pathlib import Path

try:
    import redis
    REDIS_OK = True
except ImportError:
    REDIS_OK = False

QUEUE_NAME = "kraftdo:jobs"
FAILED_QUEUE = "kraftdo:failed"
SCRIPT_DIR = Path(__file__).parent

# ── Conexión ─────────────────────────────────────────────────────────────────
def _get_redis():
    if not REDIS_OK:
        raise RuntimeError("redis no instalado")
    url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    return redis.from_url(url, decode_responses=True)

# ── Handlers registrados ─────────────────────────────────────────────────────
_handlers: dict = {}

def handler(nombre: str):
    """Decorator para registrar un handler de tarea."""
    def decorator(fn: Callable):
        _handlers[nombre] = fn
        return fn
    return decorator

# ── Encolar tarea ─────────────────────────────────────────────────────────────
def enqueue(tarea: str, params: Optional[dict] = None, delay: int = 0) -> str:
    """
    Encola una tarea para ejecución asíncrona.
    
    Args:
        tarea:  nombre registrado del handler
        params: argumentos para el handler
        delay:  segundos a esperar antes de ejecutar (0 = inmediato)
    """
    r = _get_redis()
    job_id = f"{tarea}_{int(time.time()*1000)}"
    job = {
        "id":         job_id,
        "tarea":      tarea,
        "params":     params or {},
        "encolado":   datetime.now(timezone.utc).isoformat(),
        "ejecutar_en": time.time() + delay,
        "intentos":   0,
    }
    if delay > 0:
        r.zadd(f"{QUEUE_NAME}:delayed", {json.dumps(job): time.time() + delay})
    else:
        r.lpush(QUEUE_NAME, json.dumps(job))
    return job_id

# ── Worker loop ───────────────────────────────────────────────────────────────
def _procesar_job(job: dict, r) -> bool:
    """Ejecuta un job. Retorna True si exitoso."""
    tarea  = job.get("tarea")
    params = job.get("params", {})

    if tarea not in _handlers:
        print(f"❌ Handler '{tarea}' no registrado")
        return False

    try:
        resultado = _handlers[tarea](**params)
        print(f"✅ {job['id']} [{tarea}] completado")
        return True
    except Exception as e:
        print(f"❌ {job['id']} [{tarea}] falló: {e}")
        traceback.print_exc()
        
        job["intentos"] = job.get("intentos", 0) + 1
        job["error"]    = str(e)
        
        # Reintentar hasta 3 veces
        if job["intentos"] < 3:
            print(f"   Reintentando en {60 * job['intentos']}s...")
            r.zadd(f"{QUEUE_NAME}:delayed",
                   {json.dumps(job): time.time() + 60 * job["intentos"]})
        else:
            # Mover a failed queue después de 3 intentos
            r.lpush(FAILED_QUEUE, json.dumps(job))
            print(f"   Movido a {FAILED_QUEUE} después de {job['intentos']} intentos")
        return False

def _mover_delayed_a_main(r):
    """Mueve jobs cuyo delay ya expiró a la queue principal."""
    ahora = time.time()
    vencidos = r.zrangebyscore(f"{QUEUE_NAME}:delayed", 0, ahora)
    for job_json in vencidos:
        r.lpush(QUEUE_NAME, job_json)
        r.zrem(f"{QUEUE_NAME}:delayed", job_json)

def worker_loop():
    """Loop principal del worker. Bloquea hasta recibir SIGINT."""
    r = _get_redis()
    print(f"🔄 Worker iniciado — escuchando cola '{QUEUE_NAME}'")
    print(f"   Handlers registrados: {list(_handlers.keys())}")

    while True:
        try:
            _mover_delayed_a_main(r)
            # BRPOP bloquea hasta 5 segundos esperando un job
            resultado = r.brpop(QUEUE_NAME, timeout=5)
            if not resultado:
                continue
            
            _, job_json = resultado
            job = json.loads(job_json)
            _procesar_job(job, r)
        except KeyboardInterrupt:
            print("\n👋 Worker detenido")
            break
        except Exception as e:
            print(f"⚠️  Error en worker loop: {e}")
            time.sleep(1)

# ── Stats ────────────────────────────────────────────────────────────────────
def stats() -> dict:
    r = _get_redis()
    return {
        "pendientes": r.llen(QUEUE_NAME),
        "delayed":    r.zcard(f"{QUEUE_NAME}:delayed"),
        "failed":     r.llen(FAILED_QUEUE),
        "handlers":   list(_handlers.keys()),
    }


# ── Handlers del sistema KraftDo ──────────────────────────────────────────────
@handler("generar_reporte")
def _handler_generar_reporte(empresa: str, email: str):
    """Genera y envía el reporte de una empresa."""
    import subprocess
    script = SCRIPT_DIR / f"reporte_{empresa}.py"
    if not script.exists():
        raise FileNotFoundError(f"No existe {script}")
    
    resultado = subprocess.run(
        ["python3", str(script), "--email", email],
        capture_output=True, text=True, cwd=str(SCRIPT_DIR),
        timeout=120
    )
    if resultado.returncode != 0:
        raise RuntimeError(f"Reporte falló: {resultado.stderr}")
    return resultado.stdout

@handler("procesar_upload")
def _handler_procesar_upload(empresa: str, archivo: str, email: str):
    """Procesa un Excel subido y dispara el reporte."""
    from cache import invalidar
    invalidar(f"kraftdo:{empresa}")  # invalidar cache de esa empresa
    _handler_generar_reporte(empresa=empresa, email=email)

@handler("backup_bd")
def _handler_backup_bd():
    """Dispara backup de las 3 BDs."""
    import subprocess
    script = SCRIPT_DIR / "scripts" / "backup_bd.sh"
    if not script.exists():
        raise FileNotFoundError(f"No existe {script}")
    resultado = subprocess.run(["bash", str(script)], capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"Backup falló: {resultado.stderr}")
    return resultado.stdout


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("worker", help="Iniciar worker (bloquea)")
    sub.add_parser("stats",  help="Ver estadísticas")
    enq = sub.add_parser("enqueue", help="Encolar tarea")
    enq.add_argument("tarea")
    enq.add_argument("--params", default="{}")

    args = p.parse_args()

    if args.cmd == "worker":
        worker_loop()
    elif args.cmd == "stats":
        import json as _j
        print(_j.dumps(stats(), indent=2))
    elif args.cmd == "enqueue":
        import json as _j
        job_id = enqueue(args.tarea, _j.loads(args.params))
        print(f"✅ Job encolado: {job_id}")
