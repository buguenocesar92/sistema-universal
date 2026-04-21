"""
worker.py — Worker que procesa jobs de la cola Redis
Uso: python3 worker.py
En Docker: corre como servicio separado
"""
import os, sys, json, time, traceback, subprocess, importlib
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from jobs.queue import JobQueue, HANDLERS, handler

# ── Handlers de jobs ──────────────────────────────────────────────────────────
@handler("reporte")
def procesar_reporte(payload: dict):
    """Genera y envía un reporte por correo. Llamada directa, sin subprocess."""
    from reporte_base import enviar_reporte

    empresa = payload["empresa"]
    email   = payload.get("email")
    dry_run = payload.get("dry_run", False)

    ok = enviar_reporte(empresa, email, dry_run=dry_run)
    if not ok:
        raise RuntimeError(f"No se pudo enviar el reporte de {empresa}")

    return {"empresa": empresa, "email": email, "enviado": ok}


@handler("onboarding")
def procesar_onboarding(payload: dict):
    """Ejecuta el onboarding completo de una empresa nueva."""
    from onboarding import onboarding
    return onboarding(payload["empresa"], payload["cfg"])


@handler("backup")
def procesar_backup(payload: dict):
    """Ejecuta el backup diario."""
    from jobs.backup import backup_diario
    return backup_diario()


# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    queue = JobQueue()
    if not queue.ok:
        print("❌ Redis no disponible, no se puede procesar la cola")
        sys.exit(1)

    print(f"""
╔══════════════════════════════════════════════════════╗
║       KraftDo Worker — Procesando jobs              ║
╚══════════════════════════════════════════════════════╝

🔌 Redis: {os.environ.get('REDIS_URL','redis://localhost:6379')}
📋 Handlers registrados: {', '.join(HANDLERS.keys())}
""")

    while True:
        try:
            job = queue.pop(timeout=5)
            if not job:
                continue

            tipo = job["tipo"]
            handler_fn = HANDLERS.get(tipo)

            if not handler_fn:
                print(f"❌ Sin handler para tipo '{tipo}'")
                queue.requeue(job)
                continue

            print(f"▶️  [{datetime.now().strftime('%H:%M:%S')}] Procesando {job['id']} ({tipo})")

            try:
                resultado = handler_fn(job["payload"])
                queue.marcar_ok(job["id"])
                print(f"✅ Completado: {job['id']}")
            except Exception as e:
                print(f"❌ Error en {job['id']}: {e}")
                traceback.print_exc()
                queue.requeue(job)

        except KeyboardInterrupt:
            print("\n⏹️  Worker detenido")
            break
        except Exception as e:
            print(f"❌ Error en worker: {e}")
            traceback.print_exc()
            time.sleep(5)


if __name__ == "__main__":
    main()
