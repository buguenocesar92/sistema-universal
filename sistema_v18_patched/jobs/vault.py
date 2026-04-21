"""
vault.py — Gestión centralizada de secretos
Soporta:
  1. HashiCorp Vault (producción grande)
  2. AWS Secrets Manager (si hay boto3)
  3. .env cifrado con crypto.py (fallback — suficiente para KraftDo)

Uso:
    from jobs.vault import get_secret
    db_pass = get_secret("DB_PASS")        # lee de donde esté disponible
    api_key = get_secret("ANTHROPIC_API_KEY")
"""
import os
from typing import Optional
from functools import lru_cache

VAULT_PROVIDER = os.environ.get("VAULT_PROVIDER", "env")  # "vault" | "aws" | "env"
VAULT_ADDR     = os.environ.get("VAULT_ADDR",  "http://vault:8200")
VAULT_TOKEN    = os.environ.get("VAULT_TOKEN", "")
VAULT_PATH     = os.environ.get("VAULT_PATH",  "kraftdo")


@lru_cache(maxsize=1)
def _client_vault():
    try:
        import hvac
        c = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
        if c.is_authenticated():
            return c
    except Exception:
        pass
    return None


@lru_cache(maxsize=1)
def _client_aws():
    try:
        import boto3
        return boto3.client("secretsmanager")
    except Exception:
        return None


def get_secret(clave: str, default: Optional[str] = None) -> Optional[str]:
    """
    Obtiene un secreto. Busca en este orden:
      1. Vault (si configurado)
      2. AWS Secrets Manager (si configurado)
      3. Variable de entorno (siempre como fallback)
    """
    # 1. HashiCorp Vault
    if VAULT_PROVIDER == "vault":
        c = _client_vault()
        if c:
            try:
                r = c.secrets.kv.v2.read_secret_version(path=VAULT_PATH)
                return r["data"]["data"].get(clave, default)
            except Exception:
                pass

    # 2. AWS Secrets Manager
    elif VAULT_PROVIDER == "aws":
        c = _client_aws()
        if c:
            try:
                import json
                r = c.get_secret_value(SecretId=f"kraftdo/{clave}")
                return r.get("SecretString", default)
            except Exception:
                pass

    # 3. Fallback: .env con opcional cifrado
    valor = os.environ.get(clave, default)
    if valor and valor.startswith("enc:"):
        # Si el valor comienza con "enc:" está cifrado con jobs/crypto
        try:
            from jobs.crypto import descifrar
            return descifrar(valor[4:])
        except Exception:
            return default
    return valor


def set_secret(clave: str, valor: str) -> bool:
    """Guarda un secreto. Solo funciona con Vault o AWS (no modifica .env)."""
    if VAULT_PROVIDER == "vault":
        c = _client_vault()
        if c:
            try:
                # Leer secretos actuales
                try:
                    actuales = c.secrets.kv.v2.read_secret_version(path=VAULT_PATH)["data"]["data"]
                except Exception:
                    actuales = {}
                actuales[clave] = valor
                c.secrets.kv.v2.create_or_update_secret(path=VAULT_PATH, secret=actuales)
                return True
            except Exception:
                return False

    if VAULT_PROVIDER == "aws":
        c = _client_aws()
        if c:
            try:
                c.put_secret_value(SecretId=f"kraftdo/{clave}", SecretString=valor)
                return True
            except Exception:
                try:
                    c.create_secret(Name=f"kraftdo/{clave}", SecretString=valor)
                    return True
                except Exception:
                    return False

    return False
