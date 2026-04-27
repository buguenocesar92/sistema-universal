# pyright: basic
# type: ignore
"""
KraftDo — generator.py
Lee empresas/{empresa}.json y genera:
  - database/migrations/*.php       (tablas en MySQL)
  - app/Models/*.php                 (modelos Eloquent)
  - app/Filament/Resources/*.php     (CRUD en Filament)
  - routes/api.php                   (API REST lista)
  - install.sh                       (script de instalación completa)

USO:
    python3 generator.py kraftdo           → genera todo
    python3 generator.py kraftdo --solo migraciones
    python3 generator.py kraftdo --preview → muestra sin escribir
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime
from pathlib import Path

# Módulos propios
try:
    from relations import detectar_relaciones, relaciones_por_tabla, gen_foreign_keys_migration, gen_eloquent_relationships, gen_hasmany_relationships, gen_filament_select
    from formula_parser import analizar_excel_formulas, gen_accessors_php
    from consolidator import Consolidator
    from normalizer import analizar_excel_completo as _analizar_patrones
    RELACIONES_OK = True
except ImportError:
    RELACIONES_OK = False
    def _analizar_patrones(path): return {}

def _es_consolidado(cfg_hoja: dict) -> bool:
    return bool(cfg_hoja.get("consolidado"))

def _valores_tipo(cfg_hoja: dict) -> list:
    return cfg_hoja.get("valores_tipo") or [
        _slug(f) for f in cfg_hoja.get("fuentes", [])
    ]

def _slug(s: str) -> str:
    """Convierte a slug ASCII válido para SQL: elimina tildes, emojis y espacios."""
    import re, unicodedata
    # Normalizar unicode: descompone caracteres acentuados (á → a + ́)
    s = unicodedata.normalize("NFKD", str(s))
    # Eliminar caracteres no ASCII
    s = s.encode("ascii", "ignore").decode("ascii")
    # Reemplazar caracteres no alfanuméricos por guión bajo
    s = re.sub(r"[^a-z0-9_]", "_", s.lower().strip())
    # Eliminar guiones bajos duplicados y del inicio/fin
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "hoja"

# ── Tipos de columna: inferencia por nombre ─────────────────────────────────
# Nota: el orden importa. Las reglas más específicas van primero.
REGLAS_TIPO = [
    # Fechas
    (r"^fecha|^f_|_fecha$|_date$|_at$", "timestamp", "nullable"),
    (r"^updated_at$|^created_at$",       "timestamp", "nullable"),
    # Porcentajes y márgenes (deben ir ANTES que la regla monetaria, que es más amplia).
    # Solo decimal(5,4) cuando es realmente fracción 0..1. NO incluye 'descuento'
    # (descuento_faltas es monto), ni '^iva$' (iva en ventas es monto).
    (r"^margen$|^margen_pct$|_pct$|porcentaje", "decimal:5,4", "default:0"),
    # Montos y precios — incluye iva, descuento_faltas, iva_servicio
    (r"precio|monto|costo|total|saldo|anticipo|ganancia|ahorro|^iva|descuento|servicio", "decimal:15,2", "default:0"),
    # Cantidades enteras
    (r"^cantidad$|^stock$|^dias|^horas$|^gramos$|_count$|_qty$", "integer", "default:0"),
    # Estado (select)
    (r"^estado$|^status$|^tipo$|^categoria$|^canal$", "string", "nullable"),
    # Booleanos
    (r"^activo$|^active$|^enabled$|^is_", "boolean", "default:true"),
    # Email
    (r"correo|email", "string", "nullable"),
    # Teléfono / WhatsApp
    (r"telefono|whatsapp|phone|fono", "string:20", "nullable"),
    # URLs
    (r"^web$|^url$|^link$|_url$", "string", "nullable"),
    # Identificadores de referencia
    (r"^sku$|^numero$|^codigo$|^code$|^ref", "string:50", "nullable"),
    # Texto largo
    (r"obs|descripcion|notas|detalle|comment", "text", "nullable"),
    # Default: string
]

def inferir_tipo(nombre: str) -> tuple[str, str]:
    """Retorna (tipo_laravel, modificador) según el nombre del campo."""
    nombre_lower = nombre.lower()
    for patron, tipo, mod in REGLAS_TIPO:
        if re.search(patron, nombre_lower):
            return tipo, mod
    return "string", "nullable"


# ── Reglas de cálculo automático ────────────────────────────────────────────
# Cada regla define un campo destino, sus dependencias y la fórmula PHP.
# El observer aplica las reglas en orden (las posteriores pueden depender
# de campos ya calculados por reglas anteriores).
# Se aplica una regla solo si TODOS los campos (destino + deps) existen
# en la hoja, así nunca se rompe una tabla que no tenga el patrón.
REGLAS_CALCULO = [
    # Producto: costo total = insumo + mano de obra
    {"campo": "costo_total", "deps": ["costo_insumo", "hora_trabajo"],
     "formula": "(float)($model->costo_insumo ?? 0) + (float)($model->hora_trabajo ?? 0)",
     "descripcion": "Suma de costo de insumo + hora de trabajo"},

    # Producto: precio unitario = costo / (1 - margen 40%)
    {"campo": "precio_unit", "deps": ["costo_total"],
     "formula": "(float)($model->costo_total ?? 0) > 0 ? (int) round((float)$model->costo_total / 0.60) : 0",
     "descripcion": "Precio unitario calculado con margen 40%"},

    # Producto: precio mayorista = costo / (1 - margen 37%)
    {"campo": "precio_mayor", "deps": ["costo_total"],
     "formula": "(float)($model->costo_total ?? 0) > 0 ? (int) round((float)$model->costo_total / 0.63) : 0",
     "descripcion": "Precio mayorista calculado con margen 37%"},

    # Liquidación: valor del día = sueldo / días laborales
    {"campo": "valor_dia", "deps": ["sueldo_base", "dias_laborales"],
     "formula": "(float)($model->dias_laborales ?? 0) > 0 ? (int) round((float)$model->sueldo_base / (float)$model->dias_laborales) : 0",
     "descripcion": "Valor diario del trabajador"},

    # Liquidación: descuento por faltas
    {"campo": "descuento_faltas", "deps": ["valor_dia", "faltas"],
     "formula": "(int) round((float)($model->valor_dia ?? 0) * (float)($model->faltas ?? 0))",
     "descripcion": "Descuento por días faltados"},

    # Liquidación: monto a pagar
    {"campo": "a_pagar", "deps": ["sueldo_base", "descuento_faltas"],
     "formula": "(int) round((float)($model->sueldo_base ?? 0) - (float)($model->descuento_faltas ?? 0))",
     "descripcion": "Sueldo base menos descuentos"},

    # Liquidación: saldo pendiente = a pagar - quincena ya pagada
    {"campo": "saldo", "deps": ["a_pagar", "quincena_pagada"],
     "formula": "(int) round((float)($model->a_pagar ?? 0) - (float)($model->quincena_pagada ?? 0))",
     "descripcion": "Saldo pendiente de pago"},

    # Ventas: IVA calculado del neto
    {"campo": "iva", "deps": ["neto"],
     "formula": "(int) round((float)($model->neto ?? 0) * 0.19)",
     "descripcion": "IVA 19% calculado sobre el neto"},

    # Importaciones: IVA del servicio
    {"campo": "iva_servicio", "deps": ["total_neto"],
     "formula": "(int) round((float)($model->total_neto ?? 0) * 0.19)",
     "descripcion": "IVA 19% sobre el total neto"},

    # Promociones / ventas: total con IVA
    {"campo": "total", "deps": ["neto"],
     "formula": "(int) round((float)($model->neto ?? 0) * 1.19)",
     "descripcion": "Total con IVA incluido"},

    # Importaciones: total neto = costos componentes
    {"campo": "total_neto", "deps": ["costo_china", "embarcadero", "agente_aduana"],
     "formula": "(int) round((float)($model->costo_china ?? 0) + (float)($model->embarcadero ?? 0) + (float)($model->agente_aduana ?? 0))",
     "descripcion": "Suma de costos de importación"},

    # Stock: stock disponible = importaciones - ventas - promociones
    {"campo": "stock_disponible", "deps": ["importacion", "ventas"],
     "formula": "(int) ((int)($model->importacion ?? 0) - (int)($model->ventas ?? 0) - (int)($model->promociones ?? 0))",
     "descripcion": "Stock disponible = importado - vendido - promociones"},

    # Obras: total gastado = materiales + mano de obra + otros
    {"campo": "total_gastado", "deps": ["materiales", "mano_obra"],
     "formula": "(int) round((float)($model->materiales ?? 0) + (float)($model->mano_obra ?? 0) + (float)($model->otros ?? 0))",
     "descripcion": "Suma de gastos de la obra"},

    # Obras: resultado = cobrado - total gastado
    {"campo": "resultado", "deps": ["cobrado", "total_gastado"],
     "formula": "(int) round((float)($model->cobrado ?? 0) - (float)($model->total_gastado ?? 0))",
     "descripcion": "Resultado neto de la obra"},

    # Obras: margen porcentual
    {"campo": "margen", "deps": ["cobrado", "resultado"],
     "formula": "(float)($model->cobrado ?? 0) > 0 ? round((float)($model->resultado ?? 0) / (float)$model->cobrado, 4) : 0",
     "descripcion": "Margen como fracción del cobrado"},

    # Ventas: neto con descuento (si no hay descuento explícito, copia neto)
    {"campo": "neto_dsto", "deps": ["neto"],
     "formula": "(int) round((float)($model->neto ?? 0))",
     "descripcion": "Neto con descuento (default = neto)"},
]


def _calculos_aplicables(cols: dict) -> list[dict]:
    """Devuelve las reglas de cálculo cuyo campo destino + deps están en cols."""
    nombres = set(cols.keys())
    aplicables = []
    for regla in REGLAS_CALCULO:
        if regla["campo"] not in nombres:
            continue
        if not all(d in nombres for d in regla["deps"]):
            continue
        aplicables.append(regla)
    return aplicables


# Conjuntos para clasificar campos en widgets/formularios
CAMPOS_MONEDA = {
    "monto", "total", "precio_unit", "precio_mayor", "neto", "neto_dsto",
    "cobrado", "sueldo_base", "a_pagar", "saldo", "costo_total", "costo_insumo",
    "total_neto", "total_gastado", "ganancia", "anticipo", "ahorro", "iva",
    "iva_servicio", "resultado", "materiales", "mano_obra", "costo_gym",
    "costo_nogales", "gastos_generales", "monto_neto", "costo_china",
    "embarcadero", "agente_aduana", "costo_stand", "descuento_faltas",
    "valor_dia", "quincena_pagada", "precio",
}

# Campos que típicamente NO son enums aunque sean strings cortos
NO_ENUM = {
    "nombre", "descripcion", "obs", "observaciones", "detalle", "comentario",
    "comment", "trabajador", "cliente", "producto", "sku",
    "codigo", "factura", "rut", "empresa", "evento", "lugar", "vehiculo",
    "concepto", "responsable", "contacto", "obra", "item", "variante",
    "ciudad", "whatsapp", "correo", "email", "telefono", "fecha", "url",
    "web", "sitio_web", "link", "ref_pedido", "proveedor", "modelo",
    "aplicaciones", "problema", "f_entrega",
}


def _detectar_enums_excel(excel_path: str, cfg: dict) -> dict:
    """Lee el Excel y detecta columnas string con 2..7 valores únicos como enum.

    Devuelve {alias: {campo: [val1, val2, ...]}}.
    Saltea identificadores y campos en NO_ENUM (nombres, textos abiertos, etc).
    """
    if not os.path.exists(excel_path):
        return {}
    try:
        import openpyxl
        from openpyxl.utils import column_index_from_string
    except ImportError:
        return {}
    try:
        wb = openpyxl.load_workbook(excel_path, data_only=True, read_only=True)
    except Exception:
        return {}

    resultado = {}
    for alias, hoja_cfg in cfg.get("hojas", {}).items():
        if hoja_cfg.get("tipo") not in ("registros", "catalogo"):
            continue
        nombre_hoja = hoja_cfg.get("nombre")
        if nombre_hoja not in wb.sheetnames:
            continue
        ws = wb[nombre_hoja]
        fila_inicio = hoja_cfg.get("fila_datos", 2)
        ident       = hoja_cfg.get("identificador")
        enums_hoja  = {}

        for campo, letra in hoja_cfg.get("columnas", {}).items():
            if campo == ident or campo in NO_ENUM or campo in CAMPOS_MONEDA:
                continue
            tipo, _ = inferir_tipo(campo)
            # Sólo strings (los enums numéricos son raros)
            if tipo != "string" and not tipo.startswith("string"):
                continue

            try:
                col_idx = column_index_from_string(letra)
            except Exception:
                continue

            valores = set()
            descartar = False
            try:
                fin = min(ws.max_row or fila_inicio, fila_inicio + 300)
                for row in ws.iter_rows(min_row=fila_inicio, max_row=fin,
                                         min_col=col_idx, max_col=col_idx,
                                         values_only=True):
                    v = row[0]
                    if v is None:
                        continue
                    s = str(v).strip()
                    if not s:
                        continue
                    if len(s) > 60:
                        descartar = True
                        break
                    valores.add(s)
                    if len(valores) > 8:
                        descartar = True
                        break
            except Exception:
                descartar = True
            if descartar:
                continue
            if 2 <= len(valores) <= 7:
                enums_hoja[campo] = sorted(valores)

        if enums_hoja:
            resultado[alias] = enums_hoja
    return resultado


def nombre_tabla(alias: str) -> str:
    """Convierte alias JSON a nombre de tabla Snake_case plural."""
    return alias.lower().replace("-", "_")


def nombre_modelo(alias: str) -> str:
    """Convierte alias JSON a nombre de clase PascalCase singular."""
    palabras = re.split(r'[_\-\s]+', alias)
    ult = palabras[-1].lower()
    if ult.endswith("ores"):   singular = ult[:-2]
    elif ult.endswith("ales"): singular = ult[:-2]
    elif ult.endswith("iones"): singular = ult[:-2]
    elif ult.endswith("entes"): singular = ult[:-1]
    elif ult.endswith("tes"):  singular = ult[:-1]
    elif ult.endswith("enes"): singular = ult[:-2]
    elif ult.endswith("res"):  singular = ult[:-2]
    elif ult.endswith("nes"):  singular = ult[:-1]
    elif ult.endswith("as"):   singular = ult[:-1]
    elif ult.endswith("os"):   singular = ult[:-1]
    elif ult.endswith("es") and len(ult) > 4: singular = ult[:-1]
    elif ult.endswith("s"):    singular = ult[:-1]
    else: singular = ult
    return "".join(w.capitalize() for w in palabras[:-1]) + singular.capitalize()


def nombre_migration(alias: str, idx: int) -> str:
    ts = f"2026_01_01_{idx:06d}"  # fecha fija para evitar migraciones duplicadas
    return f"{ts}_create_{nombre_tabla(alias)}_table"


# ═══════════════════════════════════════════════════════════════════════════════
# GENERADORES
# ═══════════════════════════════════════════════════════════════════════════════

def gen_migracion(alias: str, cfg_hoja: dict, idx: int) -> str:
    # ── Hoja consolidada ──────────────────────────────────────────────────
    if _es_consolidado(cfg_hoja) and RELACIONES_OK:
        try:
            fuentes    = cfg_hoja.get("fuentes", [])
            cols_raw   = {k: v for k, v in cfg_hoja.get("columnas", {}).items()
                          if k not in ("tipo",) and v != "[CALCULADO]"}
            tipos      = _valores_tipo(cfg_hoja)
            tabla_n    = nombre_tabla(alias)
            tiene_meta = bool(cfg_hoja.get("cols_especificas"))
            meta_col   = "            $table->json('metadata')->nullable();" if tiene_meta else ""
            tipos_enum = "', '".join(tipos)

            lineas = []
            for campo, letra in cols_raw.items():
                t, mod = inferir_tipo(campo)
                if t.startswith("decimal"):
                    p, s = t.split(":")[1].split(",")
                    lineas.append(
                        "            $table->decimal('" + campo + "', " + p + ", " + s + ")->nullable();")
                elif t == "integer":
                    lineas.append("            $table->integer('" + campo + "')->nullable();")
                elif t == "text":
                    lineas.append("            $table->text('" + campo + "')->nullable();")
                elif t == "timestamp":
                    lineas.append("            $table->date('" + campo + "')->nullable();")
                else:
                    lineas.append("            $table->string('" + campo + "', 255)->nullable();")

            cols_str = "\n".join(lineas)

            return (
                "<?php\n\n"
                "use Illuminate\\Database\\Migrations\\Migration;\n"
                "use Illuminate\\Database\\Schema\\Blueprint;\n"
                "use Illuminate\\Support\\Facades\\Schema;\n\n"
                "// Tabla consolidada — fuentes: " + ", ".join(fuentes) + "\n\n"
                "return new class extends Migration\n"
                "{\n"
                "    public function up(): void\n"
                "    {\n"
                "        Schema::create('" + tabla_n + "', function (Blueprint $table) {\n"
                "            $table->id();\n"
                "            $table->enum('tipo', ['" + tipos_enum + "'])->index();\n"
                + cols_str + "\n"
                + ("\n" + meta_col if meta_col else "") + "\n"
                "            $table->timestamps();\n"
                "        });\n"
                "    }\n\n"
                "    public function down(): void\n"
                "    {\n"
                "        Schema::dropIfExists('" + tabla_n + "');\n"
                "    }\n"
                "};\n"
            )
        except Exception:
            pass  # fallback a generación estándar
    # ─────────────────────────────────────────────────────────────────────


    tabla  = nombre_tabla(alias)
    clase  = "Create" + "".join(w.capitalize() for w in alias.split("_")) + "Table"
    cols   = cfg_hoja.get("columnas", {})
    estados = cfg_hoja.get("logica", {}).get("estados", [])

    lineas_col = []
    for campo, _ in cols.items():
        if campo in ("numero", "id"):
            continue  # lo maneja $table->id() o el campo numero como PK
        tipo, mod = inferir_tipo(campo)

        # Construir línea de columna
        if tipo.startswith("decimal"):
            partes = tipo.split(":")
            precision = partes[1] if len(partes) > 1 else "10,2"
            p, s = precision.split(",")
            linea = f"            $table->decimal('{campo}', {p}, {s})"
        elif tipo.startswith("string:"):
            largo = tipo.split(":")[1]
            linea = f"            $table->string('{campo}', {largo})"
        elif tipo == "text":
            linea = f"            $table->text('{campo}')"
        elif tipo == "integer":
            linea = f"            $table->integer('{campo}')"
        elif tipo == "boolean":
            linea = f"            $table->boolean('{campo}')"
        elif tipo == "timestamp":
            linea = f"            $table->timestamp('{campo}')"
        else:
            linea = f"            $table->string('{campo}')"

        # Modificador
        if "nullable" in mod:
            linea += "->nullable()"
        if "default:" in mod:
            val = mod.split("default:")[1]
            if val in ("true", "false"):
                linea += f"->default({val})"
            else:
                linea += f"->default({val})"

        lineas_col.append(linea + ";")

    cols_str = "\n".join(lineas_col)

    # Índices automáticos — detecta fecha, estado, sku, id_, email, etc.
    indices_campos = _auto_indices(cols)
    indices = ""
    for campo in indices_campos:
        if campo not in ("numero", "id"):  # no indexar PKs
            indices += f"\n            $table->index('{campo}');"

    return f"""<?php

