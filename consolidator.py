"""
KraftDo — consolidator.py
Consolida múltiples hojas Excel que representan la misma entidad
en una sola tabla MySQL normalizada con campo discriminador.

Ejemplo real:
  Hojas: productos_nfc, sublimacion, impresion3d, packs
  → Una tabla: productos(tipo, sku, nombre, precio_1, ..., metadata JSON)

USO desde código:
    from consolidator import Consolidator
    c = Consolidator(cfg)
    c.agregar_grupo("productos", ["productos_nfc","sublimacion","impresion3d"])
    json_consolidado = c.generar_json_consolidado()

USO desde CLI:
    python3 consolidator.py kraftdo --grupos "productos:nfc,sublimacion,impresion3d"
"""

import os
import re
import json
import sys
from copy import deepcopy


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slug(s: str) -> str:
    return re.sub(r'[^a-z0-9_]', '_', str(s).lower().strip()).strip('_')

def _col_union(hojas_cfg: list[dict]) -> dict:
    """
    Une las columnas de múltiples hojas.
    Retorna {campo: letra_o_None} con todas las columnas únicas.
    """
    union = {}
    for hoja in hojas_cfg:
        for campo, letra in hoja.get("columnas", {}).items():
            if campo not in union:
                union[campo] = letra
    return union

def _cols_comunes(hojas_cfg: list[dict]) -> set:
    """Columnas que aparecen en TODAS las hojas del grupo."""
    if not hojas_cfg:
        return set()
    sets = [set(h.get("columnas", {}).keys()) for h in hojas_cfg]
    return sets[0].intersection(*sets[1:]) if len(sets) > 1 else sets[0]

def _cols_especificas(alias: str, hojas_cfg: list[dict],
                      cols_comunes: set) -> dict:
    """Columnas únicas de una hoja específica (no están en las demás)."""
    hoja = next((h for h in hojas_cfg if h.get("_alias") == alias), None)
    if not hoja:
        return {}
    todas = set(hoja.get("columnas", {}).keys())
    especificas = todas - cols_comunes
    return {c: hoja["columnas"][c] for c in especificas}


