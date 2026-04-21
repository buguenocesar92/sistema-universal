"""
onboarding_steps.py — Pasos de onboarding con interface comun
Cada paso implementa: name, description, ejecutar(contexto) -> resultado

Agregar un paso nuevo = crear una funcion con @paso y listo.
La orden se infiere del orden del decorator.
"""
import json, re, shutil, sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Any

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))


@dataclass
class Contexto:
    """Contexto que se pasa entre pasos de onboarding."""
    empresa:          str
    cfg:              dict
    archivos_generados: int = 0
    pasos_completados: list = field(default_factory=list)
    pasos_fallidos:    list = field(default_factory=list)

    @property
    def nombre_empresa(self) -> str:
        return self.cfg.get("empresa", {}).get("nombre", self.empresa)


@dataclass
class Paso:
    """Definicion de un paso de onboarding."""
    nombre:      str
    descripcion: str
    fn:          Callable[[Contexto], Any]
    critico:     bool = False  # si es critico, la falla detiene el onboarding

    def ejecutar(self, ctx: Contexto) -> tuple[bool, Any]:
        """Ejecuta el paso. Retorna (exito, resultado)."""
        try:
            resultado = self.fn(ctx)
            ctx.pasos_completados.append(self.nombre)
            return True, resultado
        except Exception as e:
            ctx.pasos_fallidos.append({"paso": self.nombre, "error": str(e)})
            return False, str(e)


# ── Registry de pasos ────────────────────────────────────────────────────────
PASOS: list[Paso] = []

def paso(nombre: str, descripcion: str, critico: bool = False):
    """Decorator para registrar un paso en orden de declaración."""
    def wrap(fn):
        PASOS.append(Paso(nombre=nombre, descripcion=descripcion, fn=fn, critico=critico))
        return fn
    return wrap


# ── Pasos del onboarding ────────────────────────────────────────────────────
EMPRESAS_DIR = SCRIPT_DIR / "empresas"
LARAVEL_DIR  = SCRIPT_DIR / "laravel_multitenant"


@paso("json", "Guardar JSON de configuración", critico=True)
def guardar_json(ctx: Contexto) -> Path:
    EMPRESAS_DIR.mkdir(exist_ok=True)
    ruta = EMPRESAS_DIR / f"{ctx.empresa}.json"
    ruta.write_text(json.dumps(ctx.cfg, indent=2, ensure_ascii=False))
    return ruta


@paso("laravel_db", "Agregar conexión a database.php")
def agregar_conexion_laravel(ctx: Contexto):
    db_file = LARAVEL_DIR / "config" / "database.php"
    if not db_file.exists():
        return None

    contenido = db_file.read_text()
    if f"'{ctx.empresa}'" in contenido:
        return "ya_existe"

    db_name = f"kraftdo_{ctx.empresa}"
    bloque = f"""
        '{ctx.empresa}' => [
            'driver'    => 'mysql',
            'host'      => env('DB_HOST', 'mysql'),
            'port'      => env('DB_PORT', '3306'),
            'database'  => env('DB_DATABASE_{ctx.empresa.upper()}', '{db_name}'),
            'username'  => env('DB_USERNAME', 'kraftdo'),
            'password'  => env('DB_PASSWORD', ''),
            'charset'   => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix'    => '',
            'strict'    => true,
            'engine'    => null,
        ],
"""
    contenido = contenido.replace(
        "    ],\n\n    'migrations'",
        f"{bloque}    ],\n\n    'migrations'"
    )
    db_file.write_text(contenido)
    return "agregado"


@paso("laravel_files", "Generar archivos Laravel", critico=True)
def generar_laravel(ctx: Contexto) -> int:
    from generator import generar

    output_dir = SCRIPT_DIR / f"_generated_{ctx.empresa}"
    generar(ctx.empresa, output_dir=str(output_dir))

    empresa_cap = ctx.empresa.replace("_", " ").title().replace(" ", "")

    # Copiar modelos con namespace correcto
    src_models = output_dir / "app" / "Models"
    dst_models = LARAVEL_DIR / "app" / "Models" / empresa_cap
    if src_models.exists():
        shutil.copytree(src_models, dst_models, dirs_exist_ok=True)
        for modelo in dst_models.glob("*.php"):
            contenido = modelo.read_text()
            contenido = re.sub(
                r'(class \w+ extends Model\s*\{)',
                f"\\1\n    protected $connection = '{ctx.empresa}';\n",
                contenido
            )
            contenido = contenido.replace(
                "namespace App\\Models;",
                f"namespace App\\Models\\{empresa_cap};"
            )
            modelo.write_text(contenido)

    # Contar archivos y limpiar
    total = sum(1 for _ in output_dir.rglob("*.php"))
    ctx.archivos_generados = total
    shutil.rmtree(output_dir, ignore_errors=True)
    return total


