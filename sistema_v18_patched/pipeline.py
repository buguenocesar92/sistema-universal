"""
KraftDo — pipeline.py
Orquestación con Prefect para automatizar el flujo Excel → MySQL.

Flujos disponibles:
  1. sync_empresa       → Detectar cambios en Excel e importar a MySQL
  2. validar_empresa    → Dry-run de validación sin importar
  3. generar_sistema    → Generar código Laravel desde JSON
  4. reporte_semanal    → Generar y enviar reporte semanal
  5. backup_excel       → Backup automático a MinIO

USO:
    python3 pipeline.py sync kraftdo
    python3 pipeline.py validar kraftdo
    python3 pipeline.py generar kraftdo --output ./mi-sistema
    python3 pipeline.py reporte kraftdo
    
    # Scheduling (requiere prefect server corriendo):
    python3 pipeline.py schedule kraftdo --cada 6h
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Prefect
from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from datetime import timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)


# ══════════════════════════════════════════════════════════════════════════════
# TASKS — Unidades atómicas de trabajo
# ══════════════════════════════════════════════════════════════════════════════

@task(
    name="cargar-config",
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1),
    retries=2,
)
def task_cargar_config(empresa: str) -> dict:
    """Carga y valida el JSON de configuración de una empresa."""
    logger = get_run_logger()
    cfg_path = os.path.join(SCRIPT_DIR, "empresas", f"{empresa}.json")
    if not os.path.exists(cfg_path):
        raise FileNotFoundError(f"Config no encontrado: {cfg_path}")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    logger.info(f"Config cargado: {cfg['empresa']['nombre']}")
    return cfg


@task(name="detectar-patrones", retries=1)
def task_detectar_patrones(empresa: str, cfg: dict) -> dict:
    """Analiza el Excel y detecta patrones no estándar."""
    logger = get_run_logger()
    from normalizer import analizar_excel_completo

    excel_path = os.path.join(SCRIPT_DIR, cfg["fuente"].get("archivo", ""))
    if not os.path.exists(excel_path):
        logger.warning(f"Excel no encontrado localmente: {excel_path}")
        return {}

    patrones = analizar_excel_completo(excel_path)
    raros = {h: d for h, d in patrones.items()
             if d["patron"] not in ("vertical", "con_totales", "vacia")}

    if raros:
        logger.warning(f"Patrones no estándar detectados: {list(raros.keys())}")
        for hoja, diag in raros.items():
            logger.warning(f"  {hoja}: {diag['patron']} — {diag['descripcion']}")
    else:
        logger.info("Todos los patrones son estándar ✅")

    return patrones


@task(name="validar-datos", retries=1)
def task_validar(empresa: str, cfg: dict, solo: list = None) -> dict:
    """Dry-run: valida datos sin insertar en la BD."""
    logger = get_run_logger()
    from importer import Importer

    imp = Importer(empresa)
    resultados = imp.dry_run(solo)

    total_errores = sum(r.get("errores", 0) for r in resultados.values())
    total_validas = sum(r.get("validas", 0) for r in resultados.values())

    logger.info(f"Validación: {total_validas} filas válidas, {total_errores} errores")
    if total_errores > 0:
        logger.warning(f"Hay {total_errores} errores de validación")

    return resultados


@task(name="importar-datos", retries=2, retry_delay_seconds=30)
def task_importar(empresa: str, cfg: dict, solo: list = None,
                  limpiar: bool = False) -> dict:
    """Importa datos del Excel/Sheets a MySQL."""
    logger = get_run_logger()
    from importer import Importer

    imp = Importer(empresa)
    resultados = imp.importar_todo(solo, limpiar, preview=False)

    total = sum(r.get("insertados", 0) for r in resultados.values())
    logger.info(f"Importados: {total} registros en total")
    return resultados


@task(name="detectar-cambios", retries=1)
def task_detectar_cambios(empresa: str) -> dict:
    """Detecta cambios en el JSON vs último snapshot."""
    logger = get_run_logger()
    from differ import diff_hojas, ultimo_snapshot, cargar_json, guardar_snapshot

    cfg_path = os.path.join(SCRIPT_DIR, "empresas", f"{empresa}.json")
    cfg_nuevo = cargar_json(cfg_path)

    snap = ultimo_snapshot(empresa)
    if not snap:
        logger.info("Sin snapshot previo — guardando estado inicial")
        guardar_snapshot(empresa, cfg_nuevo)
        return {"sin_cambios": True, "razon": "primer_run"}

    cfg_viejo = cargar_json(snap)
    diff = diff_hojas(cfg_viejo, cfg_nuevo)

    total = (len(diff["hojas_nuevas"]) +
             len(diff["hojas_eliminadas"]) +
             len(diff["hojas_modificadas"]))

    if total > 0:
        logger.info(f"Cambios detectados: {total} modificaciones en el schema")
    else:
        logger.info("Sin cambios en el schema desde el último run")

    return diff


@task(name="generar-codigo", retries=1)
def task_generar(empresa: str, output_dir: str) -> dict:
    """Genera código Laravel+Filament desde el JSON."""
    logger = get_run_logger()
    from generator import generar

    archivos = generar(empresa, output_dir)
    logger.info(f"Generados {len(archivos)} archivos en {output_dir}")
    return {"archivos": len(archivos), "output": output_dir}


@task(name="backup-minio", retries=3, retry_delay_seconds=10)
def task_backup_minio(empresa: str, cfg: dict) -> str:
    """Sube el Excel a MinIO como backup versionado."""
    logger = get_run_logger()

    minio_url    = os.environ.get("MINIO_URL",    "localhost:9000")
    minio_user   = os.environ.get("MINIO_ROOT_USER", "kraftdo")
    minio_pass   = os.environ.get("MINIO_ROOT_PASSWORD", "kraftdo123")
    bucket       = os.environ.get("MINIO_BUCKET", "kraftdo-backups")

    excel_path = os.path.join(SCRIPT_DIR, cfg["fuente"].get("archivo", ""))
    if not os.path.exists(excel_path):
        logger.warning(f"Excel no encontrado para backup: {excel_path}")
        return ""

    try:
        from minio import Minio
        from minio.error import S3Error

        client = Minio(minio_url, access_key=minio_user,
                       secret_key=minio_pass, secure=False)

        # Crear bucket si no existe
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info(f"Bucket creado: {bucket}")

        # Nombre con timestamp para versionado
        ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
        objeto     = f"{empresa}/{ts}_{os.path.basename(excel_path)}"
        client.fput_object(bucket, objeto, excel_path)

        logger.info(f"Backup subido: {bucket}/{objeto}")
        return f"minio://{bucket}/{objeto}"

    except ImportError:
        logger.warning("minio no instalado — saltando backup")
        return ""
    except Exception as e:
        logger.error(f"Error en backup MinIO: {e}")
        raise


@task(name="notificar-telegram", retries=2)
def task_notificar(mensaje: str, chat_id: str = None):
    """Envía notificación por Telegram."""
    logger = get_run_logger()
    token   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados")
        return

    try:
        import urllib.request
        url     = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": mensaje,
                              "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        logger.info("Notificación Telegram enviada")
    except Exception as e:
        logger.warning(f"Error enviando Telegram: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# FLOWS — Pipelines completos
# ══════════════════════════════════════════════════════════════════════════════

@flow(
    name="sync-empresa",
    description="Sincroniza Excel → MySQL con validación, backup y notificación",
    log_prints=True,
)
def flow_sync(empresa: str, solo: list = None, limpiar: bool = False,
              backup: bool = True, notificar: bool = True):
    """
    Flujo completo de sincronización:
    1. Cargar config
    2. Detectar patrones no estándar
    3. Validar datos (dry-run)
    4. Importar a MySQL
    5. Backup a MinIO (opcional)
    6. Notificar por Telegram (opcional)
    """
    logger = get_run_logger()
    inicio = datetime.now()
    logger.info(f"🚀 Iniciando sync para: {empresa}")

    # 1. Config
    cfg = task_cargar_config(empresa)

    # 2. Patrones
    patrones = task_detectar_patrones(empresa, cfg)

    # 3. Validar
    validacion = task_validar(empresa, cfg, solo)
    total_errores = sum(r.get("errores", 0) for r in validacion.values())

    if total_errores > 0:
        logger.warning(f"⚠️ {total_errores} errores de validación — importando igual")

    # 4. Importar
    resultado = task_importar(empresa, cfg, solo, limpiar)
    total_imp  = sum(r.get("insertados", 0) for r in resultado.values())

    # 5. Backup
    backup_url = ""
    if backup:
        backup_url = task_backup_minio(empresa, cfg)

    # 6. Notificación
    duracion = (datetime.now() - inicio).seconds
    msg = (
        f"✅ *Sync completado — {cfg['empresa']['nombre']}*\n"
        f"📊 {total_imp} registros importados\n"
        f"⚠️  {total_errores} errores de validación\n"
        f"⏱️  {duracion}s\n"
        f"💾 Backup: {'✅' if backup_url else '❌'}"
    )
    if notificar:
        task_notificar(msg)

    return {"importados": total_imp, "errores": total_errores, "backup": backup_url}


@flow(name="validar-empresa", log_prints=True)
def flow_validar(empresa: str, solo: list = None):
    """Valida datos sin importar — útil antes de un sync crítico."""
    cfg        = task_cargar_config(empresa)
    validacion = task_validar(empresa, cfg, solo)
    total_err  = sum(r.get("errores", 0) for r in validacion.values())
    total_ok   = sum(r.get("validas", 0) for r in validacion.values())

    print(f"\n{'='*50}")
    print(f"Validación: {total_ok} filas válidas, {total_err} errores")
    for alias, r in validacion.items():
        status = "✅" if r.get("errores", 0) == 0 else "❌"
        print(f"  {status} {alias}: {r.get('validas', 0)} válidas, {r.get('errores', 0)} errores")

    return validacion


@flow(name="generar-sistema", log_prints=True)
def flow_generar(empresa: str, output_dir: str = None):
    """Genera código Laravel+Filament desde el JSON."""
    if not output_dir:
        output_dir = f"./sistema_{empresa}_{datetime.now().strftime('%Y%m%d')}"
    cfg = task_cargar_config(empresa)
    resultado = task_generar(empresa, output_dir)
    print(f"\n✅ Sistema generado en: {output_dir}")
    print(f"   {resultado['archivos']} archivos Laravel+Filament")
    return resultado


@flow(name="backup-manual", log_prints=True)
def flow_backup(empresa: str):
    """Backup manual del Excel a MinIO."""
    cfg = task_cargar_config(empresa)
    url = task_backup_minio(empresa, cfg)
    if url:
        print(f"✅ Backup en: {url}")
    else:
        print("❌ Backup falló o MinIO no configurado")
    return url


@flow(name="sync-periodico", log_prints=True)
def flow_sync_periodico(empresa: str):
    """
    Flujo para scheduling periódico:
    - Detecta cambios en el schema
    - Solo importa si hay cambios o datos nuevos
    - Siempre hace backup
    """
    logger = get_run_logger()
    cfg    = task_cargar_config(empresa)
    diff   = task_detectar_cambios(empresa)

    if diff.get("sin_cambios"):
        logger.info("Sin cambios — skip importación")
        # Backup igual aunque no haya cambios
        task_backup_minio(empresa, cfg)
        return {"accion": "skip", "razon": diff.get("razon")}

    # Hay cambios — importar
    resultado = task_importar(empresa, cfg)
    task_backup_minio(empresa, cfg)

    total = sum(r.get("insertados", 0) for r in resultado.values())
    msg   = f"🔄 *Sync periódico — {cfg['empresa']['nombre']}*\n{total} registros sincronizados"
    task_notificar(msg)

    return {"accion": "sync", "importados": total}


# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KraftDo Pipeline — Prefect")
    sub    = parser.add_subparsers(dest="cmd")

    # sync
    p = sub.add_parser("sync", help="Sincronizar Excel → MySQL")
    p.add_argument("empresa")
    p.add_argument("--solo",    help="Hojas separadas por coma")
    p.add_argument("--limpiar", action="store_true")
    p.add_argument("--no-backup",    action="store_true")
    p.add_argument("--no-notificar", action="store_true")

    # validar
    p = sub.add_parser("validar", help="Validar sin importar")
    p.add_argument("empresa")
    p.add_argument("--solo", help="Hojas separadas por coma")

    # generar
    p = sub.add_parser("generar", help="Generar código Laravel")
    p.add_argument("empresa")
    p.add_argument("--output", default=None)

    # backup
    p = sub.add_parser("backup", help="Backup manual a MinIO")
    p.add_argument("empresa")

    # schedule
    p = sub.add_parser("schedule", help="Programar sync periódico")
    p.add_argument("empresa")
    p.add_argument("--cada", default="6h", help="Intervalo: 1h, 6h, 24h")

    args = parser.parse_args()

    if args.cmd == "sync":
        solo = [s.strip() for s in args.solo.split(",")] if getattr(args, "solo", None) else None
        flow_sync(
            args.empresa, solo,
            getattr(args, "limpiar", False),
            not getattr(args, "no_backup", False),
            not getattr(args, "no_notificar", False),
        )

    elif args.cmd == "validar":
        solo = [s.strip() for s in args.solo.split(",")] if getattr(args, "solo", None) else None
        flow_validar(args.empresa, solo)

    elif args.cmd == "generar":
        flow_generar(args.empresa, getattr(args, "output", None))

    elif args.cmd == "backup":
        flow_backup(args.empresa)

    elif args.cmd == "schedule":
        print(f"""
Para scheduling periódico con Prefect:

  # 1. Iniciar servidor Prefect
  prefect server start

  # 2. En otra terminal, desplegar el flujo
  prefect deploy pipeline.py:flow_sync_periodico \\
      --name "sync-{args.empresa}" \\
      --cron "0 */6 * * *"    # cada 6 horas

  # 3. Iniciar worker
  prefect worker start --pool "default-agent-pool"

  # O ejecutar manualmente:
  python3 pipeline.py sync {args.empresa}
""")
    else:
        parser.print_help()
