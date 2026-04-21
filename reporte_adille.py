"""
reporte_adille.py — Wrapper de compatibilidad
La lógica real está en reporte_base.py.
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reporte_base import enviar_reporte

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--email",   default=os.environ.get("EMAIL_ADILLE", "hola@kraftdo.cl"))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    enviar_reporte("adille", args.email, args.dry_run)
