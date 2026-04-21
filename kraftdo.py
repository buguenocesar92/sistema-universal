#!/usr/bin/env python3
"""
KraftDo CLI — Punto de entrada unificado

USO:
    python3 kraftdo.py <comando> [opciones]

COMANDOS:
    setup                   → Verificar dependencias e instalar
    clasificar              → Abrir UI web para clasificar Excel
    api                     → Iniciar API REST
    generar  <empresa>      → Generar código Laravel+Filament
    importar <empresa>      → Importar datos Excel → MySQL
    n8n      <empresa>      → Generar workflows n8n
    diff     <empresa>      → Detectar cambios en el JSON
    test                    → Correr suite de tests
    empresas                → Listar empresas configuradas
    ayuda    [comando]      → Mostrar ayuda detallada

EJEMPLOS:
    python3 kraftdo.py setup
    python3 kraftdo.py clasificar
    python3 kraftdo.py generar kraftdo --output ./mi-sistema
    python3 kraftdo.py importar kraftdo --dry-run
    python3 kraftdo.py n8n kraftdo --telegram-id 123456789
    python3 kraftdo.py diff kraftdo
    python3 kraftdo.py test
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

VERDE  = "\033[92m"
ROJO   = "\033[91m"
AMBAR  = "\033[93m"
AZUL   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):  print(f"  {VERDE}✅{RESET} {msg}")
def err(msg): print(f"  {ROJO}❌{RESET} {msg}")
def warn(msg):print(f"  {AMBAR}⚠️ {RESET} {msg}")
def info(msg):print(f"  {AZUL}ℹ️ {RESET} {msg}")

def banner():
    print(f"""
{BOLD}╔══════════════════════════════════════════════════════╗
║              KraftDo Sistema v10 CLI                ║
║        Excel → Sistema Web en minutos               ║
╚══════════════════════════════════════════════════════╝{RESET}
""")


# ── Comando: setup ────────────────────────────────────────────────────────────
def cmd_setup(args):
    """Verifica dependencias y guía la instalación inicial."""
    banner()
    print(f"{BOLD}Verificando dependencias...{RESET}\n")
    
    errores = 0
    
    # Python
    v = sys.version_info
    if v >= (3, 10):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        err(f"Python {v.major}.{v.minor} — se requiere 3.10+")
        errores += 1
    
    # Paquetes Python
    paquetes = [
        ("fastapi",   "FastAPI"),
        ("uvicorn",   "Uvicorn"),
        ("openpyxl",  "OpenPyXL"),
        ("sqlalchemy","SQLAlchemy"),
        ("pymysql",   "PyMySQL"),
        ("gspread",   "gspread"),
        ("pytest",    "pytest"),
    ]
    for pkg, nombre in paquetes:
        try:
            __import__(pkg)
            ok(nombre)
        except ImportError:
            err(f"{nombre} — instalar con: pip install {pkg}")
            errores += 1
    
    # Docker
    result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
    if result.returncode == 0:
        ok(f"Docker — {result.stdout.strip()}")
    else:
        warn("Docker no encontrado — necesario para deploy en VPS")
    
    # .env
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        ok(".env configurado")
        # Verificar variables críticas
        env = {}
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
        
        for var in ["API_KEY", "DB_PASS"]:
            if env.get(var):
                ok(f"  {var} configurado")
            else:
                warn(f"  {var} vacío — configurar en .env")
    else:
        warn(".env no encontrado — copiando desde .env.example")
        example = BASE_DIR / ".env.example"
        if example.exists():
            import shutil
            shutil.copy(example, env_path)
            info("Creado .env desde .env.example — edítalo con tus valores")
        else:
            err(".env.example tampoco encontrado")
            errores += 1
    
    # Empresas configuradas
    empresas_dir = BASE_DIR / "empresas"
    if empresas_dir.exists():
        jsons = list(empresas_dir.glob("*.json"))
        jsons = [j for j in jsons if "ejemplo" not in j.name]
        if jsons:
            ok(f"Empresas: {', '.join(j.stem for j in jsons)}")
        else:
            warn("Sin empresas configuradas — usa 'kraftdo.py clasificar' para crear una")
    
    print()
    if errores == 0:
        print(f"{VERDE}{BOLD}Todo OK — el sistema está listo para usar.{RESET}\n")
        print("Próximos pasos:")
        print("  1. python3 kraftdo.py clasificar    → clasificar tu Excel")
        print("  2. python3 kraftdo.py api            → iniciar la API")
        print("  3. python3 kraftdo.py generar kraft  → generar Laravel")
    else:
        print(f"{ROJO}{BOLD}{errores} problema(s) encontrado(s) — revisar arriba.{RESET}\n")


# ── Comando: clasificar ───────────────────────────────────────────────────────
def cmd_clasificar(args):
    """Abre la UI web de clasificación de Excel."""
    banner()
    port = getattr(args, 'port', 8001)
    print(f"Iniciando Classifier en http://localhost:{port}\n")
    print("  Sube tu Excel, clasifica las hojas y descarga el JSON de configuración.\n")
    os.execv(sys.executable, [sys.executable, str(BASE_DIR / "classifier.py"), "--port", str(port)])


# ── Comando: api ──────────────────────────────────────────────────────────────
def cmd_api(args):
    """Inicia la API REST."""
    banner()
    port = getattr(args, 'port', 8000)
    print(f"Iniciando API en http://localhost:{port}\n")
    print("  Docs: http://localhost:{port}/docs\n")
    
    # Listar empresas disponibles
    empresas_dir = BASE_DIR / "empresas"
    if empresas_dir.exists():
        jsons = [j.stem for j in empresas_dir.glob("*.json") if "ejemplo" not in j.name]
        if jsons:
            info(f"Empresas disponibles: {', '.join(jsons)}")
    
    os.execv(sys.executable, [sys.executable, str(BASE_DIR / "api.py"), "--port", str(port)])


# ── Comando: generar ──────────────────────────────────────────────────────────
def cmd_generar(args):
    """Genera código Laravel+Filament desde el JSON de la empresa."""
    banner()
    from generator import generar
    
    empresa = args.empresa
    output  = getattr(args, 'output', f"./sistema_{empresa}")
    
    print(f"Generando sistema para: {BOLD}{empresa}{RESET}")
    print(f"Output: {output}\n")
    
    try:
        archivos = generar(empresa, output)
        print(f"\n{VERDE}✅ {len(archivos)} archivos generados en: {output}{RESET}")
        print("\nPróximos pasos:")
        print(f"  1. cd {output}")
        print(f"  2. cp .env.example .env && nano .env")
        print(f"  3. chmod +x install.sh && ./install.sh")
        print(f"  4. python3 {BASE_DIR}/kraftdo.py importar {empresa}")
    except FileNotFoundError as e:
        err(str(e))
        sys.exit(1)


# ── Comando: importar ─────────────────────────────────────────────────────────
def cmd_importar(args):
    """Importa datos del Excel a MySQL."""
    banner()
    from importer import Importer
    
    empresa    = args.empresa
    dry_run    = getattr(args, 'dry_run', False)
    solo       = [s.strip() for s in args.solo.split(",")] if getattr(args, 'solo', None) else None
    limpiar    = getattr(args, 'limpiar', False)
    
    print(f"Importando datos de: {BOLD}{empresa}{RESET}")
    print(f"Modo: {'DRY-RUN' if dry_run else 'INSERTAR'}\n")
    
    imp = Importer(empresa)
    if dry_run:
        resultados = imp.dry_run(solo)
    else:
        resultados = imp.importar_todo(solo, limpiar, False)
    
    total = sum(r.get("insertados", r.get("validas", 0)) for r in resultados.values())
    print(f"\n{VERDE}Total: {total} registros procesados{RESET}")


# ── Comando: n8n ──────────────────────────────────────────────────────────────
def cmd_n8n(args):
    """Genera workflows n8n."""
    banner()
    from n8n_generator import generar_todos
    
    empresa      = args.empresa
    output       = getattr(args, 'output', "./n8n_workflows")
    api_url      = getattr(args, 'api_url', "http://localhost:8000")
    telegram_id  = getattr(args, 'telegram_id', "TU_CHAT_ID")
    email        = getattr(args, 'email', "tu@email.cl")
    importar     = getattr(args, 'importar', False)
    
    generar_todos(empresa, output, api_url, telegram_id, email, importar)


# ── Comando: diff ─────────────────────────────────────────────────────────────
def cmd_diff(args):
    """Detecta cambios en el JSON y genera migraciones ALTER TABLE."""
    banner()
    
    if getattr(args, 'watch', False):
        from differ import watch as differ_watch
        differ_watch(args.empresa, args.output, args.intervalo)
    else:
        from differ import main as differ_main
        sys.argv = [sys.argv[0], args.empresa]
        if getattr(args, 'preview', False):
            sys.argv.append('--preview')
        if getattr(args, 'output', None):
            sys.argv += ['--output', args.output]
        differ_main()


# ── Comando: test ─────────────────────────────────────────────────────────────
def cmd_test(args):
    """Corre la suite de tests."""
    banner()
    print("Corriendo tests...\n")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=BASE_DIR
    )
    sys.exit(result.returncode)


def cmd_pipeline(args):
    """Orquestación Prefect."""
    banner()
    pipeline_script = BASE_DIR / "pipeline.py"
    argv = [str(pipeline_script), args.subcomando, args.empresa]
    if getattr(args, "solo", None):
        argv += ["--solo", args.solo]
    if getattr(args, "limpiar", False):
        argv.append("--limpiar")
    if getattr(args, "output", None):
        argv += ["--output", args.output]
    os.execv(sys.executable, [sys.executable] + argv)


# ── Comando: empresas ─────────────────────────────────────────────────────────
def cmd_empresas(args):
    """Lista las empresas configuradas."""
    banner()
    empresas_dir = BASE_DIR / "empresas"
    if not empresas_dir.exists():
        warn("Carpeta 'empresas/' no encontrada")
        return
    
    import json
    jsons = [j for j in empresas_dir.glob("*.json") if "ejemplo" not in j.name]
    
    if not jsons:
        warn("Sin empresas configuradas. Usa 'kraftdo.py clasificar' para crear una.")
        return
    
    print(f"{BOLD}Empresas configuradas ({len(jsons)}):{RESET}\n")
    for j in sorted(jsons):
        try:
            cfg = json.loads(j.read_text())
            nombre = cfg.get("empresa", {}).get("nombre", j.stem)
            tipo   = cfg.get("fuente", {}).get("tipo", "local")
            hojas  = len([h for h in cfg.get("hojas", {}).values() if h.get("tipo") in ("catalogo","registros")])
            print(f"  {BOLD}{j.stem}{RESET}")
            print(f"    Nombre:  {nombre}")
            print(f"    Fuente:  {tipo}")
            print(f"    Hojas:   {hojas} configuradas")
            print()
        except Exception as e:
            err(f"{j.stem}: {e}")


# ── CLI Principal ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog="kraftdo",
        description="KraftDo CLI — Excel → Sistema Web",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="comando", metavar="COMANDO")

    # setup
    p = subparsers.add_parser("setup", help="Verificar dependencias e instalar")
    p.set_defaults(func=cmd_setup)

    # clasificar
    p = subparsers.add_parser("clasificar", help="Abrir UI web para clasificar Excel")
    p.add_argument("--port", type=int, default=8001)
    p.set_defaults(func=cmd_clasificar)

    # api
    p = subparsers.add_parser("api", help="Iniciar API REST")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(func=cmd_api)

    # generar
    p = subparsers.add_parser("generar", help="Generar código Laravel+Filament")
    p.add_argument("empresa", help="Nombre de la empresa (ej: kraftdo)")
    p.add_argument("--output", default=None, help="Directorio de salida")
    p.add_argument("--solo", choices=["migraciones","modelos","filament","api","seeders","requests","pages"])
    p.set_defaults(func=cmd_generar)

    # importar
    p = subparsers.add_parser("importar", help="Importar datos Excel → MySQL")
    p.add_argument("empresa", help="Nombre de la empresa")
    p.add_argument("--solo", help="Hojas separadas por coma")
    p.add_argument("--limpiar", action="store_true")
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    p.add_argument("--db", help="URL de BD")
    p.set_defaults(func=cmd_importar)

    # n8n
    p = subparsers.add_parser("n8n", help="Generar workflows n8n")
    p.add_argument("empresa")
    p.add_argument("--output",      default="./n8n_workflows")
    p.add_argument("--api-url",     default="http://localhost:8000", dest="api_url")
    p.add_argument("--telegram-id", default="TU_CHAT_ID",           dest="telegram_id")
    p.add_argument("--email",       default="tu@email.cl")
    p.add_argument("--importar",    action="store_true")
    p.set_defaults(func=cmd_n8n)

    # diff
    p = subparsers.add_parser("diff", help="Detectar cambios y generar ALTER TABLE")
    p.add_argument("empresa")
    p.add_argument("--output",    default="./diff_migrations")
    p.add_argument("--preview",   action="store_true")
    p.add_argument("--watch",     action="store_true", help="Monitorear cambios automáticamente")
    p.add_argument("--intervalo", type=int, default=5)
    p.set_defaults(func=cmd_diff)

    # test
    p = subparsers.add_parser("test", help="Correr suite de tests")
    p.set_defaults(func=cmd_test)

    # pipeline
    p = subparsers.add_parser("pipeline", help="Orquestación Prefect (sync, validar, backup)")
    p.add_argument("subcomando", choices=["sync","validar","generar","backup","schedule"])
    p.add_argument("empresa")
    p.add_argument("--solo",    help="Hojas separadas por coma")
    p.add_argument("--limpiar", action="store_true")
    p.add_argument("--output",  default=None)
    p.add_argument("--cada",    default="6h")
    p.set_defaults(func=cmd_pipeline)

    # empresas
    p = subparsers.add_parser("empresas", help="Listar empresas configuradas")
    p.set_defaults(func=cmd_empresas)

    args = parser.parse_args()

    if not args.comando:
        banner()
        parser.print_help()
        print("\nEjemplos rápidos:")
        print("  python3 kraftdo.py setup")
        print("  python3 kraftdo.py clasificar")
        print("  python3 kraftdo.py generar kraftdo")
        return

    args.func(args)


if __name__ == "__main__":
    main()