use Illuminate\\Database\\Migrations\\Migration;
use Illuminate\\Database\\Schema\\Blueprint;
use Illuminate\\Support\\Facades\\Schema;

return new class extends Migration
{{
    public function up(): void
    {{
        Schema::create('{tabla}', function (Blueprint $table) {{
            $table->id();
{cols_str}{indices}
            $table->timestamps();
        }});
    }}

    public function down(): void
    {{
        Schema::dropIfExists('{tabla}');
    }}
}};
"""


def gen_modelo(alias: str, cfg_hoja: dict, empresa_cfg: dict, relaciones=None, formulas=None) -> str:
    modelo = nombre_modelo(alias)
    tabla  = nombre_tabla(alias)
    cols   = cfg_hoja.get("columnas", {})

    # fillable: todos los campos excepto id/timestamps
    fillable = [c for c in cols.keys() if c not in ("id",)]
    fillable_str = ",\n        ".join(f"'{c}'" for c in fillable)

    # casts
    casts = []
    for campo in cols.keys():
        tipo, _ = inferir_tipo(campo)
        if tipo.startswith("decimal"):
            casts.append(f"'{campo}' => 'decimal:2'")
        elif tipo == "integer":
            casts.append(f"'{campo}' => 'integer'")
        elif tipo == "boolean":
            casts.append(f"'{campo}' => 'boolean'")
        elif tipo == "timestamp":
            casts.append(f"'{campo}' => 'datetime'")
    casts_str = ",\n        ".join(casts) if casts else ""
    casts_block = "\n        " + casts_str + "\n    " if casts_str else ""

    # scope de activos si tiene campo estado
    scope = ""
    if "estado" in cols:
        estados_activos = cfg_hoja.get("filtro_activos", {}).get("valores", ["Activo"])
        estados_str = ", ".join(f"'{e}'" for e in estados_activos)
        scope = f"""
    public function scopeActivos($query)
    {{
        return $query->whereIn('estado', [{estados_str}]);
    }}"""

    # Relaciones si están disponibles (belongsTo + hasMany)
    rels_str = ""
    if RELACIONES_OK and hasattr(gen_modelo, '_relaciones'):
        rels = gen_modelo._relaciones
        belongs = gen_eloquent_relationships(rels, tabla)
        hasmany = gen_hasmany_relationships(rels, tabla, {})
        # Deduplicar métodos por nombre de función
        todos_metodos = []
        nombres_vistos = set()
        for bloque in [belongs, hasmany]:
            if not bloque:
                continue
            for metodo in bloque.split("\n\n"):
                metodo = metodo.strip()
                if not metodo:
                    continue
                # Extraer nombre del método
                import re as _re2
                m = _re2.search(r"public function (\w+)\(", metodo)
                nombre = m.group(1) if m else metodo[:30]
                if nombre not in nombres_vistos:
                    nombres_vistos.add(nombre)
                    todos_metodos.append(metodo)
        if todos_metodos:
            rels_str = "\n\n" + "\n\n".join(todos_metodos)

    # Scopes por tipo si la hoja es consolidada
    if _es_consolidado(cfg_hoja):
        tipos = _valores_tipo(cfg_hoja)
        scopes = ""
        for tipo in tipos:
            nombre_scope = "".join(w.capitalize() for w in tipo.split("_"))
            scopes += (
                "\n\n"
                "    public function scope" + nombre_scope + "($query)\n"
                "    {\n"
                "        return $query->where('tipo', '" + tipo + "');\n"
                "    }"
            )
        if scopes:
            rels_str += scopes

    # Accessors de fórmulas si están disponibles
    accessors_str = ""
    if RELACIONES_OK and hasattr(gen_modelo, '_formulas') and alias in gen_modelo._formulas:
        for conv in gen_modelo._formulas[alias]:
            if conv.get("php"):
                accessors_str += "\n\n" + gen_accessors_php(conv["campo"], conv)

    # ¿Tiene observer? Cuando hay reglas de cálculo aplicables
    # o cuando la hoja define formato_id para auto-numeración.
    formato_id = cfg_hoja.get("formato_id")
    ident      = cfg_hoja.get("identificador")
    tiene_observer = bool(_calculos_aplicables(cols)) or bool(
        formato_id and ident and ident in cols
    )
    observer_use   = ""
    observer_attr  = ""
    if tiene_observer:
        observer_use  = (
            "use Illuminate\\Database\\Eloquent\\Attributes\\ObservedBy;\n"
            f"use App\\Observers\\{modelo}Observer;\n"
        )
        observer_attr = f"#[ObservedBy([{modelo}Observer::class])]\n"

    return f"""<?php

