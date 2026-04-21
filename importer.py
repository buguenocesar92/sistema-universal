"""
KraftDo — importer.py
Importa los datos actuales del Excel a la base de datos MySQL
que generó el generator.py.

USO:
    python3 importer.py kraftdo                          # importa todo
    python3 importer.py kraftdo --solo pedidos,clientes  # solo esas hojas
    python3 importer.py kraftdo --preview                # muestra sin insertar
    python3 importer.py kraftdo --limpiar                # borra antes de insertar

REQUISITOS:
    pip install sqlalchemy pymysql
    Variables de entorno (o archivo .env):
        DB_HOST=localhost
        DB_PORT=3306
        DB_NAME=kraftdo
        DB_USER=root
        DB_PASS=secret
"""

import os
import sys
import json
import argparse
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Any

# Integración con normalizer
try:
    from normalizer import detectar_patron, normalizar
    NORMALIZER_OK = True
except ImportError:
    NORMALIZER_OK = False

# ── Validadores Pydantic v2 ───────────────────────────────────────────────────
try:
    from pydantic import BaseModel, field_validator, model_validator, ValidationError
    import pydantic

    def _crear_modelo_hoja(alias: str, cfg_hoja: dict) -> type:
        """
        Genera dinámicamente un modelo Pydantic v2 para una hoja.
        Campos requeridos se infieren del JSON de configuración.
        """
        from generator import inferir_tipo
        import re

        campos_hoja = cfg_hoja.get("columnas", {})
        estados     = cfg_hoja.get("logica", {}).get("estados", [])
        ident       = cfg_hoja.get("identificador")
        annotations = {}
        defaults    = {}
        validators  = {}

        for campo in campos_hoja.keys():
            if campo == ident:
                annotations[campo] = str
                defaults[campo]    = ...  # requerido
            else:
                annotations[campo] = Optional[Any]
                defaults[campo]    = None

        # Crear clase dinámicamente
        namespace = {
            "__annotations__": annotations,
            "model_config": {"extra": "allow", "str_strip_whitespace": True},
        }
        namespace.update(defaults)
        modelo = type(f"{alias.title()}Row", (BaseModel,), namespace)
        return modelo

    PYDANTIC_OK = True

except ImportError:
    PYDANTIC_OK = False
    ValidationError = Exception

# Cargar .env si existe
def cargar_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

cargar_env()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from core import Sistema, _num, _str


# ── Conexión a base de datos ─────────────────────────────────────────────────
def get_engine(db_url: str = None):
    try:
        from sqlalchemy import create_engine
    except ImportError:
        raise ImportError("Instalar: pip install sqlalchemy pymysql")

    if not db_url:
        host = os.environ.get("DB_HOST", "localhost")
        port = os.environ.get("DB_PORT", "3306")
        name = os.environ.get("DB_NAME", "kraftdo")
        user = os.environ.get("DB_USER", "root")
        pwd  = os.environ.get("DB_PASS", "")
        db_url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{name}?charset=utf8mb4"

    return create_engine(db_url, echo=False)


# ── Limpieza de valores para MySQL ───────────────────────────────────────────
def limpiar_valor(v, campo: str):
    """Convierte valores del Excel a tipos seguros para MySQL."""
    if v is None or v == "" or v == "-":
        return None

    nombre = campo.lower()

    # Fechas
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else str(v)

    # Números: precio, monto, costo, total, etc.
    es_numero = any(p in nombre for p in (
        "precio", "monto", "costo", "total", "saldo", "anticipo",
        "ganancia", "margen", "descuento", "iva", "ahorro",
        "cantidad", "stock", "dias", "horas", "gramos", "pct"
    ))
    if es_numero:
        return _num(v) or None

    # Strings
    s = str(v).strip()
    return s if s else None


