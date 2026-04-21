"""
drive_export.py — Exporta backups a Google Drive como seguro externo
Redundancia adicional al MinIO local.

Configuracion:
  GOOGLE_CREDS_PATH=/app/creds.json    # Cuenta de servicio
  GDRIVE_FOLDER_ID=1abc...def          # ID de carpeta compartida con la cuenta de servicio
"""
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

GOOGLE_CREDS_PATH = os.environ.get("GOOGLE_CREDS_PATH", "/app/creds.json")
GDRIVE_FOLDER_ID  = os.environ.get("GDRIVE_FOLDER_ID", "")


def _servicio():
    """Crea el cliente de Google Drive API."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        if not Path(GOOGLE_CREDS_PATH).exists():
            return None

        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDS_PATH,
            scopes=["https://www.googleapis.com/auth/drive.file"],
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        print(f"[drive_export] No se pudo iniciar Drive: {e}")
        return None


def subir_backup(archivo: Path, folder_id: Optional[str] = None) -> dict:
    """
    Sube un archivo de backup a Google Drive.

    Returns:
        {"ok": True, "file_id": "...", "url": "..."}  si todo bien
        {"ok": False, "error": "..."}                  si falla
    """
    if not archivo.exists():
        return {"ok": False, "error": f"Archivo no existe: {archivo}"}

    service = _servicio()
    if not service:
        return {"ok": False, "error": "Drive no disponible (sin creds.json o librerias)"}

    folder_id = folder_id or GDRIVE_FOLDER_ID
    if not folder_id:
        return {"ok": False, "error": "GDRIVE_FOLDER_ID no configurado"}

    try:
        from googleapiclient.http import MediaFileUpload

        metadata = {
            "name":    archivo.name,
            "parents": [folder_id],
            "description": f"KraftDo backup — {datetime.now().isoformat()}",
        }
        media = MediaFileUpload(str(archivo), resumable=True, chunksize=5*1024*1024)

        request = service.files().create(
            body=metadata, media_body=media,
            fields="id, webViewLink, size"
        )
        response = None
        while response is None:
            _, response = request.next_chunk()

        return {
            "ok":      True,
            "file_id": response["id"],
            "url":     response.get("webViewLink", ""),
            "size":    response.get("size", "?"),
            "nombre":  archivo.name,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def limpiar_antiguos(dias: int = 90):
    """Elimina backups en Drive mas viejos que N dias."""
    service = _servicio()
    if not service or not GDRIVE_FOLDER_ID:
        return {"eliminados": 0, "error": "Drive no disponible"}

    try:
        # Listar archivos en la carpeta
        from datetime import timedelta
        limite = (datetime.utcnow() - timedelta(days=dias)).isoformat() + "Z"

        query = f"'{GDRIVE_FOLDER_ID}' in parents and createdTime < '{limite}' and name contains 'backup_'"
        results = service.files().list(q=query, fields="files(id, name, createdTime)").execute()

        eliminados = 0
        for f in results.get("files", []):
            try:
                service.files().delete(fileId=f["id"]).execute()
                eliminados += 1
            except Exception:
                pass
        return {"eliminados": eliminados}
    except Exception as e:
        return {"eliminados": 0, "error": str(e)}