@paso("reporte", "Registrar empresa en reporte_base.py")
def registrar_reporte(ctx: Contexto):
    """Agrega la empresa al dict REPORTES de reporte_base.py con config por defecto."""
    rb_file = SCRIPT_DIR / "reporte_base.py"
    if not rb_file.exists():
        return "reporte_base_no_existe"

    contenido = rb_file.read_text()
    if f'"{ctx.empresa}":' in contenido:
        return "ya_existe"

    color_p = ctx.cfg.get("empresa", {}).get("color_primary", "1A1A2E")
    color_a = ctx.cfg.get("empresa", {}).get("color_accent",  "E94560")

    # Construir secciones default desde las hojas del JSON
    secciones = []
    for alias, hoja in ctx.cfg.get("hojas", {}).items():
        if hoja.get("tipo") == "kpis":
            secciones.append({"tipo": "kpis", "alias": alias, "titulo": alias.replace("_", " ").title()})
        elif hoja.get("tipo") in ("registros", "catalogo"):
            secciones.append({"tipo": "registros", "alias": alias, "titulo": alias.replace("_", " ").title(), "limit": 15})

    nuevo_bloque = f'''    "{ctx.empresa}": {{
        "nombre":          "{ctx.nombre_empresa}",
        "email_default":   "hola@kraftdo.cl",
        "color_primary":   "{color_p}",
        "color_accent":    "{color_a}",
        "subject":         "Reporte — {ctx.nombre_empresa}",
        "secciones": {json.dumps(secciones, indent=12)[:-1]}        ],
    }},
'''
    # Insertar antes del cierre del dict REPORTES
    contenido = contenido.replace(
        "}\n\n\n# ── Helpers",
        nuevo_bloque + "}\n\n\n# ── Helpers",
        1
    )
    rb_file.write_text(contenido)
    return "registrado"


@paso("portal", "Registrar en portal de upload")
def registrar_en_portal(ctx: Contexto):
    portal = SCRIPT_DIR / "upload_portal.py"
    if not portal.exists():
        return "portal_no_existe"

    contenido = portal.read_text()
    if f'"{ctx.empresa}"' in contenido:
        return "ya_registrado"

    contenido = contenido.replace(
        '"kraftdo_bd":   {"nombre": "KraftDo SpA (BD Maestra)", "reporte": "reporte_kraftdo.py"},',
        f'"kraftdo_bd":   {{"nombre": "KraftDo SpA (BD Maestra)", "reporte": "reporte_kraftdo.py"}},\n'
        f'    "{ctx.empresa}":      {{"nombre": "{ctx.nombre_empresa}", "reporte": "reporte_base.py"}},'
    )
    portal.write_text(contenido)
    return "registrado"


@paso("mysql", "Agregar BD a init.sql")
def agregar_bd_mysql(ctx: Contexto):
    init_sql = SCRIPT_DIR / "docker" / "mysql" / "init.sql"
    if not init_sql.exists():
        return "init_sql_no_existe"

    db_name = f"kraftdo_{ctx.empresa}"
    contenido = init_sql.read_text()

    if db_name in contenido:
        return "ya_existe"

    nuevo_bloque = f"""
CREATE DATABASE IF NOT EXISTS {db_name}
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON {db_name}.* TO 'kraftdo'@'%';
"""
    contenido = contenido.replace("FLUSH PRIVILEGES;", nuevo_bloque + "\nFLUSH PRIVILEGES;")
    init_sql.write_text(contenido)
    return "creado"


# ── Orquestador ─────────────────────────────────────────────────────────────
def ejecutar_onboarding(empresa: str, cfg: dict) -> dict:
    """
    Ejecuta todos los pasos registrados en orden.
    Si un paso crítico falla, detiene el onboarding.
    """
    ctx = Contexto(empresa=empresa, cfg=cfg)

    print(f"\n{'='*60}")
    print(f"  KraftDo Onboarding — {ctx.nombre_empresa}")
    print(f"  Pasos registrados: {len(PASOS)}")
    print(f"{'='*60}\n")

    resultados = {}
    for p in PASOS:
        print(f"▶ {p.nombre} - {p.descripcion}")
        exito, resultado = p.ejecutar(ctx)
        status = "✅" if exito else "❌"
        print(f"  {status} {resultado}")
        resultados[p.nombre] = {"exito": exito, "resultado": str(resultado)}

        if not exito and p.critico:
            print(f"\n❌ Paso crítico falló, abortando onboarding")
            break

    # Email de confirmación al final (no es un paso, es siempre)
    try:
        from onboarding import enviar_confirmacion
        enviar_confirmacion(empresa, cfg, ctx.archivos_generados)
    except Exception as e:
        print(f"  ⚠️  Email confirmación: {e}")

    print(f"\n{'='*60}")
    print(f"  Completados: {len(ctx.pasos_completados)} / {len(PASOS)}")
    if ctx.pasos_fallidos:
        print(f"  Fallidos: {len(ctx.pasos_fallidos)}")
    print(f"{'='*60}\n")

    return {
        "empresa":          empresa,
        "pasos":            resultados,
        "completados":      len(ctx.pasos_completados),
        "fallidos":         len(ctx.pasos_fallidos),
        "archivos_laravel": ctx.archivos_generados,
        "ok":               len(ctx.pasos_fallidos) == 0,
    }


# Compatibilidad con el onboarding() original
def onboarding(empresa: str, cfg: dict) -> dict:
    return ejecutar_onboarding(empresa, cfg)