namespace App\\Models;

use Illuminate\\Database\\Eloquent\\Model;
use Illuminate\\Database\\Eloquent\\Factories\\HasFactory;
{observer_use}
{observer_attr}class {modelo} extends Model
{{
    use HasFactory;

    protected $table = '{tabla}';

    protected $fillable = [
        {fillable_str},
    ];

    protected $casts = [{casts_block}];{scope}{rels_str}{accessors_str}
}}
"""


def gen_observer(alias: str, cfg_hoja: dict) -> str | None:
    """Genera un Observer PHP que recalcula campos al guardar.

    Devuelve el contenido PHP, o None si la hoja no tiene ni reglas
    aplicables ni formato_id.
    Usa $model SIN backslash en typehint (regla CLAUDE.md).

    Si la hoja define `formato_id` (ej "KDO-{:03d}"), el observer
    asigna el siguiente identificador disponible al crear (creating).
    """
    cols       = cfg_hoja.get("columnas", {})
    aplicables = _calculos_aplicables(cols)
    formato_id = cfg_hoja.get("formato_id")
    ident      = cfg_hoja.get("identificador")
    auto_id    = bool(formato_id and ident and ident in cols)

    if not aplicables and not auto_id:
        return None

    modelo = nombre_modelo(alias)

    bloques = []
    for regla in aplicables:
        comentario = regla.get("descripcion", "")
        bloques.append(
            f"        // {comentario}\n"
            f"        $model->{regla['campo']} = {regla['formula']};"
        )
    body = "\n\n".join(bloques) if bloques else "        // (sin reglas de cálculo)"

    # Bloque de auto-numeración: en creating, si el identificador está vacío,
    # buscar el último ID con el patrón y emitir el siguiente.
    auto_id_block = ""
    if auto_id:
        # Convertir patrón Python "{:03d}" a regex y formato sprintf-equivalente
        # Soportamos formatos tipo "PREFIJO-{:0Nd}".
        m = re.match(r"^(.*?)\{:0?(\d+)d\}(.*)$", formato_id)
        if m:
            prefijo, ancho, sufijo = m.group(1), int(m.group(2)), m.group(3)
            php_pattern = "/^" + re.escape(prefijo) + r"(\d+)" + re.escape(sufijo) + "$/"
            php_format  = prefijo + "%0" + str(ancho) + "d" + sufijo
            auto_id_block = (
                "\n"
                f"    public function creatingAutoId({modelo} $model): void\n"
                "    {\n"
                f"        if (!empty($model->{ident})) {{\n"
                "            return;\n"
                "        }\n"
                f"        $ultimo = {modelo}::query()\n"
                f"            ->where('{ident}', 'like', '" + prefijo.replace("'", "\\'") + "%')\n"
                f"            ->pluck('{ident}')\n"
                f"            ->map(fn ($v) => preg_match('" + php_pattern + "', (string) $v, $m) ? (int) $m[1] : 0)\n"
                "            ->max() ?? 0;\n"
                f"        $model->{ident} = sprintf('" + php_format + "', $ultimo + 1);\n"
                "    }\n"
            )

    creating_calls = "        $this->recalcular($model);"
    if auto_id_block:
        creating_calls = "        $this->creatingAutoId($model);\n" + creating_calls

    return (
        "<?php\n\n"
        "namespace App\\Observers;\n\n"
        f"use App\\Models\\{modelo};\n\n"
        "/**\n"
        f" * Observer auto-generado para {modelo}.\n"
        " * Recalcula campos derivados antes de guardar.\n"
        " */\n"
        f"class {modelo}Observer\n"
        "{\n"
        f"    public function creating({modelo} $model): void\n"
        "    {\n"
        + creating_calls + "\n"
        "    }\n\n"
        f"    public function updating({modelo} $model): void\n"
        "    {\n"
        "        $this->recalcular($model);\n"
        "    }\n\n"
        f"    protected function recalcular({modelo} $model): void\n"
        "    {\n"
        + body + "\n"
        "    }\n"
        + auto_id_block
        + "}\n"
    )


def gen_filament_resource(alias: str, cfg_hoja: dict, empresa_cfg: dict,
                           relaciones=None, enums=None) -> str:
    """Genera un Filament Resource completo con ExcelExport incluido.

    enums: {campo: [val1, val2, ...]} para esta hoja (si se detectaron en Excel).
    relaciones: lista global de relaciones detectadas por relations.detectar_relaciones.
    """
    modelo   = nombre_modelo(alias)
    resource = modelo + "Resource"
    cols     = list(cfg_hoja.get("columnas", {}).keys())
    tipo     = cfg_hoja.get("tipo", "registros")
    estados  = cfg_hoja.get("logica", {}).get("estados", [])
    enums    = enums or {}
    tabla_n  = nombre_tabla(alias)
    rels_hoja = [r for r in (relaciones or []) if r["tabla_origen"] == tabla_n]
    rels_por_campo = {r["campo_origen"]: r for r in rels_hoja}

    ns = "\\App\\Filament\\Resources\\"
    ns_models = "\\App\\Models\\"

    # Campos del formulario
    # Campos que nunca van en el formulario (PKs y los calculados por observer)
    cols_dict = cfg_hoja.get("columnas", {})
    calc_fields = {r["campo"] for r in _calculos_aplicables(cols_dict)}
    CAMPOS_AUTO = {"id", "n_pedido", "created_at", "updated_at"} | calc_fields

    form_fields = []
    for campo in cols[:10]:  # max 10 campos visibles
        if campo in CAMPOS_AUTO:
            continue
        t, mod = inferir_tipo(campo)
        label  = campo.replace("_", " ").capitalize()
        req    = ""  # Filament 4: nullable/required se maneja en validación

        # Prioridad 1: estado con valores definidos en el JSON
        if campo == "estado" and estados:
            opts = "\n".join(
                "                    '" + _slug(e) + "' => '" + e + "',"
                for e in estados
            )
            form_fields.append(
                "            Forms\\Components\\Select::make('" + campo + "')\n"
                "                ->label('" + label + "')\n"
                "                ->options([\n"
                + opts + "\n"
                "                ])" + req + ","
            )
        # Prioridad 2: relación detectada → Select con opciones del modelo
        elif campo in rels_por_campo:
            rel = rels_por_campo[campo]
            modelo_dest = rel["modelo_destino"]
            campo_dest  = rel["campo_destino"]
            form_fields.append(
                "            Forms\\Components\\Select::make('" + campo + "')\n"
                "                ->label('" + label + "')\n"
                "                ->options(fn() => \\App\\Models\\" + modelo_dest
                + "::query()->pluck('" + campo_dest + "', '" + campo_dest + "')->toArray())\n"
                "                ->searchable()\n"
                "                ->preload()"
                + req + ","
            )
        # Prioridad 3: enum auto-detectado en Excel
        elif campo in enums:
            opts_lines = "\n".join(
                "                    '" + v.replace("'", "\\'") + "' => '" + v.replace("'", "\\'") + "',"
                for v in enums[campo]
            )
            form_fields.append(
                "            Forms\\Components\\Select::make('" + campo + "')\n"
                "                ->label('" + label + "')\n"
                "                ->options([\n"
                + opts_lines + "\n"
                "                ])" + req + ","
            )
        # Prioridad alta: campo monetario → numeric con prefix $
        elif campo in CAMPOS_MONEDA:
            form_fields.append(
                "            Forms\\Components\\TextInput::make('" + campo + "')\n"
                "                ->label('" + label + "')\n"
                "                ->numeric()\n"
                "                ->prefix('$')" + req + ","
            )
        elif t == "text":
            form_fields.append(
                "            Forms\\Components\\Textarea::make('" + campo + "')\n"
                "                ->label('" + label + "')" + req + ","
            )
        elif t.startswith("decimal") or t == "integer":
            form_fields.append(
                "            Forms\\Components\\TextInput::make('" + campo + "')\n"
                "                ->label('" + label + "')\n"
                "                ->numeric()" + req + ","
            )
        elif t == "timestamp":
            form_fields.append(
                "            Forms\\Components\\DatePicker::make('" + campo + "')\n"
                "                ->label('" + label + "')\n"
                "                ->displayFormat('d/m/Y')\n"
                "                ->native(false)" + req + ","
            )
        else:
            form_fields.append(
                "            Forms\\Components\\TextInput::make('" + campo + "')\n"
                "                ->label('" + label + "')" + req + ","
            )

    # Placeholder readonly para los campos calculados por el observer
    placeholders = []
    for campo in calc_fields:
        if campo not in cols_dict:
            continue
        label = campo.replace("_", " ").capitalize()
        if campo in CAMPOS_MONEDA:
            content_expr = (
                "$record ? '$' . number_format((float) $record->" + campo
                + ", 0, ',', '.') : '— se calcula al guardar —'"
            )
        else:
            content_expr = "$record?->" + campo + " ?? '— se calcula al guardar —'"
        placeholders.append(
            "            Forms\\Components\\Placeholder::make('" + campo + "')\n"
            "                ->label('" + label + " (auto)')\n"
            "                ->content(fn ($record) => " + content_expr + "),"
        )
    placeholders_str = ("\n" + "\n".join(placeholders)) if placeholders else ""

    form_str  = "\n".join(form_fields)

    # Columnas de la tabla
    table_cols = []
    for campo in cols[:8]:
        t, _ = inferir_tipo(campo)
        label_c = campo.replace('_', ' ').capitalize()
        # Monetario → money() con formato CLP
        if campo in CAMPOS_MONEDA:
            table_cols.append(
                "                Tables\\Columns\\TextColumn::make('" + campo + "')\n"
                "                    ->label('" + label_c + "')\n"
                "                    ->money('clp', divideBy: 1, locale: 'es_CL')\n"
                "                    ->sortable(),"
            )
        # Fecha → format d/m/Y
        elif t == "timestamp":
            table_cols.append(
                "                Tables\\Columns\\TextColumn::make('" + campo + "')\n"
                "                    ->label('" + label_c + "')\n"
                "                    ->date('d/m/Y')\n"
                "                    ->sortable(),"
            )
        # Numérico no monetario
        elif t.startswith("decimal") or t == "integer":
            table_cols.append(
                "                Tables\\Columns\\TextColumn::make('" + campo + "')\n"
                "                    ->label('" + label_c + "')\n"
                "                    ->numeric(thousandsSeparator: '.')\n"
                "                    ->sortable()->searchable(),"
            )
        # Badge para enums detectados o estado
        elif campo in enums or (campo == "estado" and estados):
            table_cols.append(
                "                Tables\\Columns\\TextColumn::make('" + campo + "')\n"
                "                    ->label('" + label_c + "')\n"
                "                    ->badge()\n"
                "                    ->sortable()->searchable(),"
            )
        else:
            table_cols.append(
                "                Tables\\Columns\\TextColumn::make('" + campo + "')\n"
                "                    ->label('" + label_c + "')\n"
                "                    ->sortable()->searchable(),"
            )

    table_str = "\n".join(table_cols)

    # Filtros: SelectFilter por estado/enums + DateRangeFilter por fechas
    filters_lines = []
    if "estado" in cols:
        filters_lines.append(
            "                Tables\\Filters\\SelectFilter::make('estado')\n"
            "                    ->options(fn() => " + ns_models + modelo + "::distinct()->pluck('estado', 'estado')->toArray()),"
        )
    for campo, valores in enums.items():
        if campo == "estado":
            continue
        opts = ", ".join("'" + v.replace("'", "\\'") + "' => '" + v.replace("'", "\\'") + "'" for v in valores)
        filters_lines.append(
            "                Tables\\Filters\\SelectFilter::make('" + campo + "')\n"
            "                    ->label('" + campo.replace('_', ' ').capitalize() + "')\n"
            "                    ->options([" + opts + "]),"
        )
    # DateRangeFilter (un Filter con dos DatePicker)
    for campo in cols:
        t, _ = inferir_tipo(campo)
        if t != "timestamp":
            continue
        filters_lines.append(
            "                Tables\\Filters\\Filter::make('" + campo + "_range')\n"
            "                    ->label('" + campo.replace('_', ' ').capitalize() + " (rango)')\n"
            "                    ->schema([\n"
            "                        Forms\\Components\\DatePicker::make('desde')->native(false),\n"
            "                        Forms\\Components\\DatePicker::make('hasta')->native(false),\n"
            "                    ])\n"
            "                    ->query(fn ($query, array $data) => $query\n"
            "                        ->when($data['desde'] ?? null, fn ($q, $d) => $q->whereDate('" + campo + "', '>=', $d))\n"
            "                        ->when($data['hasta'] ?? null, fn ($q, $d) => $q->whereDate('" + campo + "', '<=', $d))\n"
            "                    ),"
        )
    filters_str = ("\n" + "\n".join(filters_lines)) if filters_lines else ""

    # Global search: primeros 3 campos string no técnicos
    search_attrs = []
    for campo in cols:
        if len(search_attrs) >= 3:
            break
        if campo in ("id", "n_pedido"):
            continue
        if campo in CAMPOS_MONEDA or campo in calc_fields:
            continue
        t, _ = inferir_tipo(campo)
        if t == "string" or t.startswith("string"):
            search_attrs.append(campo)
    global_search = ""
    if search_attrs:
        attrs = ", ".join("'" + c + "'" for c in search_attrs)
        global_search = (
            "    public static function getGloballySearchableAttributes(): array\n"
            "    {\n"
            f"        return [{attrs}];\n"
            "    }\n\n"
        )

    # ExportAction desactivado — requiere pxlrbt/filament-excel
    export_action = ""

    # Relaciones como Select en el formulario
    rel_fields = ""  # desactivado — relaciones en formularios requieren modelos con relationship() definido
    if False and RELACIONES_OK and relaciones:
        from relations import gen_filament_select
        tabla_n = nombre_tabla(alias)
        rels_hoja = [r for r in relaciones if r["tabla_origen"] == tabla_n]
        for rel in rels_hoja[:3]:
            campo = rel["campo_origen"]
            if campo not in cols:
                continue
            rel_fields += (
                "\n            Forms\\Components\\Select::make('" + campo + "')\n"
                "                ->label('" + campo.replace('_',' ').capitalize() + "')\n"
                "                ->relationship('" + campo.rstrip('s') + "', '" + rel['campo_destino'] + "')\n"
                "                ->searchable()->preload()->nullable(),"
            )

    return (
        "<?php\n\n"
        "namespace App\\Filament\\Resources;\n\n"
        "use App\\Filament\\Resources\\" + resource + "\\Pages;\n"
        "use App\\Models\\" + modelo + ";\n"
        "use Filament\\Forms;\n"
        "use Filament\\Schemas\\Schema;\n"
        "use Filament\\Resources\\Resource;\n"
        "use Filament\\Tables;\n"
        "use Filament\\Tables\\Table;\n\n"
        "class " + resource + " extends Resource\n"
        "{\n"
        "    protected static ?string $model = " + modelo + "::class;\n"
        "    protected static \\BackedEnum|string|null $navigationIcon = 'heroicon-o-table-cells';\n"
        "    protected static ?string $navigationLabel = '" + alias.replace('_',' ').title() + "';\n\n"
        "    protected static ?string $pluralModelLabel = '" + alias.replace('_',' ').title() + "';\n\n"
        "    public static function form(Schema $schema): Schema\n"
        "    {\n"
        "        return $schema->components([\n"
        + form_str + rel_fields + placeholders_str + "\n"
        "        ]);\n"
        "    }\n\n"
        "    public static function table(Table $table): Table\n"
        "    {\n"
        "        return $table\n"
        ""  # headerActions removido
        "            ->columns([\n"
        + table_str + "\n"
        "            ])\n"
        "            ->filters([" + filters_str + "\n"
        "            ])\n"
        "            ->actions([\n"
        "                \\Filament\\Actions\\EditAction::make(),\n"
        "                \\Filament\\Actions\\DeleteAction::make(),\n"
        "            ])\n"
        "            ->bulkActions([\n"
        "                \\Filament\\Actions\\BulkActionGroup::make([\n"
        "                    \\Filament\\Actions\\DeleteBulkAction::make(),\n"
        "                ]),\n"
        "            ]);\n"
        "    }\n\n"
        + global_search +
        "    public static function getPages(): array\n"
        "    {\n"
        "        return [\n"
        "            'index'  => Pages\\List" + modelo + "s::route('/'),\n"
        "            'create' => Pages\\Create" + modelo + "::route('/create'),\n"
        "            'edit'   => Pages\\Edit" + modelo + "::route('/{record}/edit'),\n"
        "        ];\n"
        "    }\n"
        "}\n"
    )


def gen_form_request(alias: str, cfg_hoja: dict, enums: dict | None = None) -> str:
    """Genera Laravel FormRequest con reglas de validación desde el JSON.

    Mejoras v19:
      - Identificador → required (no nullable).
      - Campos calculados por observer → no se validan (el observer los rellena).
      - Email con max:255.
      - `in:` para enum cuando hay estados definidos.
    Mejoras v20:
      - Enum auto-detectado del Excel → `in:val1,val2,...`
    """
    modelo_n  = nombre_modelo(alias)
    cols      = cfg_hoja.get("columnas", {})
    estados   = cfg_hoja.get("logica", {}).get("estados", [])
    identif   = cfg_hoja.get("identificador")
    calc      = {r["campo"] for r in _calculos_aplicables(cols)}
    enums     = enums or {}

    reglas = []
    for campo in cols.keys():
        if campo in ("id", "numero"):
            continue
        if campo in calc:
            continue  # los rellena el observer
        tipo, mod = inferir_tipo(campo)
        regla_partes = []

        es_identif = (campo == identif)
        if es_identif or "nullable" not in mod:
            regla_partes.append("required")
        else:
            regla_partes.append("nullable")

        if tipo.startswith("decimal") or tipo == "integer":
            regla_partes.append("numeric")
            regla_partes.append("min:0")
        elif tipo == "timestamp":
            regla_partes.append("date")
        elif tipo == "boolean":
            regla_partes.append("boolean")
        elif campo in ("correo", "email"):
            regla_partes.append("email")
            regla_partes.append("max:255")
        elif campo == "estado" and estados:
            vals = ",".join(estados)
            regla_partes.append(f"in:{vals}")
        elif campo in enums:
            # Comas dentro de valores se escapan (Laravel separa con comas)
            vals = ",".join(v.replace(",", "\\,") for v in enums[campo])
            regla_partes.append(f"in:{vals}")
        else:
            regla_partes.append("string")
            regla_partes.append("max:255")

        reglas.append(f"            '{campo}' => '{"|".join(regla_partes)}',")

    reglas_str = "\n".join(reglas)

    return (
        "<?php\n\n"
        "namespace App\\Http\\Requests;\n\n"
        "use Illuminate\\Foundation\\Http\\FormRequest;\n\n"
        "class " + modelo_n + "Request extends FormRequest\n"
        "{\n"
        "    public function authorize(): bool\n"
        "    {\n"
        "        return true;\n"
        "    }\n\n"
        "    public function rules(): array\n"
        "    {\n"
        "        return [\n"
        + reglas_str + "\n"
        "        ];\n"
        "    }\n"
        "}\n"
    )


def gen_seeder(alias: str, cfg_hoja: dict) -> str:
    """Genera DatabaseSeeder con datos de ejemplo."""
    modelo_n = nombre_modelo(alias)
    cols    = cfg_hoja.get("columnas", {})
    estados = cfg_hoja.get("logica", {}).get("estados", ["Activo"])

    fakes = []
    for campo in list(cols.keys())[:8]:
        if campo in ("id", "numero"):
            continue
        tipo, _ = inferir_tipo(campo)
        n = campo.lower()
        if "nombre" in n or "producto" in n or "descripcion" in n:
            fakes.append(f"            '{campo}' => fake()->words(3, true),")
        elif "cliente" in n:
            fakes.append(f"            '{campo}' => fake()->name(),")
        elif "email" in n or "correo" in n:
            fakes.append(f"            '{campo}' => fake()->email(),")
        elif "telefono" in n or "whatsapp" in n:
            fakes.append(f"            '{campo}' => fake()->phoneNumber(),")
        elif "sku" in n or "codigo" in n:
            fakes.append(f"            '{campo}' => strtoupper(fake()->lexify('???##')),")
        elif "estado" in n:
            opts = "', '".join(estados)
            fakes.append(f"            '{campo}' => fake()->randomElement(['{opts}']),")
        elif tipo.startswith("decimal") or tipo == "integer":
            fakes.append(f"            '{campo}' => fake()->numberBetween(1000, 100000),")
        elif "fecha" in n:
            fakes.append(f"            '{campo}' => fake()->dateTimeBetween('-1 year', 'now'),")
        else:
            fakes.append(f"            '{campo}' => fake()->word(),")

    fakes_str = "\n".join(fakes)

    return (
        "<?php\n\n"
        "namespace Database\\Seeders;\n\n"
        "use App\\Models\\" + modelo_n + ";\n"
        "use Illuminate\\Database\\Seeder;\n\n"
        "class " + modelo_n + "Seeder extends Seeder\n"
        "{\n"
        "    public function run(): void\n"
        "    {\n"
        "        " + modelo_n + "::factory(10)->create();\n"
        "        // O datos de ejemplo fijos:\n"
        "        // " + modelo_n + "::create([\n"
        + fakes_str + "\n"
        "        // ]);\n"
        "    }\n"
        "}\n"
    )



def gen_filament_pages(alias: str, cfg_hoja: dict) -> dict:
    """Genera las 3 Pages que necesita cada Filament Resource."""
    modelo_n = nombre_modelo(alias)
    pages    = {}
    ns_r = "App\\Filament\\Resources\\"
    ns_f = "Filament\\"

    tabla_n = nombre_tabla(alias)
    pages["app/Filament/Resources/" + modelo_n + "Resource/Pages/List" + modelo_n + "s.php"] = (
        "<?php\n\n"
        "namespace " + ns_r + modelo_n + "Resource\\Pages;\n\n"
        "use " + ns_r + modelo_n + "Resource;\n"
        "use " + ns_f + "Actions;\n"
        "use App\\Models\\" + modelo_n + ";\n"
        "use " + ns_f + "Resources\\Pages\\ListRecords;\n\n"
        "class List" + modelo_n + "s extends ListRecords\n"
        "{\n"
        "    protected static string $resource = " + modelo_n + "Resource::class;\n\n"
        "    protected function getHeaderActions(): array\n"
        "    {\n"
        "        return [\n"
        "            Actions\\CreateAction::make(),\n"
        "            Actions\\Action::make('export_csv')\n"
        "                ->label('Exportar CSV')\n"
        "                ->icon('heroicon-o-arrow-down-tray')\n"
        "                ->color('success')\n"
        "                ->action(function () {\n"
        "                    $registros = " + modelo_n + "::all();\n"
        "                    $filename = '" + tabla_n + "_' . now()->format('Y-m-d_His') . '.csv';\n"
        "                    return response()->streamDownload(function () use ($registros) {\n"
        "                        $out = fopen('php://output', 'w');\n"
        "                        fwrite($out, \"\\xEF\\xBB\\xBF\");\n"
        "                        if ($registros->isNotEmpty()) {\n"
        "                            fputcsv($out, array_keys($registros->first()->toArray()), ';');\n"
        "                            foreach ($registros as $r) {\n"
        "                                fputcsv($out, array_map(fn($v) => is_array($v) ? json_encode($v) : (string) $v, $r->toArray()), ';');\n"
        "                            }\n"
        "                        }\n"
        "                        fclose($out);\n"
        "                    }, $filename, ['Content-Type' => 'text/csv; charset=UTF-8']);\n"
        "                }),\n"
        "        ];\n"
        "    }\n"
        "}\n"
    )

    pages["app/Filament/Resources/" + modelo_n + "Resource/Pages/Create" + modelo_n + ".php"] = (
        "<?php\n\n"
        "namespace " + ns_r + modelo_n + "Resource\\Pages;\n\n"
        "use " + ns_r + modelo_n + "Resource;\n"
        "use " + ns_f + "Resources\\Pages\\CreateRecord;\n\n"
        "class Create" + modelo_n + " extends CreateRecord\n"
        "{\n"
        "    protected static string $resource = " + modelo_n + "Resource::class;\n"
        "}\n"
    )

    pages["app/Filament/Resources/" + modelo_n + "Resource/Pages/Edit" + modelo_n + ".php"] = (
        "<?php\n\n"
        "namespace " + ns_r + modelo_n + "Resource\\Pages;\n\n"
        "use " + ns_r + modelo_n + "Resource;\n"
        "use " + ns_f + "Actions;\n"
        "use " + ns_f + "Resources\\Pages\\EditRecord;\n\n"
        "class Edit" + modelo_n + " extends EditRecord\n"
        "{\n"
        "    protected static string $resource = " + modelo_n + "Resource::class;\n\n"
        "    protected function getHeaderActions(): array\n"
        "    {\n"
        "        return [Actions\\DeleteAction::make()];\n"
        "    }\n"
        "}\n"
    )

    return pages


def gen_api_routes(hojas: dict) -> str:
    rutas = []
    for alias, cfg_hoja in hojas.items():
        if cfg_hoja.get("tipo") not in ("catalogo", "registros"):
            continue
        modelo  = nombre_modelo(alias)
        tabla   = nombre_tabla(alias)
        rutas.append(
            f"Route::apiResource('{tabla}', \\App\\Http\\Controllers\\Api\\{modelo}Controller::class);"
        )
    rutas_str = "\n".join(rutas)
    return f"""<?php

