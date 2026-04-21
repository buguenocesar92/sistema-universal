"""
backup.py — Backup automático diario de BD + archivos
Sube a MinIO (local) y opcionalmente a Cloudflare R2 (externo)

Uso:
  python3 jobs/backup.py             # backup normal
  python3 jobs/backup.py --restore   # listar backups disponibles
"""
import os, sys, subprocess, tarfile, tempfile, shutil
from pathlib import Path
from datetime import datetime, timedelta

SCRIPT_DIR = Path(__file__).parent.parent

BACKUP_DIR = SCRIPT_DIR / "storage" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

RETENCION_DIAS = int(os.environ.get("BACKUP_RETENCION_DIAS", "30"))

# ── Bases de datos a respaldar ─────────────────────────────────────────────────
BASES_DATOS = ["kraftdo_bd", "kraftdo_adille", "kraftdo_extractores", "n8n"]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def backup_mysql(nombre_bd: str, destino: Path) -> bool:
    """Dump de una base de datos MySQL."""
    user = os.environ.get("DB_USER", "kraftdo")
    pwd  = os.environ.get("DB_PASS", "")
    host = os.environ.get("DB_HOST", "mysql")
    port = os.environ.get("DB_PORT", "3306")

    try:
        cmd = [
            "mysqldump",
            f"--host={host}",
            f"--port={port}",
            f"--user={user}",
            f"--password={pwd}",
            "--single-transaction",
            "--quick",
            "--lock-tables=false",
            nombre_bd,
        ]
        with open(destino, "wb") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=600)

        if result.returncode != 0:
            log(f"❌ Falló backup de {nombre_bd}: {result.stderr.decode()[:200]}")
            return False

        tam_mb = destino.stat().st_size / 1024 / 1024
        log(f"✅ {nombre_bd}: {tam_mb:.1f}MB")
        return True
    except Exception as e:
        log(f"❌ Error con {nombre_bd}: {e}")
        return False


def backup_archivos(destino: Path) -> bool:
    """Comprime las carpetas críticas (empresas, storage/uploads)."""
    try:
        with tarfile.open(destino, "w:gz") as tar:
            for carpeta in ["empresas", "storage/uploads"]:
                path = SCRIPT_DIR / carpeta
                if path.exists():
                    tar.add(path, arcname=carpeta)
        tam_mb = destino.stat().st_size / 1024 / 1024
        log(f"✅ Archivos: {tam_mb:.1f}MB")
        return True
    except Exception as e:
        log(f"❌ Error comprimiendo archivos: {e}")
        return False


def subir_a_minio(archivo: Path) -> bool:
    """Sube el backup a MinIO (bucket kraftdo-backups)."""
    try:
        from minio import Minio
    except ImportError:
        log("⚠️  minio no instalado, saltando upload a MinIO")
        return False

    endpoint = os.environ.get("MINIO_ENDPOINT", "minio:9000")
    access   = os.environ.get("MINIO_ROOT_USER", "kraftdo")
    secret   = os.environ.get("MINIO_ROOT_PASSWORD", "kraftdo123secure")

    try:
        client = Minio(endpoint, access_key=access, secret_key=secret, secure=False)
        bucket = "kraftdo-backups"
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

        nombre = archivo.name
        client.fput_object(bucket, nombre, str(archivo))
        log(f"✅ Subido a MinIO: {bucket}/{nombre}")
        return True
    except Exception as e:
        log(f"⚠️  MinIO falló: {e}")
        return False


def limpiar_antiguos():
    """Elimina backups más viejos que RETENCION_DIAS."""
    limite = datetime.now() - timedelta(days=RETENCION_DIAS)
    eliminados = 0
    for f in BACKUP_DIR.glob("backup_*.tar.gz"):
        if datetime.fromtimestamp(f.stat().st_mtime) < limite:
            f.unlink()
            eliminados += 1
    if eliminados:
        log(f"🗑️  Eliminados {eliminados} backups antiguos (>{RETENCION_DIAS} días)")


def backup_diario() -> dict:
    """Ejecuta el backup completo. Usado por el worker y el cron."""
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    log(f"🔄 Iniciando backup {fecha}")

    resultados = {"fecha": fecha, "bds": {}, "archivos": False, "minio": False}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Dumps de BDs
        for bd in BASES_DATOS:
            sql_file = tmp_path / f"{bd}.sql"
            resultados["bds"][bd] = backup_mysql(bd, sql_file)

        # Archivos estáticos
        archivos_tar = tmp_path / "archivos.tar.gz"
        resultados["archivos"] = backup_archivos(archivos_tar)

        # Empaquetar todo
        backup_final = BACKUP_DIR / f"backup_{fecha}.tar.gz"
        with tarfile.open(backup_final, "w:gz") as tar:
            for item in tmp_path.iterdir():
                tar.add(item, arcname=item.name)

        tam_mb = backup_final.stat().st_size / 1024 / 1024
        log(f"📦 Backup final: {backup_final.name} ({tam_mb:.1f}MB)")

        # Subir a MinIO
        resultados["minio"] = subir_a_minio(backup_final)

        # Subir a Google Drive (backup externo redundante)
        try:
            from jobs.drive_export import subir_backup as subir_drive
            resultados["drive"] = subir_drive(backup_final)
        except Exception as e:
            resultados["drive"] = {"ok": False, "error": str(e)}

    limpiar_antiguos()
    log(f"✅ Backup completado")
    return resultados


if __name__ == "__main__":
    if "--restore" in sys.argv:
        backups = sorted(BACKUP_DIR.glob("backup_*.tar.gz"), reverse=True)
        print(f"\nBackups disponibles en {BACKUP_DIR}:")
        for b in backups[:10]:
            tam = b.stat().st_size / 1024 / 1024
            fecha = datetime.fromtimestamp(b.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            print(f"  {fecha}  {b.name}  ({tam:.1f}MB)")
    else:
        backup_diario()
