"""
KraftDo — differ.py
Detecta cambios entre dos versiones del JSON de configuración
y genera las migraciones de ALTER TABLE necesarias.

USO:
    python3 differ.py kraftdo                    # compara con versión guardada
    python3 differ.py kraftdo --old v7.json      # compara con archivo específico
    python3 differ.py kraftdo --preview          # muestra sin escribir
"""

import os
import sys
import json
import re
import time
import argparse
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORIAL_DIR = os.path.join(SCRIPT_DIR, "historial")

# Asegurar que el directorio del sistema esté en el path de Python
# para que los imports funcionen independientemente del CWD
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def tabla(alias: str) -> str:
    return alias.lower().replace("-", "_")


def inferir_tipo_col(nombre: str) -> tuple[str, str]:
    """Mismo sistema que generator.py para consistencia."""
    from generator import inferir_tipo
    return inferir_tipo(nombre)


def cargar_json(ruta: str) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def columnas_de_hoja(hoja_cfg: dict) -> dict:
    """Retorna dict {nombre_campo: tipo_laravel}."""
    cols = hoja_cfg.get("columnas", {})
    resultado = {}
    for campo in cols.keys():
        tipo, mod = inferir_tipo_col(campo)
        resultado[campo] = (tipo, mod)
    return resultado


# ── Comparadores ─────────────────────────────────────────────────────────────
def diff_hojas(cfg_viejo: dict, cfg_nuevo: dict) -> dict:
    """
    Compara las hojas entre dos configs.
    Retorna: {
      "hojas_nuevas":     [...],
      "hojas_eliminadas": [...],
      "hojas_modificadas": { alias: { cols_nuevas, cols_eliminadas, cols_modificadas } }
    }
    """
    hojas_v = {a: h for a, h in cfg_viejo.get("hojas", {}).items()
               if h.get("tipo") in ("catalogo", "registros")}
    hojas_n = {a: h for a, h in cfg_nuevo.get("hojas", {}).items()
               if h.get("tipo") in ("catalogo", "registros")}

    aliases_v = set(hojas_v.keys())
    aliases_n = set(hojas_n.keys())

    nuevas     = list(aliases_n - aliases_v)
    eliminadas = list(aliases_v - aliases_n)
    comunes    = aliases_v & aliases_n

    modificadas = {}
    for alias in comunes:
        cols_v = columnas_de_hoja(hojas_v[alias])
        cols_n = columnas_de_hoja(hojas_n[alias])

        campos_v = set(cols_v.keys())
        campos_n = set(cols_n.keys())

        cols_nuevas     = list(campos_n - campos_v)
        cols_eliminadas = list(campos_v - campos_n)
        cols_modificadas = [
            c for c in (campos_v & campos_n)
            if cols_v[c] != cols_n[c]
        ]

        if cols_nuevas or cols_eliminadas or cols_modificadas:
            modificadas[alias] = {
                "cols_nuevas":     cols_nuevas,
                "cols_eliminadas": cols_eliminadas,
                "cols_modificadas": cols_modificadas,
                "cols_v": cols_v,
                "cols_n": cols_n,
            }

    return {
        "hojas_nuevas":      nuevas,
        "hojas_eliminadas":  eliminadas,
        "hojas_modificadas": modificadas,
    }


# ── Generadores de migración ─────────────────────────────────────────────────
def gen_col_definition(campo: str, tipo: str, mod: str) -> str:
    """Genera definición de columna para ALTER TABLE usando SQLGlot para validar."""
    try:
        import sqlglot
        import sqlglot.expressions as exp

        # Validar nombre de columna con SQLGlot
        campo_seguro = sqlglot.parse_one(
            f"SELECT {campo} FROM t", dialect="mysql"
        ).find(exp.Column).name
    except Exception:
        # Si SQLGlot falla, sanitizar manualmente
        import re
        campo_seguro = re.sub(r"[^a-zA-Z0-9_]", "_", campo)

    if tipo.startswith("decimal"):
        p, s = tipo.split(":")[1].split(",")
        col = f"$table->decimal('{campo_seguro}', {p}, {s})"
    elif tipo.startswith("string:"):
        col = f"$table->string('{campo_seguro}', {tipo.split(':')[1]})"
    elif tipo == "text":
        col = f"$table->text('{campo_seguro}')"
    elif tipo == "integer":
        col = f"$table->integer('{campo_seguro}')"
    elif tipo == "boolean":
        col = f"$table->boolean('{campo_seguro}')"
    elif tipo == "timestamp":
        col = f"$table->timestamp('{campo_seguro}')"
    else:
        col = f"$table->string('{campo_seguro}')"

    if "nullable" in mod:
        col += "->nullable()"
    elif "default:" in mod:
        val = mod.split("default:")[1]
        col += f"->default({val})"
    return col + ";"