# ── Importador principal ─────────────────────────────────────────────────────
class Importer:
    def __init__(self, empresa: str, db_url: str = None):
        self.sistema = Sistema(empresa)
        self.cfg     = self.sistema.cfg
        self.engine  = get_engine(db_url)
        self.empresa = empresa

    def dry_run(self, solo: list = None) -> dict:
        """Valida los datos sin insertar — genera reporte detallado de errores."""
        resultados = {}
        hojas = self.cfg["hojas"]

        for alias, cfg_hoja in hojas.items():
            if cfg_hoja.get("tipo") not in ("catalogo", "registros"):
                continue
            if solo and alias not in solo:
                continue

            cols = cfg_hoja.get("columnas", {})
            filas_raw = self.sistema._db.filas(cfg_hoja["nombre"], cfg_hoja.get("fila_datos", 5))

            errores   = []
            warnings  = []
            ok        = 0

            for i, fila_raw in enumerate(filas_raw, 1):
                fila_ext = list(fila_raw) + [None] * 30
                from core import _col_idx, _limpio
                reg = {}
                for campo, letra in cols.items():
                    idx = _col_idx(letra)
                    reg[campo] = _limpio(fila_ext[idx])

                ident = cfg_hoja.get("identificador")
                if ident and not reg.get(ident):
                    continue  # fila vacía

                # Validación con Pydantic si está disponible
                if PYDANTIC_OK:
                    try:
                        modelo_cls = _crear_modelo_hoja(alias, cfg_hoja)
                        modelo_cls(**reg)
                    except ValidationError as ve:
                        for err in ve.errors():
                            campo_err = ".".join(str(e) for e in err["loc"])
                            errores.append(f"Fila {i}: {campo_err} — {err['msg']}")
                    except Exception:
                        pass  # fallback a validación básica

                # Validar campos numéricos (fallback)
                for campo, val in reg.items():
                    tipo_field = any(p in campo for p in ("precio","monto","costo","total","cantidad","stock"))
                    if tipo_field and val is not None:
                        try:
                            _num(val)
                        except Exception:
                            if not any(campo in e for e in errores):
                                errores.append(f"Fila {i}: {campo}='{val}' no es un número válido")

                # Validar fechas
                for campo, val in reg.items():
                    if "fecha" in campo and val is not None and not isinstance(val, (int, float)):
                        from datetime import datetime
                        try:
                            if isinstance(val, str) and "/" in val:
                                datetime.strptime(val, "%d/%m/%Y")
                        except Exception:
                            warnings.append(f"Fila {i}: {campo}='{val}' formato de fecha inusual")

                ok += 1

            estado = "✅" if not errores else "❌"
            print(f"  {estado} {alias}: {ok} filas válidas, {len(errores)} errores, {len(warnings)} warnings")
            for e in errores[:3]:
                print(f"      ERROR: {e}")
            for w in warnings[:3]:
                print(f"      WARN:  {w}")

            resultados[alias] = {
                "validas": ok, "errores": len(errores), "warnings": len(warnings),
                "detalle_errores": errores, "detalle_warnings": warnings
            }

        return resultados

    def _insertar_filas_normalizadas(self, tabla_n: str, filas: list,
                                     limpiar: bool, preview: bool) -> dict:
        """Inserta filas ya normalizadas (sin mapeo de columnas del config)."""
        if preview or not filas:
            return {"insertados": 0, "omitidos": 0, "preview": preview, "tabla": tabla_n}

        from sqlalchemy import text, inspect
        with self.engine.connect() as conn:
            insp = inspect(self.engine)
            if not insp.has_table(tabla_n):
                return {"insertados": 0, "error": f"tabla {tabla_n} no existe"}
            cols_bd = {c["name"] for c in insp.get_columns(tabla_n)} - {"id","created_at","updated_at"}
            if limpiar:
                conn.execute(text(f"DELETE FROM `{tabla_n}`"))
                conn.commit()
            insertados = 0
            for fila in filas:
                reg = {k: v for k, v in fila.items() if k in cols_bd and v is not None}
                if not reg:
                    continue
                campos_sql = ", ".join(f"`{k}`" for k in reg)
                valores_sql = ", ".join(f":{k}" for k in reg)
                sql = text(f"INSERT INTO `{tabla_n}` ({campos_sql}) VALUES ({valores_sql})")
                try:
                    conn.execute(sql, reg)
                    insertados += 1
                except Exception:
                    pass
            conn.commit()
        print(f"  ✅ {tabla_n}: {insertados} filas normalizadas insertadas")
        return {"insertados": insertados, "omitidos": 0, "tabla": tabla_n}

    def importar_todo(self, solo: list = None, limpiar: bool = False,
                      preview: bool = False) -> dict:
        """Importa todas las hojas configuradas como 'registros' o 'catalogo'."""
        resultados = {}
        hojas = self.cfg["hojas"]

        for alias, cfg_hoja in hojas.items():
            tipo = cfg_hoja.get("tipo")
            if tipo not in ("catalogo", "registros"):
                continue
            if solo and alias not in solo:
                continue

            try:
                # Hojas consolidadas: importar cada fuente con su tipo
                if cfg_hoja.get("consolidado"):
                    r = self.importar_hoja_consolidada(alias, cfg_hoja, limpiar, preview)
                else:
                    r = self.importar_hoja(alias, cfg_hoja, limpiar, preview)
                resultados[alias] = r
            except Exception as e:
                resultados[alias] = {"error": str(e), "insertados": 0}
                print(f"  ❌ {alias}: {e}")

        return resultados

    def importar_hoja_consolidada(self, alias: str, cfg_hoja: dict,
                                   limpiar: bool, preview: bool) -> dict:
        """
        Importa múltiples hojas fuente en una sola tabla consolidada.
        Agrega automáticamente el campo `tipo` a cada fila.
        """
        fuentes  = cfg_hoja.get("fuentes", [])
        tabla_n  = alias.lower().replace("-", "_")
        cfg_orig = self.cfg  # config original con las hojas fuente

        # Buscar las hojas fuente en el JSON original
        # (pueden no estar en el JSON consolidado)
        json_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "empresas", f"{self.empresa}.json"
        )
        # Cargar JSON original para acceder a las hojas fuente
        # (en el JSON consolidado las hojas fuente ya no existen)
        import os, json as _json
        cfg_original_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "empresas", f"{self.empresa}.json"
        )
        if os.path.exists(cfg_original_path):
            with open(cfg_original_path, encoding="utf-8") as _f:
                cfg_fuente_original = _json.load(_f)
        else:
            # Fallback: intentar encontrar las hojas fuente en el cfg actual
            cfg_fuente_original = self.cfg

        total_insertados = 0
        total_omitidos   = 0
        primera_vez      = True

        from sqlalchemy import text, inspect
        with self.engine.connect() as conn:
            insp = inspect(self.engine)
            if not insp.has_table(tabla_n):
                print(f"  ⚠️  {alias}: tabla '{tabla_n}' no existe")
                return {"insertados": 0, "error": "tabla no existe"}
            cols_bd = {c["name"] for c in insp.get_columns(tabla_n)} - {"id","created_at","updated_at"}

            if limpiar and primera_vez:
                conn.execute(text(f"DELETE FROM `{tabla_n}`"))
                conn.commit()

            for fuente_alias in fuentes:
                # Buscar config de la hoja fuente
                cfg_fuente = None
                for origen_alias, h in cfg_fuente_original["hojas"].items():
                    if origen_alias == fuente_alias:
                        cfg_fuente = h
                        break

                if not cfg_fuente:
                    print(f"  ⚠️  Fuente '{fuente_alias}' no encontrada en el config")
                    continue

                tipo_valor = fuente_alias.lower().replace("-", "_")
                cols_fuente = cfg_fuente.get("columnas", {})
                fila_ini    = cfg_fuente.get("fila_datos", 5)

                try:
                    filas_raw = self.sistema._db.filas(cfg_fuente["nombre"], fila_ini)
                except Exception as e:
                    print(f"  ⚠️  {fuente_alias}: {e}")
                    continue

                insertados_fuente = 0
                for fila_raw in filas_raw:
                    fila_ext = list(fila_raw) + [None] * 30
                    from core import _col_idx, _limpio
                    reg = {"tipo": tipo_valor}
                    for campo, letra in cols_fuente.items():
                        if campo == "tipo":
                            continue
                        idx = _col_idx(letra)
                        val = limpiar_valor(_limpio(fila_ext[idx]), campo)
                        reg[campo] = val

                    ident = cfg_fuente.get("identificador")
                    if ident and not reg.get(ident):
                        continue
                    if not any(v for k, v in reg.items() if k != "tipo"):
                        continue

                    if preview:
                        insertados_fuente += 1
                        continue

                    reg_ok = {k: v for k, v in reg.items() if k in cols_bd and v is not None}
                    if not reg_ok:
                        total_omitidos += 1
                        continue

                    campos_sql  = ", ".join(f"`{k}`" for k in reg_ok)
                    valores_sql = ", ".join(f":{k}" for k in reg_ok)
                    sql = text(f"INSERT INTO `{tabla_n}` ({campos_sql}) VALUES ({valores_sql})")
                    try:
                        conn.execute(sql, reg_ok)
                        insertados_fuente += 1
                    except Exception:
                        total_omitidos += 1

                total_insertados += insertados_fuente
                modo = "preview" if preview else "insertados"
                print(f"  ✅ {fuente_alias} → '{tabla_n}' (tipo={tipo_valor}): {insertados_fuente} {modo}")

            if not preview:
                conn.commit()

        return {"insertados": total_insertados, "omitidos": total_omitidos, "tabla": tabla_n}

    def importar_hoja(self, alias: str, cfg_hoja: dict,
                      limpiar: bool = False, preview: bool = False) -> dict:
        """Importa una hoja al tabla correspondiente."""
        from sqlalchemy import text, inspect

        tabla_n = alias.lower().replace("-", "_")
        cols    = cfg_hoja.get("columnas", {})

        # ── Detectar patrón estructural antes de importar ─────────────────
        es_consolidado = cfg_hoja.get("consolidado", False)
        tipo_consolidado = None

        if NORMALIZER_OK and hasattr(self.sistema._db, '_path'):
            try:
                import openpyxl
                wb = openpyxl.load_workbook(self.sistema._db._path, data_only=True)
                nombre_hoja = cfg_hoja["nombre"]
                ws = next((wb[h] for h in wb.sheetnames
                           if nombre_hoja.lower() in h.lower()), None)
                if ws:
                    diag = detectar_patron(ws, cfg_hoja.get("fila_datos", 5))
                    patron = diag["patron"]

                    if patron not in ("vertical", "con_totales") and not preview:
                        print(f"  ⚠️  {alias}: patrón '{patron}' detectado — normalizando antes de importar")

                    if patron == "horizontal":
                        # Unpivot automático
                        resultado = normalizar(ws, diag)
                        filas_normalizadas = resultado["filas"]
                        print(f"  ↔️   {alias}: unpivot → {len(filas_normalizadas)} filas")
                        # Para tablas horizontales, insertar directamente
                        return self._insertar_filas_normalizadas(
                            tabla_n, filas_normalizadas, limpiar, preview
                        )
                    elif patron == "con_totales":
                        resultado = normalizar(ws, diag)
                        # Continuar con filas normalizadas (sin totales)
                        # pero usando el mapeo de columnas estándar
                        excluidas = resultado["excluidas"]
                        if excluidas and not preview:
                            print(f"  ✂️   {alias}: excluyendo {len(excluidas)} filas de totales")
                    elif patron == "multi_header":
                        resultado = normalizar(ws, diag)
                        filas_normalizadas = resultado["filas"]
                        return self._insertar_filas_normalizadas(
                            tabla_n, filas_normalizadas, limpiar, preview
                        )
            except Exception as e:
                pass  # si falla el normalizer, continuar con importación estándar

        # ── Para hojas consolidadas: agregar campo tipo ───────────────────
        if es_consolidado:
            # El alias en la tabla consolidada viene del fuente original
            # tipo_consolidado se infiere del alias de la hoja fuente
            pass  # se maneja al mapear los campos
        # ─────────────────────────────────────────────────────────────────

        # Leer filas del Excel (flujo estándar)
        filas_raw = self.sistema._db.filas(cfg_hoja["nombre"], cfg_hoja.get("fila_datos", 5))

        # Mapear a dicts usando columnas del config
        registros = []
        for fila_raw in filas_raw:
            fila_ext = list(fila_raw) + [None] * 30
            reg = {}
            for campo, letra in cols.items():
                if campo in ("numero",):  # numero lo manejamos aparte
                    continue
                from core import _col_idx, _limpio
                idx = _col_idx(letra)
                val = limpiar_valor(_limpio(fila_ext[idx]), campo)
                reg[campo] = val

            # Saltar filas completamente vacías
            ident = cfg_hoja.get("identificador")
            if ident and not reg.get(ident):
                continue
            if not ident and not any(v is not None for v in reg.values()):
                continue

            registros.append(reg)

        if not registros:
            print(f"  ⚠️  {alias}: sin datos para importar")
            return {"insertados": 0, "omitidos": 0, "tabla": tabla}

        if preview:
            print(f"\n  📋 {alias} → tabla '{tabla}'")
            print(f"     {len(registros)} filas encontradas")
            print(f"     Ejemplo: {registros[0]}")
            return {"insertados": 0, "omitidos": 0, "preview": True, "tabla": tabla}

        with self.engine.connect() as conn:
            # Verificar que la tabla existe
            insp = inspect(self.engine)
            if not insp.has_table(tabla_n):
                print(f"  ⚠️  {alias}: tabla '{tabla_n}' no existe — ejecuta php artisan migrate primero")
                return {"insertados": 0, "omitidos": 0, "error": f"tabla {tabla_n} no existe"}

            # Obtener columnas reales de la BD
            cols_bd = {c["name"] for c in insp.get_columns(tabla_n)}
            cols_bd -= {"id", "created_at", "updated_at"}

            if limpiar:
                conn.execute(text(f"DELETE FROM `{tabla_n}`"))
                conn.commit()
                print(f"  🧹 {alias}: tabla limpiada")

            insertados = 0
            omitidos   = 0

            for reg in registros:
                # Filtrar solo campos que existen en la BD
                reg_filtrado = {k: v for k, v in reg.items() if k in cols_bd}
                if not reg_filtrado:
                    omitidos += 1
                    continue

                # Construir INSERT
                campos_sql = ", ".join(f"`{k}`" for k in reg_filtrado)
                valores_sql = ", ".join(f":{k}" for k in reg_filtrado)
                sql = text(f"INSERT INTO `{tabla}` ({campos_sql}) VALUES ({valores_sql})")

                try:
                    conn.execute(sql, reg_filtrado)
                    insertados += 1
                except Exception as e:
                    omitidos += 1
                    if "Duplicate" not in str(e):
                        print(f"    ⚠️  fila omitida: {e}")

            conn.commit()

        print(f"  ✅ {alias} → '{tabla_n}': {insertados} insertados, {omitidos} omitidos")
        return {"insertados": insertados, "omitidos": omitidos, "tabla": tabla_n}


# ── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="KraftDo Importer — Excel → MySQL")
    parser.add_argument("empresa", help="Nombre empresa (ej: kraftdo)")
    parser.add_argument("--solo", help="Hojas a importar separadas por coma (ej: pedidos,clientes)")
    parser.add_argument("--preview", action="store_true", help="Mostrar sin insertar")
    parser.add_argument("--limpiar", action="store_true", help="Borrar tabla antes de insertar")
    parser.add_argument("--db", help="URL de BD (ej: mysql+pymysql://user:pass@host/db)")
    parser.add_argument("--dry-run", action="store_true", help="Validar datos sin insertar nada — genera reporte de errores")
    args = parser.parse_args()

    solo = [s.strip() for s in args.solo.split(",")] if args.solo else None

    print(f"\n{'='*60}")
    print(f"  KraftDo Importer — {args.empresa}")
    print(f"  Modo: {'PREVIEW' if args.preview else 'IMPORTAR'}")
    if args.limpiar and not args.preview:
        print(f"  ⚠️  LIMPIAR activado — se borrarán los datos existentes")
    print(f"{'='*60}\n")

    imp = Importer(args.empresa, args.db)

    if getattr(args, 'dry_run', False):
        print("  🔍 Modo DRY-RUN — validando datos sin insertar\n")
        resultados = imp.dry_run(solo)
    else:
        resultados = imp.importar_todo(solo, args.limpiar, args.preview)

    total_insertados = sum(r.get("insertados", 0) for r in resultados.values())
    total_omitidos   = sum(r.get("omitidos", 0) for r in resultados.values())

    print(f"\n{'─'*60}")
    print(f"  Total: {total_insertados} registros insertados, {total_omitidos} omitidos")
    print(f"{'─'*60}\n")


if __name__ == "__main__":
    main()