use Illuminate\\Support\\Facades\\Route;

/*
|--------------------------------------------------------------------------
| API Routes — Generadas automáticamente desde el JSON de configuración
|--------------------------------------------------------------------------
*/

{rutas_str}
"""


def gen_api_controller(alias: str, cfg_hoja: dict) -> str:
    modelo = nombre_modelo(alias)
    ns = "\\App\\"
    return (
        "<?php\n\n"
        "namespace App\\Http\\Controllers\\Api;\n\n"
        "use App\\Http\\Controllers\\Controller;\n"
        "use " + ns + "Models\\" + modelo + ";\n"
        "use " + ns + "Http\\Requests\\" + modelo + "Request;\n\n"
        "class " + modelo + "Controller extends Controller\n"
        "{\n"
        "    public function index()\n"
        "    {\n"
        "        return " + modelo + "::all();\n"
        "    }\n\n"
        "    public function store(" + modelo + "Request $request)\n"
        "    {\n"
        "        return " + modelo + "::create($request->validated());\n"
        "    }\n\n"
        "    public function show(" + modelo + " $record)\n"
        "    {\n"
        "        return $record;\n"
        "    }\n\n"
        "    public function update(" + modelo + "Request $request, " + modelo + " $record)\n"
        "    {\n"
        "        $record->update($request->validated());\n"
        "        return $record;\n"
        "    }\n\n"
        "    public function destroy(" + modelo + " $record)\n"
        "    {\n"
        "        $record->delete();\n"
        "        return response()->noContent();\n"
        "    }\n"
        "}\n"
    )



STOCK_FIELDS = {"stock", "stock_disponible", "disponible", "cantidad"}
STOCK_UMBRAL = 5


def gen_filament_widget(cfg: dict) -> str:
    """Genera un widget de KPIs para el dashboard de Filament.

    v21: incluye:
      - Conteo y sumas financieras por hoja (existente).
      - Stat 'Stock crítico' en color danger cuando hay registros con
        stock|cantidad|disponible < STOCK_UMBRAL.
      - KPIs custom desde cfg.logica_negocios.kpis_custom (si está definido).
    """
    hojas     = cfg.get("hojas", {})
    registros = {a: h for a, h in hojas.items() if h.get("tipo") in ("registros", "catalogo")}
    ns        = "\\App\\Models\\"
    logica    = cfg.get("logica_negocios", {})
    moneda    = logica.get("moneda", "CLP")
    simbolo   = "$"

    stats_lines = []

    # 1) KPIs custom desde el JSON: logica_negocios.kpis_custom = [{...}]
    for kpi in logica.get("kpis_custom", []):
        label   = kpi.get("label", "KPI")
        modelo_n = kpi.get("modelo")
        if not modelo_n:
            continue
        agreg   = kpi.get("agregacion", "count")
        color   = kpi.get("color", "primary")
        formato = kpi.get("formato", "numero")
        wheres  = kpi.get("where", [])
        descr   = kpi.get("descripcion", label)

        # Construir cadena de wheres en PHP
        where_php = ""
        for w in wheres:
            if not isinstance(w, list) or len(w) < 3:
                continue
            campo, op, val = w[0], w[1], w[2]
            if val == "today":
                val_php = "now()->startOfDay()"
            elif isinstance(val, (int, float)):
                val_php = str(val)
            else:
                val_php = "'" + str(val).replace("'", "\\'") + "'"
            where_php += "->where('" + campo + "', '" + op + "', " + val_php + ")"

        # Construir agregación
        if agreg == "count":
            valor = ns + modelo_n + "::query()" + where_php + "->count()"
        elif agreg.startswith("sum:"):
            campo = agreg.split(":", 1)[1]
            valor = "(float) " + ns + modelo_n + "::query()" + where_php + "->sum('" + campo + "')"
        elif agreg.startswith("avg:"):
            campo = agreg.split(":", 1)[1]
            valor = "(float) " + ns + modelo_n + "::query()" + where_php + "->avg('" + campo + "')"
        else:
            valor = ns + modelo_n + "::count()"

        if formato == "moneda":
            stat_value = "'" + simbolo + " ' . number_format(" + valor + ", 0, ',', '.')"
            icono = "heroicon-m-banknotes"
        else:
            stat_value = "(string) (" + valor + ")"
            icono = "heroicon-m-chart-bar"

        stats_lines.append(
            "            Stat::make('" + label + "', fn() => " + stat_value + ")\n"
            "                ->description('" + descr.replace("'", "\\'") + "')\n"
            "                ->descriptionIcon('" + icono + "')\n"
            "                ->color('" + color + "'),"
        )

    # 2) Stock crítico (auto-detectado)
    for alias, hoja in registros.items():
        modelo_n = nombre_modelo(alias)
        label    = alias.replace("_", " ").title()
        cols     = list(hoja.get("columnas", {}).keys())
        for campo in cols:
            if campo not in STOCK_FIELDS:
                continue
            stats_lines.append(
                "            Stat::make('" + label + " — Stock crítico', fn() => "
                + ns + modelo_n + "::where('" + campo + "', '<', " + str(STOCK_UMBRAL) + ")->count())\n"
                "                ->description('Registros con " + campo + " < " + str(STOCK_UMBRAL) + "')\n"
                "                ->descriptionIcon('heroicon-m-exclamation-triangle')\n"
                "                ->color(fn() => " + ns + modelo_n + "::where('" + campo + "', '<', " + str(STOCK_UMBRAL) + ")->count() > 0 ? 'danger' : 'gray'),"
            )
            break  # solo un stock-stat por hoja

    # 3) Conteos y sumas financieras por hoja
    for alias, hoja in list(registros.items())[:6]:
        modelo_n = nombre_modelo(alias)
        label    = alias.replace("_", " ").title()
        cols     = list(hoja.get("columnas", {}).keys())

        stats_lines.append(
            "            Stat::make('" + label + " — Total', fn() => "
            + ns + modelo_n + "::count())\n"
            "                ->description('Registros en " + label + "')\n"
            "                ->descriptionIcon('heroicon-m-rectangle-stack')\n"
            "                ->color('primary'),"
        )

        sumas = 0
        for campo in cols:
            if sumas >= 2:
                break
            if campo not in CAMPOS_MONEDA:
                continue
            label_campo = campo.replace("_", " ").capitalize()
            stats_lines.append(
                "            Stat::make('" + label + " — " + label_campo + "', "
                "fn() => '" + simbolo + " ' . number_format((float) "
                + ns + modelo_n + "::sum('" + campo + "'), 0, ',', '.'))\n"
                "                ->description('Suma " + label_campo + " (" + moneda + ")')\n"
                "                ->descriptionIcon('heroicon-m-banknotes')\n"
                "                ->color('success'),"
            )
            sumas += 1

    stats_str = "\n".join(stats_lines) if stats_lines else (
        "            Stat::make('Sin datos', '0')->color('gray'),"
    )
    ns_w = "Filament\\Widgets"

    return (
        "<?php\n\n"
        "namespace App\\" + ns_w + ";\n\n"
        "use " + ns_w + "\\StatsOverviewWidget as BaseWidget;\n"
        "use " + ns_w + "\\StatsOverviewWidget\\Stat;\n\n"
        "class KraftDoStatsWidget extends BaseWidget\n"
        "{\n"
        "    protected ?string $heading = 'Indicadores generales';\n\n"
        "    protected function getStats(): array\n"
        "    {\n"
        "        return [\n"
        + stats_str + "\n"
        "        ];\n"
        "    }\n"
        "}\n"
    )


def gen_recalcular_command(modelos_observers: list[str]) -> str:
    """Genera app/Console/Commands/RecalcularTodo.php que llama save() en cada
    registro de los modelos con observer, forzando recálculo de campos derivados."""
    if not modelos_observers:
        modelos_observers = []
    lineas = ",\n".join(
        "            \\App\\Models\\" + m + "::class"
        for m in modelos_observers
    )
    return (
        "<?php\n\n"
        "namespace App\\Console\\Commands;\n\n"
        "use Illuminate\\Console\\Command;\n\n"
        "class RecalcularTodo extends Command\n"
        "{\n"
        "    protected $signature = 'kraftdo:recalcular';\n"
        "    protected $description = 'Recalcula todos los campos derivados llamando save() en cada registro';\n\n"
        "    public function handle(): int\n"
        "    {\n"
        "        $modelos = [\n"
        + lineas + "\n"
        "        ];\n\n"
        "        foreach ($modelos as $clase) {\n"
        "            if (!class_exists($clase)) {\n"
        "                continue;\n"
        "            }\n"
        "            $count = 0;\n"
        "            $clase::query()->lazy()->each(function ($r) use (&$count) {\n"
        "                $r->save();\n"
        "                $count++;\n"
        "            });\n"
        "            $this->info(\"  {$clase}: {$count} registros recalculados\");\n"
        "        }\n\n"
        "        $this->info('✅ Recalculo completo.');\n"
        "        return self::SUCCESS;\n"
        "    }\n"
        "}\n"
    )


def gen_install_script(empresa: str, hojas: dict) -> str:
    modelos = [nombre_modelo(a) for a, h in hojas.items()
               if h.get("tipo") in ("catalogo", "registros")]
    resources_cmd = "\n".join(
        f"php artisan make:filament-resource {m} --generate --force"
        for m in modelos
    )
    seeders_cmd = "\n".join(
        f"php artisan db:seed --class={nombre_modelo(a)}Seeder"
        for a in hojas.keys()
    )
    return (
        "#!/bin/bash\n"
        "# KraftDo — install.sh\n"
        "# Instala el sistema generado para: " + empresa + "\n"
        "# Ejecutar desde la raíz del proyecto Laravel\n\n"
        "set -e\n"
        'echo "🚀 Instalando sistema ' + empresa + '..."\n\n'
        "# 1. Dependencias\n"
        "composer require filament/filament\\n"
        "composer require bezhansalleh/filament-shield\\n"
        "composer require pxlrbt/filament-excel\\n"
        "composer require leandrocfe/filament-apex-charts\\n"
        "composer require spatie/laravel-medialibrary\\n"
        "composer require filament/spatie-laravel-media-library-plugin\\n"
        'echo "✅ Dependencias + plugins Filament instalados"\n\n'
        "# 2. Migraciones\n"
        "php artisan migrate --force\n"
        'echo "✅ Tablas creadas"\n\n'
        "# 3. Seeders (datos de ejemplo)\n"
        + seeders_cmd + "\n"
        'echo "✅ Datos de ejemplo cargados"\n\n'
        "# 4. Recursos Filament\n"
        + resources_cmd + "\n"
        'echo "✅ Recursos Filament generados"\n\n'
        "# 5. Compilar assets\n"
        "npm install && npm run build\n"
        'echo "✅ Assets compilados"\n\n'
        "# 6. Recalcular campos derivados (observers se ejecutan al save)\n"
        "php artisan kraftdo:recalcular || true\n"
        'echo "✅ Campos derivados recalculados"\n\n'
        "# 7. Crear usuario admin\n"
        "php artisan make:filament-user\n"
        'echo "✅ Listo! Abre /admin en tu navegador"\n'
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def _auto_indices(columnas: dict) -> list[str]:
    """Detecta campos que deberían tener índice MySQL automáticamente."""
    indices = []
    patrones_indice = [
        "fecha", "date", "created", "updated",
        "estado", "status", "tipo", "type",
        "id_", "_id", "sku", "email",
        "cliente", "proveedor", "empresa",
    ]
    for campo in columnas.keys():
        campo_lower = campo.lower()
        if any(p in campo_lower for p in patrones_indice):
            indices.append(campo)
    return indices



def _crear_base_laravel(output_dir: str, empresa: str, cfg: dict) -> bool:
    """
    Crea un proyecto Laravel completo con Filament instalado.
    Retorna True si se creó correctamente.
    """
    import subprocess, shutil

    nombre = cfg["empresa"]["nombre"]
    db_name = empresa  # usar el nombre de empresa directamente como nombre de BD
    db_pass = "4c4e99bc4d1c2e6a"  # password MySQL del usuario kraftdo

    print(f"\n🚀 Creando base Laravel en {output_dir}...")

    # Verificar que composer esté disponible
    if not shutil.which("composer"):
        print("❌ composer no encontrado — instalarlo primero")
        print("   curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer")
        return False

    # Si ya existe y tiene artisan, no recrear
    if os.path.exists(os.path.join(output_dir, "artisan")):
        print(f"  ✓ Base Laravel ya existe en {output_dir}")
        return True

    parent = os.path.dirname(os.path.abspath(output_dir))
    dirname = os.path.basename(output_dir)

    # 1. composer create-project
    print("  📦 Ejecutando composer create-project laravel/laravel ...")
    r = subprocess.run(
        ["composer", "create-project", "laravel/laravel", dirname, "--no-interaction", "--quiet"],
        cwd=parent, capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"  ❌ Error en composer create-project:\n{r.stderr[:500]}")
        return False
    print("  ✓ Laravel instalado")

    # 2. composer require filament
    print("  🎛️  Instalando Filament 3 ...")
    r = subprocess.run(
        ["composer", "require", "filament/filament:^4.0", "--no-interaction", "--quiet"],
        cwd=output_dir, capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"  ❌ Error instalando Filament:\n{r.stderr[:500]}")
        return False
    print("  ✓ Filament instalado")

    # 3. php artisan filament:install --panels
    print("  ⚙️  Configurando panel Filament ...")
    r = subprocess.run(
        ["php", "artisan", "filament:install", "--panels", "--no-interaction"],
        cwd=output_dir, capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"  ❌ Error en filament:install:\n{r.stderr[:300]}")
        return False
    print("  ✓ Panel Filament configurado")

    # 4. Escribir .env con datos de la empresa
    env_path = os.path.join(output_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            env = f.read()
        env = re.sub(r'APP_NAME=.*', 'APP_NAME="' + nombre + '"', env)
        # Laravel 13 tiene DB_ comentadas — descomentar y configurar
        env = re.sub(r"#\s*DB_CONNECTION=.*", "DB_CONNECTION=mysql", env)
        env = re.sub(r"DB_CONNECTION=.*", "DB_CONNECTION=mysql", env)
        env = re.sub(r"#\s*DB_HOST=.*", "DB_HOST=127.0.0.1", env)
        env = re.sub(r"DB_HOST=.*", "DB_HOST=127.0.0.1", env)
        env = re.sub(r"#\s*DB_PORT=.*", "DB_PORT=3306", env)
        env = re.sub(r"DB_PORT=.*", "DB_PORT=3307", env)
        env = re.sub(r"#\s*DB_DATABASE=.*", f"DB_DATABASE={db_name}", env)
        env = re.sub(r"DB_DATABASE=.*", f"DB_DATABASE={db_name}", env)
        env = re.sub(r"#\s*DB_USERNAME=.*", "DB_USERNAME=kraftdo", env)
        env = re.sub(r"DB_USERNAME=.*", "DB_USERNAME=kraftdo", env)
        env = re.sub(r"DB_PASSWORD=\S*", f"DB_PASSWORD={db_pass}", env)
        env = re.sub(r"DB_PASSWORD=\S*", f"DB_PASSWORD={db_pass}", env)
        env = re.sub(r"DB_HOST=.*", "DB_HOST=127.0.0.1", env)
        env = re.sub(r"DB_PORT=.*", "DB_PORT=3307", env)
        env = re.sub(r"DB_DATABASE=.*", f"DB_DATABASE={db_name}", env)
        env = re.sub(r"DB_USERNAME=.*", "DB_USERNAME=kraftdo", env)
        env = re.sub(r"DB_PASSWORD=.*", "DB_PASSWORD=", env)
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(env)
        # Asegurar DB_PASSWORD en el .env
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\nDB_PASSWORD={db_pass}\n")
        print(f"  ✓ .env configurado para {nombre} (mysql)")

    # 5. php artisan key:generate
    subprocess.run(
        ["php", "artisan", "key:generate", "--no-interaction"],
        cwd=output_dir, capture_output=True
    )
    print("  ✓ APP_KEY generado")

    print(f"\n✅ Base Laravel lista en {output_dir}\n")
    return True

def generar(empresa: str, output_dir: str, preview: bool = False, solo: str = None):
    # Cargar config
    base = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base, "empresas", f"{empresa}.json")
    if not os.path.exists(cfg_path):
        print(f"❌ No encontré: {cfg_path}")
        sys.exit(1)

    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    nombre_empresa = cfg["empresa"]["nombre"]
    hojas = cfg["hojas"]

    print(f"\n{'='*60}")
    print(f"  KraftDo Generator — {nombre_empresa}")
    print(f"  Output: {output_dir}")
    print(f"{'='*60}\n")

    # Opción B: crear base Laravel completa si no existe
    if not preview:
        if not _crear_base_laravel(output_dir, empresa, cfg):
            print("⚠️  Continuando sin crear base Laravel — solo se generan los archivos")

    archivos = {}  # path → contenido

    hojas_generables = {
        a: h for a, h in hojas.items()
        if h.get("tipo") in ("catalogo", "registros")
    }

    # 1. Migraciones
    if not solo or solo == "migraciones":
        for idx, (alias, cfg_hoja) in enumerate(hojas_generables.items(), start=1):
            nombre_arch = f"database/migrations/{nombre_migration(alias, idx)}.php"
            archivos[nombre_arch] = gen_migracion(alias, cfg_hoja, idx)
            print(f"  📄 {nombre_arch}")

    # 2. Modelos
    # Analizar patrones del Excel si está disponible
    excel_path_check = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     cfg.get("fuente", {}).get("archivo", ""))
    patrones = {}
    if RELACIONES_OK and os.path.exists(excel_path_check):
        try:
            patrones = _analizar_patrones(excel_path_check)
            hojas_raras = {h: d for h, d in patrones.items()
                           if d.get("patron") not in ("vertical", "con_totales", "vacia")}
            if hojas_raras:
                print(f"  ⚠️  Patrones no estándar detectados:")
                for hoja, diag in hojas_raras.items():
                    print(f"     {hoja}: {diag['patron']} — {diag['transformacion'][:60]}")
                print()
        except Exception:
            pass

    # Calcular relaciones y fórmulas una sola vez
    rels = detectar_relaciones(cfg) if RELACIONES_OK else []
    rels_x_tabla = relaciones_por_tabla(rels) if RELACIONES_OK else {}
    excel_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), cfg.get("fuente", {}).get("archivo", ""))
    formulas_all = analizar_excel_formulas(excel_path, cfg) if RELACIONES_OK and os.path.exists(excel_path) else {}
    # Pasar datos a gen_modelo via atributos
    gen_modelo._relaciones = rels
    gen_modelo._formulas   = formulas_all

    # Detectar enums leyendo el Excel (string columns con pocos valores únicos)
    enums_por_hoja = _detectar_enums_excel(excel_path, cfg)
    if enums_por_hoja:
        n = sum(len(e) for e in enums_por_hoja.values())
        print(f"  🔠 {n} columnas detectadas como enum auto:")
        for a, e in enums_por_hoja.items():
            for campo, vals in e.items():
                muestra = ", ".join(vals[:4]) + (" …" if len(vals) > 4 else "")
                print(f"     {a}.{campo} = [{muestra}]")
        print()

    if not solo or solo == "modelos":
        for alias, cfg_hoja in hojas_generables.items():
            modelo_n = nombre_modelo(alias)
            nombre_arch = f"app/Models/{modelo_n}.php"
            archivos[nombre_arch] = gen_modelo(alias, cfg_hoja, cfg, rels, formulas_all)
            print(f"  📦 {nombre_arch}")

    # 3. Filament Resources
    if not solo or solo == "filament":
        for alias, cfg_hoja in hojas_generables.items():
            modelo = nombre_modelo(alias)
            nombre_arch = f"app/Filament/Resources/{modelo}Resource.php"
            archivos[nombre_arch] = gen_filament_resource(
                alias, cfg_hoja, cfg, rels, enums_por_hoja.get(alias, {})
            )
            print(f"  🎛️  {nombre_arch}")

    # 3a-bis. Observers (campos calculados auto al guardar)
    modelos_con_observer = []
    if not solo or solo in ("modelos", "observers"):
        for alias, cfg_hoja in hojas_generables.items():
            obs = gen_observer(alias, cfg_hoja)
            if obs is None:
                continue
            modelo_n = nombre_modelo(alias)
            nombre_arch = f"app/Observers/{modelo_n}Observer.php"
            archivos[nombre_arch] = obs
            modelos_con_observer.append(modelo_n)
            print(f"  👁️  {nombre_arch}")

    # 3a-ter. Comando artisan kraftdo:recalcular
    if (not solo or solo in ("modelos", "observers")) and modelos_con_observer:
        nombre_arch = "app/Console/Commands/RecalcularTodo.php"
        archivos[nombre_arch] = gen_recalcular_command(modelos_con_observer)
        print(f"  🔁 {nombre_arch}")

    # 3b. FormRequests
    if not solo or solo in ("modelos", "requests"):
        for alias, cfg_hoja in hojas_generables.items():
            modelo_n = nombre_modelo(alias)
            nombre_arch = f"app/Http/Requests/{modelo_n}Request.php"
            archivos[nombre_arch] = gen_form_request(
                alias, cfg_hoja, enums_por_hoja.get(alias, {})
            )
            print(f"  ✅ {nombre_arch}")

    # 3c. Seeders
    if not solo or solo in ("modelos", "seeders"):
        for alias, cfg_hoja in hojas_generables.items():
            modelo_n = nombre_modelo(alias)
            nombre_arch = f"database/seeders/{modelo_n}Seeder.php"
            archivos[nombre_arch] = gen_seeder(alias, cfg_hoja)
            print(f"  🌱 {nombre_arch}")

    # 3d. Filament Pages
    if not solo or solo in ("filament", "pages"):
        for alias, cfg_hoja in hojas_generables.items():
            pages = gen_filament_pages(alias, cfg_hoja)
            for path, contenido in pages.items():
                archivos[path] = contenido
                print(f"  📄 {path}")

    # 4. API Routes y Controllers
    if not solo or solo == "api":
        archivos["routes/api.php"] = gen_api_routes(hojas_generables)
        print(f"  🔌 routes/api.php")
        for alias, cfg_hoja in hojas_generables.items():
            modelo = nombre_modelo(alias)
            nombre_arch = f"app/Http/Controllers/Api/{modelo}Controller.php"
            archivos[nombre_arch] = gen_api_controller(alias, cfg_hoja)
            print(f"  🔌 {nombre_arch}")

    # 6. Dashboard Widget de Filament
    if not solo or solo in ("filament", "widgets"):
        nombre_arch = "app/Filament/Widgets/KraftDoStatsWidget.php"
        archivos[nombre_arch] = gen_filament_widget(cfg)
        print(f"  📊 {nombre_arch}")

    # 5. Script de instalación
    archivos["install.sh"] = gen_install_script(empresa, hojas_generables)
    print(f"  ⚙️  install.sh")

    print(f"\n  Total: {len(archivos)} archivos\n")

    if preview:
        print("── PREVIEW (no se escriben archivos) ──────────────────────")
        for path, contenido in list(archivos.items())[:3]:
            print(f"\n{'─'*60}\n{path}\n{'─'*60}")
            print(contenido[:800] + ("..." if len(contenido) > 800 else ""))
        return archivos

    # Escribir archivos
    for path, contenido in archivos.items():
        full_path = os.path.join(output_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(contenido)

    print(f"✅ Generado en: {output_dir}")

    # Auto-setup: migrar y crear usuario admin si no es preview
    if not preview:
        import subprocess
        db_pass = "4c4e99bc4d1c2e6a"
        db_name = empresa  # usar el nombre de empresa directamente como nombre de BD
        db_root_pass = "51381c69b62f87a6"
        print("\n🔧 Configurando base de datos...")
        # Crear BD si no existe
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host="127.0.0.1", port=3307,
                user="root", password=db_root_pass
            )
            conn.cursor().execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
            cur = conn.cursor()
            cur.execute(f"GRANT ALL ON `{db_name}`.* TO 'kraftdo'@'%'")
            cur.execute("FLUSH PRIVILEGES")
            conn.commit()
            conn.close()
            print(f"  ✓ BD {db_name} creada")
        except Exception as e:
            print(f"  ⚠️  No se pudo crear la BD: {e}")
        # Migrar
        r = subprocess.run(
            ["php", "artisan", "migrate:fresh", "--force"],
            cwd=output_dir, capture_output=True, text=True
        )
        if r.returncode == 0:
            print("  ✓ Migraciones ejecutadas")
        else:
            print(f"  ⚠️  Error en migrate: {r.stderr[:200]}")

        # Crear usuario admin
        tinker_cmd = (
            "App\\Models\\User::create(["
            "'name'=>'Admin',"
            f"'email'=>'{cfg['empresa'].get('email','admin@kraftdo.cl')}',"
            "'password'=>bcrypt('kraftdo2026')"
            "]);echo 'ok';"
        )
        subprocess.run(
            ["php", "artisan", "tinker", "--execute", tinker_cmd],
            cwd=output_dir, capture_output=True
        )
        print("  ✓ Usuario admin creado (password: kraftdo2026)")

        # Importar Excel
        importer = os.path.join(os.path.dirname(os.path.abspath(__file__)), "importar_excel_a_mysql.py")
        if os.path.exists(importer):
            print("\n📊 Importando datos del Excel...")
            r = subprocess.run(
                ["python3", importer, empresa, output_dir],
                capture_output=True, text=True
            )
            print(r.stdout)
            if r.returncode != 0:
                print(f"  ⚠️  {r.stderr[:200]}")

        # Recalcular campos derivados (observers se ejecutan en save())
        print("\n🔁 Recalculando campos derivados...")
        r = subprocess.run(
            ["php", "artisan", "kraftdo:recalcular"],
            cwd=output_dir, capture_output=True, text=True
        )
        if r.returncode == 0:
            for line in r.stdout.strip().splitlines()[-6:]:
                print(line)
        else:
            print(f"  ⚠️  {r.stderr[:200]}")

        # Puerto único por empresa basado en hash del nombre
        import hashlib
        puerto = 8080 + int(hashlib.md5(empresa.encode()).hexdigest(), 16) % 900
        print(f"\n🚀 Panel listo en: php artisan serve --host=0.0.0.0 --port={puerto}")
        print(f"   URL: http://localhost:{puerto}/admin")
        print(f"   Email: {cfg['empresa'].get('email','admin@kraftdo.cl')}")
        print(f"   Password: kraftdo2026\n")


    return archivos


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KraftDo Generator")
    parser.add_argument("empresa", help="Nombre de la empresa (ej: kraftdo)")
    parser.add_argument("--output", default="./laravel_output", help="Directorio de salida")
    parser.add_argument("--preview", action="store_true", help="Mostrar sin escribir")
    parser.add_argument("--solo",
                        choices=["migraciones", "modelos", "filament", "api",
                                 "pages", "seeders", "requests", "observers", "widgets"],
                        help="Generar solo una capa")
    args = parser.parse_args()

    generar(args.empresa, args.output, args.preview, args.solo)