def validar_sql_alter(sql: str, dialect: str = "mysql") -> tuple[bool, str]:
    """
    Valida SQL generado por SQLGlot antes de ejecutar.
    Retorna (es_valido, mensaje_error).
    """
    try:
        import sqlglot
        errores = sqlglot.transpile(sql, read=dialect, write=dialect, error_level="raise")
        return True, ""
    except Exception as e:
        return False, str(e)


def gen_alter_migration(alias: str, diff: dict, idx: int) -> str:
    """Genera una migración de ALTER TABLE para una hoja modificada."""
    tabla_n = tabla(alias)
    ts = datetime.now().strftime("%Y_%m_%d") + f"_{idx:06d}"
    clase = "Update" + "".join(w.capitalize() for w in alias.split("_")) + "Table"

    up_lines   = []
    down_lines = []

    # Agregar columnas nuevas
    for campo in diff["cols_nuevas"]:
        tipo, mod = diff["cols_n"][campo]
        col_def = gen_col_definition(campo, tipo, mod)
        up_lines.append(f"            $table->{col_def.lstrip('$table->')}")
        down_lines.append(f"            $table->dropColumn('{campo}');")

    # Eliminar columnas (con precaución)
    for campo in diff["cols_eliminadas"]:
        up_lines.append(f"            $table->dropColumn('{campo}'); // ⚠️ REVISAR antes de ejecutar")
        tipo, mod = diff["cols_v"][campo]
        col_def = gen_col_definition(campo, tipo, mod)
        down_lines.append(f"            $table->{col_def.lstrip('$table->')}")

    # Modificar columnas
    for campo in diff["cols_modificadas"]:
        tipo_n, mod_n = diff["cols_n"][campo]
        tipo_v, mod_v = diff["cols_v"][campo]
        col_def_n = gen_col_definition(campo, tipo_n, mod_n).rstrip(";") + "->change();"
        col_def_v = gen_col_definition(campo, tipo_v, mod_v).rstrip(";") + "->change();"
        up_lines.append(f"            $table->{col_def_n.lstrip('$table->')}")
        down_lines.append(f"            $table->{col_def_v.lstrip('$table->')}")

    up_str   = "\n".join(up_lines)   or "            // Sin cambios"
    down_str = "\n".join(down_lines) or "            // Sin cambios"

    # Validar SQL con SQLGlot antes de retornar
    # (solo verificamos la lógica, no la sintaxis PHP)

    return f"""<?php

use Illuminate\\Database\\Migrations\\Migration;
use Illuminate\\Database\\Schema\\Blueprint;
use Illuminate\\Support\\Facades\\Schema;

// Generado automáticamente por KraftDo differ.py
// Cambios detectados en: {alias}
// Columnas nuevas: {diff['cols_nuevas']}
// Columnas eliminadas: {diff['cols_eliminadas']}
// Columnas modificadas: {diff['cols_modificadas']}

return new class extends Migration
{{
    public function up(): void
    {{
        Schema::table('{tabla_n}', function (Blueprint $table) {{
{up_str}
        }});
    }}

    public function down(): void
    {{
        Schema::table('{tabla_n}', function (Blueprint $table) {{
{down_str}
        }});
    }}
}};
"""


