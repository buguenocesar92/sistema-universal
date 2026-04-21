"""
reporte_kraftdo.py — Wrapper de compatibilidad
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reporte_base import enviar_reporte

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--email",   default=os.environ.get("EMAIL_KRAFTDO_BD", "hola@kraftdo.cl"))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    enviar_reporte("kraftdo_bd", args.email, args.dry_run)