# ═══════════════════════════════════════════════════════════════════════════════
# CONSOLIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class Consolidator:
    def __init__(self, cfg: dict):
        self.cfg    = deepcopy(cfg)
        self.grupos = {}  # {nombre_entidad: [alias_hoja, ...]}

    def agregar_grupo(self, nombre_entidad: str, aliases: list[str]):
        """
        Define un grupo de consolidación.
        nombre_entidad: nombre de la tabla consolidada (ej: "productos")
        aliases:        hojas que se consolidan (ej: ["nfc", "sublimacion", "3d"])
        """
        # Validar que las hojas existen
        hojas = self.cfg.get("hojas", {})
        validas = [a for a in aliases if a in hojas]
        invalidas = [a for a in aliases if a not in hojas]
        if invalidas:
            print(f"  ⚠️  Hojas no encontradas, se ignorarán: {invalidas}")
        if len(validas) < 2:
            raise ValueError(f"Se necesitan al menos 2 hojas para consolidar. Válidas: {validas}")
        self.grupos[nombre_entidad] = validas

    def analizar_grupo(self, nombre_entidad: str) -> dict:
        """
        Analiza un grupo y retorna un reporte de qué columnas son comunes
        y cuáles son específicas de cada hoja.
        """
        aliases  = self.grupos[nombre_entidad]
        hojas    = self.cfg.get("hojas", {})
        cfgs     = []
        for alias in aliases:
            cfg_hoja = {**hojas[alias], "_alias": alias}
            cfgs.append(cfg_hoja)

        comunes     = _cols_comunes(cfgs)
        union_cols  = _col_union(cfgs)
        especificas = {}
        for alias in aliases:
            esp = _cols_especificas(alias, cfgs, comunes)
            if esp:
                especificas[alias] = esp

        return {
            "entidad":     nombre_entidad,
            "aliases":     aliases,
            "cols_comunes": sorted(comunes),
            "cols_union":   union_cols,
            "cols_especificas": especificas,
            "n_cols_total": len(union_cols),
            "n_cols_comunes": len(comunes),
        }

    def generar_json_consolidado(self) -> dict:
        """
        Genera el JSON de configuración con las hojas consolidadas.
        Las hojas del grupo se reemplazan por una única entrada con campo 'tipo'.
        """
        cfg_nuevo   = deepcopy(self.cfg)
        hojas_nuevo = {}

        # Hojas ya procesadas en algún grupo
        en_grupo = set()
        for aliases in self.grupos.values():
            en_grupo.update(aliases)

        # 1. Agregar hojas consolidadas
        for nombre_entidad, aliases in self.grupos.items():
            reporte      = self.analizar_grupo(nombre_entidad)
            union_cols   = reporte["cols_union"]
            especificas  = reporte["cols_especificas"]

            # Hojas originales para sacar metadata
            hoja_base = self.cfg["hojas"].get(aliases[0], {})
            valores_tipo = [_slug(a) for a in aliases]

            # Guardar mapeo de columnas COMPLETO por cada hoja fuente
            # Esto permite que core.py use el mapeo correcto para cada hoja
            hojas_cfg = self.cfg.get("hojas", {})
            columnas_por_fuente = {}
            for alias in aliases:
                cfg_fuente = hojas_cfg.get(alias, {})
                cols = {k: v for k, v in cfg_fuente.get("columnas", {}).items()
                        if v != "[CALCULADO]"}
                if cols:
                    columnas_por_fuente[alias] = cols

            cfg_consolidada = {
                "nombre":        f"[CONSOLIDADO] {nombre_entidad}",
                "tipo":          hoja_base.get("tipo", "catalogo"),
                "descripcion":   f"Consolidación de: {', '.join(aliases)}",
                "fila_datos":    hoja_base.get("fila_datos", 5),
                "consolidado":   True,
                "fuentes":       aliases,
                "discriminador": "tipo",
                "valores_tipo":  valores_tipo,
                "columnas": {
                    "tipo": "[CALCULADO]",
                    **union_cols,
                },
                "columnas_por_fuente": columnas_por_fuente,
                "cols_especificas": especificas,
                "metadata_campos": list(especificas.keys()) if especificas else [],
            }

            # Copiar logica si existe en la hoja base
            if "logica" in hoja_base:
                cfg_consolidada["logica"] = hoja_base["logica"]
            if hoja_base.get("precios"):
                cfg_consolidada["precios"] = hoja_base["precios"]
            if hoja_base.get("identificador"):
                cfg_consolidada["identificador"] = hoja_base["identificador"]

            hojas_nuevo[nombre_entidad] = cfg_consolidada

        # 2. Agregar hojas que NO están en ningún grupo
        for alias, hoja in self.cfg["hojas"].items():
            if alias not in en_grupo:
                hojas_nuevo[alias] = hoja

        cfg_nuevo["hojas"] = hojas_nuevo
        return cfg_nuevo

    def gen_migracion_consolidada(self, nombre_entidad: str) -> str:
        """
        Genera la migración Laravel para la tabla consolidada.
        Incluye el campo 'tipo' discriminador y 'metadata' JSON
        para campos específicos de cada sub-tipo.
        """
        reporte    = self.analizar_grupo(nombre_entidad)
        cols       = reporte["cols_union"]
        especificas = reporte["cols_especificas"]
        aliases    = reporte["aliases"]
        tabla      = _slug(nombre_entidad)
        ts         = "2026_03_31_000001"

        # Inferir tipos de columna
        lineas_cols = []
        for campo, letra in cols.items():
            if campo == "tipo":
                continue
            n = campo.lower()
            if any(p in n for p in ("precio", "costo", "total", "monto", "margen", "ganancia")):
                lineas_cols.append(f"            $table->decimal('{campo}', 10, 2)->nullable();")
            elif any(p in n for p in ("cantidad", "stock", "dias", "horas")):
                lineas_cols.append(f"            $table->integer('{campo}')->nullable();")
            elif "fecha" in n:
                lineas_cols.append(f"            $table->date('{campo}')->nullable();")
            else:
                lineas_cols.append(f"            $table->string('{campo}', 255)->nullable();")

        cols_str     = "\n".join(lineas_cols)
        valores_tipo = "', '".join(_slug(a) for a in aliases)
        tiene_meta   = bool(especificas)
        meta_col     = "            $table->json('metadata')->nullable(); // Campos específicos por tipo" if tiene_meta else ""

        clase = "Create" + "".join(w.capitalize() for w in tabla.split("_")) + "Table"

        return (
            "<?php\n\n"
            "use Illuminate\\Database\\Migrations\\Migration;\n"
            "use Illuminate\\Database\\Schema\\Blueprint;\n"
            "use Illuminate\\Support\\Facades\\Schema;\n\n"
            f"// Tabla consolidada desde: {', '.join(aliases)}\n"
            f"// Tipos: {valores_tipo}\n\n"
            f"return new class extends Migration\n"
            "{\n"
            "    public function up(): void\n"
            "    {\n"
            f"        Schema::create('{tabla}', function (Blueprint $table) {{\n"
            "            $table->id();\n"
            f"            $table->enum('tipo', ['{valores_tipo}'])->index();\n"
            f"{cols_str}\n"
            f"{meta_col}\n"
            "            $table->timestamps();\n"
            "        });\n"
            "    }\n\n"
            "    public function down(): void\n"
            "    {\n"
            f"        Schema::dropIfExists('{tabla}');\n"
            "    }\n"
            "};\n"
        )

    def gen_modelo_consolidado(self, nombre_entidad: str) -> str:
        """Genera el modelo Eloquent con scopes por tipo."""
        aliases   = self.grupos[nombre_entidad]
        reporte   = self.analizar_grupo(nombre_entidad)
        tabla     = _slug(nombre_entidad)
        clase     = "".join(w.capitalize() for w in tabla.split("_"))
        fillable  = list(reporte["cols_union"].keys())
        fillable_str = "\n        ".join(f"'{c}'," for c in fillable)

        # Scopes por tipo
        scopes = ""
        for alias in aliases:
            tipo    = _slug(alias)
            metodo  = "".join(w.capitalize() for w in tipo.split("_"))
            scopes += (
                f"\n    public function scope{metodo}($query)\n"
                f"    {{\n"
                f"        return $query->where('tipo', '{tipo}');\n"
                f"    }}\n"
            )

        # Cast de metadata
        cast_meta = "\n        'metadata' => 'array'," if reporte["cols_especificas"] else ""

        ns = "\\App\\Models\\"
        return (
            "<?php\n\n"
            "namespace App\\Models;\n\n"
            "use Illuminate\\Database\\Eloquent\\Model;\n"
            "use Illuminate\\Database\\Eloquent\\Factories\\HasFactory;\n\n"
            f"// Modelo consolidado — fuentes: {', '.join(aliases)}\n"
            f"class {clase} extends Model\n"
            "{\n"
            "    use HasFactory;\n\n"
            f"    protected $table = '{tabla}';\n\n"
            "    protected $fillable = [\n"
            f"        'tipo',\n"
            f"        {fillable_str}\n"
            "    ];\n\n"
            "    protected $casts = ["
            f"{cast_meta}\n"
            "    ];\n"
            f"{scopes}"
            "}\n"
        )

    def gen_filament_resource_consolidado(self, nombre_entidad: str) -> str:
        """Genera Resource Filament con filtro por tipo y campo select."""
        aliases  = self.grupos[nombre_entidad]
        tabla    = _slug(nombre_entidad)
        clase    = "".join(w.capitalize() for w in tabla.split("_"))
        reporte  = self.analizar_grupo(nombre_entidad)
        cols     = list(reporte["cols_union"].keys())[:6]
        cols_str = "\n".join(
            f"                Tables\\Columns\\TextColumn::make('{c}')->sortable()->searchable(),"
            for c in cols
        )
        tipos_opts = "\n".join(
            f"                    '{_slug(a)}' => '{a}',"
            for a in aliases
        )

        ns = "\\App\\Filament\\Resources\\"
        return (
            "<?php\n\n"
            f"namespace App\\Filament\\Resources;\n\n"
            "use Filament\\Forms;\n"
            "use Filament\\Tables;\n"
            "use Filament\\Resources\\Resource;\n"
            f"use App\\Models\\{clase};\n\n"
            f"class {clase}Resource extends Resource\n"
            "{\n"
            f"    protected static ?string $model = {clase}::class;\n"
            f"    protected static ?string $navigationIcon = 'heroicon-o-squares-2x2';\n"
            f"    protected static ?string $navigationLabel = '{nombre_entidad.title()}';\n\n"
            "    public static function form(Forms\\Form $form): Forms\\Form\n"
            "    {\n"
            "        return $form->schema([\n"
            "            Forms\\Components\\Select::make('tipo')\n"
            f"                ->options([{tipos_opts}\n                ])\n"
            "                ->required()->reactive(),\n"
            "            // Campos comunes\n"
            "            Forms\\Components\\TextInput::make('sku')->required(),\n"
            "            Forms\\Components\\TextInput::make('nombre')->required(),\n"
            "            Forms\\Components\\TextInput::make('precio_1')\n"
            "                ->numeric()->prefix('$'),\n"
            "            // Campos específicos por tipo (en metadata)\n"
            "            Forms\\Components\\KeyValue::make('metadata')\n"
            "                ->label('Datos específicos del tipo')\n"
            "                ->reorderable(),\n"
            "        ]);\n"
            "    }\n\n"
            "    public static function table(Tables\\Table $table): Tables\\Table\n"
            "    {\n"
            "        return $table\n"
            "            ->columns([\n"
            f"{cols_str}\n"
            "                Tables\\Columns\\BadgeColumn::make('tipo')\n"
            "                    ->colors(['primary' => 'nfc', 'success' => 'sublimacion', 'warning' => 'impresion3d']),\n"
            "            ])\n"
            "            ->filters([\n"
            "                Tables\\Filters\\SelectFilter::make('tipo')\n"
            f"                    ->options([{tipos_opts}\n                    ]),\n"
            "            ]);\n"
            "    }\n\n"
            "    public static function getPages(): array\n"
            "    {\n"
            "        return [\n"
            f"            'index'  => Pages\\List{clase}s::route('/'),\n"
            f"            'create' => Pages\\Create{clase}::route('/create'),\n"
            f"            'edit'   => Pages\\Edit{clase}::route('/{{record}}/edit'),\n"
            "        ];\n"
            "    }\n"
            "}\n"
        )

    def exportar_todo(self, output_dir: str):
        """Genera y guarda todos los archivos de consolidación."""
        os.makedirs(output_dir, exist_ok=True)

        for nombre_entidad in self.grupos:
            # Migración
            mig = self.gen_migracion_consolidada(nombre_entidad)
            path = os.path.join(output_dir, f"create_{_slug(nombre_entidad)}_table.php")
            with open(path, "w") as f:
                f.write(mig)
            print(f"  📄 {os.path.basename(path)}")

            # Modelo
            mod = self.gen_modelo_consolidado(nombre_entidad)
            nombre_clase = "".join(w.capitalize() for w in _slug(nombre_entidad).split("_"))
            path = os.path.join(output_dir, f"{nombre_clase}.php")
            with open(path, "w") as f:
                f.write(mod)
            print(f"  📦 {os.path.basename(path)}")

            # Resource Filament
            res = self.gen_filament_resource_consolidado(nombre_entidad)
            path = os.path.join(output_dir, f"{nombre_clase}Resource.php")
            with open(path, "w") as f:
                f.write(res)
            print(f"  🎛️  {os.path.basename(path)}")

        # JSON consolidado
        cfg_nuevo = self.generar_json_consolidado()
        path = os.path.join(output_dir, "kraftdo_consolidado.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg_nuevo, f, indent=2, ensure_ascii=False)
        print(f"  📋 kraftdo_consolidado.json")


# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="KraftDo Consolidator")
    parser.add_argument("empresa", help="Nombre empresa (ej: kraftdo)")
    parser.add_argument("--grupos", help="Grupos: 'entidad:alias1,alias2;entidad2:alias3,alias4'")
    parser.add_argument("--output", default="./consolidado")
    parser.add_argument("--analizar", action="store_true", help="Solo analizar sin generar")
    args = parser.parse_args()

    cfg_path = os.path.join(os.path.dirname(__file__), "empresas", f"{args.empresa}.json")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    c = Consolidator(cfg)

    # Parsear grupos del argumento
    if args.grupos:
        for grupo_str in args.grupos.split(";"):
            if ":" in grupo_str:
                nombre, aliases_str = grupo_str.split(":", 1)
                aliases = [a.strip() for a in aliases_str.split(",")]
                c.agregar_grupo(nombre.strip(), aliases)
    else:
        # Demo con KraftDo — consolidar las 3 hojas de productos
        c.agregar_grupo("productos", ["productos_nfc", "sublimacion", "impresion3d"])

    for nombre_entidad in c.grupos:
        reporte = c.analizar_grupo(nombre_entidad)
        print(f"\n{'═'*60}")
        print(f"  Entidad: {reporte['entidad']}")
        print(f"  Fuentes: {reporte['aliases']}")
        print(f"  Columnas comunes ({reporte['n_cols_comunes']}): {reporte['cols_comunes'][:5]}...")
        print(f"  Total columnas union: {reporte['n_cols_total']}")
        if reporte["cols_especificas"]:
            for alias, cols in reporte["cols_especificas"].items():
                print(f"  Específicas de {alias}: {list(cols.keys())}")

    if not args.analizar:
        print(f"\nGenerando archivos en: {args.output}")
        c.exportar_todo(args.output)
        print("\n✅ Consolidación completa")