def gen_create_migration(alias: str, hoja_cfg: dict, idx: int) -> str:
    """Genera migración de CREATE TABLE para una hoja nueva."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "generator", os.path.join(SCRIPT_DIR, "generator.py")
        )
        gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen)
        return gen.gen_migracion(alias, hoja_cfg, idx)
    except Exception:
        from generator import gen_migracion
        return gen_migracion(alias, hoja_cfg, idx)


# ── Historial ─────────────────────────────────────────────────────────────────
def guardar_snapshot(empresa: str, cfg: dict):
    """Guarda snapshot del JSON actual en historial/."""
    os.makedirs(HISTORIAL_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(HISTORIAL_DIR, f"{empresa}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    return path


def ultimo_snapshot(empresa: str) -> str | None:
    """Retorna ruta al último snapshot de una empresa."""
    if not os.path.exists(HISTORIAL_DIR):
        return None
    archivos = sorted([
        f for f in os.listdir(HISTORIAL_DIR)
        if f.startswith(empresa) and f.endswith(".json")
    ])
    if not archivos:
        return None
    return os.path.join(HISTORIAL_DIR, archivos[-1])


# ── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="KraftDo Differ — Detecta cambios en el JSON")
    parser.add_argument("empresa")
    parser.add_argument("--old",       help="JSON viejo para comparar (default: último snapshot)")
    parser.add_argument("--output",    default="./diff_migrations")
    parser.add_argument("--preview",   action="store_true")
    parser.add_argument("--watch",     action="store_true", help="Monitorear cambios automáticamente")
    parser.add_argument("--intervalo", type=int, default=5,  help="Segundos entre checks en modo watch")
    args = parser.parse_args()

    if args.watch:
        watch(args.empresa, args.output, args.intervalo)
        return

    cfg_nuevo_path = os.path.join(SCRIPT_DIR, "empresas", f"{args.empresa}.json")
    cfg_nuevo = cargar_json(cfg_nuevo_path)

    cfg_viejo_path = args.old or ultimo_snapshot(args.empresa)
    if not cfg_viejo_path or not os.path.exists(cfg_viejo_path):
        print(f"⚠️  No hay versión anterior. Guardando snapshot inicial...")
        snap = guardar_snapshot(args.empresa, cfg_nuevo)
        print(f"✅ Snapshot guardado: {snap}")
        print(f"   Modifica tu JSON y ejecuta differ.py de nuevo para ver los cambios.")
        return

    cfg_viejo = cargar_json(cfg_viejo_path)
    diff = diff_hojas(cfg_viejo, cfg_nuevo)

    print(f"\n{'='*60}")
    print(f"  KraftDo Differ — {args.empresa}")
    print(f"  Comparando con: {os.path.basename(cfg_viejo_path)}")
    print(f"{'='*60}\n")

    # Resumen
    total_cambios = (len(diff["hojas_nuevas"]) + len(diff["hojas_eliminadas"]) +
                     len(diff["hojas_modificadas"]))

    if total_cambios == 0:
        print("  ✅ Sin cambios detectados entre versiones\n")
        guardar_snapshot(args.empresa, cfg_nuevo)
        return

    if diff["hojas_nuevas"]:
        print(f"  ➕ Hojas nuevas:      {diff['hojas_nuevas']}")
    if diff["hojas_eliminadas"]:
        print(f"  ➖ Hojas eliminadas:  {diff['hojas_eliminadas']}")
    if diff["hojas_modificadas"]:
        for alias, cambios in diff["hojas_modificadas"].items():
            print(f"  ✏️  {alias}:")
            if cambios["cols_nuevas"]:     print(f"      + {cambios['cols_nuevas']}")
            if cambios["cols_eliminadas"]: print(f"      - {cambios['cols_eliminadas']}")
            if cambios["cols_modificadas"]:print(f"      ~ {cambios['cols_modificadas']}")

    if preview := args.preview:
        print(f"\n  [PREVIEW — no se escriben archivos]\n")
        return

    # Generar migraciones
    os.makedirs(args.output, exist_ok=True)
    idx = 1

    for alias in diff["hojas_nuevas"]:
        hoja_cfg = cfg_nuevo["hojas"].get(alias, {})
        contenido = gen_create_migration(alias, hoja_cfg, idx)
        nombre = f"{datetime.now().strftime('%Y_%m_%d')}_{idx:06d}_create_{tabla(alias)}_table.php"
        path = os.path.join(args.output, nombre)
        with open(path, "w") as f:
            f.write(contenido)
        print(f"\n  ✅ {nombre}")
        idx += 1

    for alias, cambios in diff["hojas_modificadas"].items():
        contenido = gen_alter_migration(alias, cambios, idx)
        nombre = f"{datetime.now().strftime('%Y_%m_%d')}_{idx:06d}_update_{tabla(alias)}_table.php"
        path = os.path.join(args.output, nombre)
        with open(path, "w") as f:
            f.write(contenido)
        print(f"\n  ✅ {nombre}")
        idx += 1

    guardar_snapshot(args.empresa, cfg_nuevo)
    print(f"\n  Migraciones en: {args.output}")
    print(f"  Ejecutar: php artisan migrate\n")


def watch(empresa: str, output_dir: str, intervalo: int = 5):
    """
    Modo watch: monitorea el JSON de la empresa y genera migraciones
    automáticamente cuando detecta cambios.
    """
    cfg_path = os.path.join(SCRIPT_DIR, "empresas", f"{empresa}.json")
    if not os.path.exists(cfg_path):
        print(f"❌ No encontré: {cfg_path}")
        sys.exit(1)

    print(f"""
╔══════════════════════════════════════════════════════╗
║           KraftDo Differ — Modo Watch               ║
╚══════════════════════════════════════════════════════╝

Monitoreando: {cfg_path}
Intervalo: cada {intervalo} segundos
Ctrl+C para detener.
""")

    ultimo_mtime = 0
    ultimo_snapshot_path = ultimo_snapshot(empresa)

    while True:
        try:
            mtime = os.path.getmtime(cfg_path)
            if mtime != ultimo_mtime:
                ultimo_mtime = mtime
                now = datetime.now().strftime("%H:%M:%S")

                if ultimo_snapshot_path and os.path.exists(ultimo_snapshot_path):
                    cfg_nuevo = cargar_json(cfg_path)
                    cfg_viejo = cargar_json(ultimo_snapshot_path)
                    diff = diff_hojas(cfg_viejo, cfg_nuevo)

                    total = (len(diff["hojas_nuevas"]) +
                             len(diff["hojas_eliminadas"]) +
                             len(diff["hojas_modificadas"]))

                    if total > 0:
                        print(f"[{now}] 🔄 Cambio detectado — {total} modificación(es)")

                        os.makedirs(output_dir, exist_ok=True)
                        idx = 1

                        for alias in diff["hojas_nuevas"]:
                            hoja_cfg = cfg_nuevo["hojas"].get(alias, {})
                            contenido = gen_create_migration(alias, hoja_cfg, idx)
                            nombre = f"{datetime.now().strftime('%Y_%m_%d')}_{idx:06d}_create_{tabla(alias)}_table.php"
                            path = os.path.join(output_dir, nombre)
                            with open(path, "w") as f:
                                f.write(contenido)
                            print(f"  ✅ Nueva: {nombre}")
                            idx += 1

                        for alias, cambios in diff["hojas_modificadas"].items():
                            contenido = gen_alter_migration(alias, cambios, idx)
                            nombre = f"{datetime.now().strftime('%Y_%m_%d')}_{idx:06d}_update_{tabla(alias)}_table.php"
                            path = os.path.join(output_dir, nombre)
                            with open(path, "w") as f:
                                f.write(contenido)
                            print(f"  ✅ Modificada: {nombre}")
                            idx += 1

                        ultimo_snapshot_path = guardar_snapshot(empresa, cfg_nuevo)
                        print(f"  📸 Snapshot guardado")
                    else:
                        print(f"[{now}] 📁 Archivo modificado — sin cambios estructurales")
                else:
                    # Primera vez — guardar snapshot inicial
                    cfg = cargar_json(cfg_path)
                    ultimo_snapshot_path = guardar_snapshot(empresa, cfg)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📸 Snapshot inicial guardado")

            time.sleep(intervalo)

        except KeyboardInterrupt:
            print("\n👋 Watch detenido.")
            break
        except Exception as e:
            print(f"  ⚠️  Error: {e}")
            time.sleep(intervalo)


if __name__ == "__main__":
    main()
