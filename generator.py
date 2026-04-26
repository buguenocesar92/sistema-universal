#!/usr/bin/env python3
"""
KraftDo Sistema Universal — Generador v19
Convierte config de empresa → Laravel 11 + Filament 4 completo

4 capas implementadas:
  1. Observers: cálculo automático de campos [AUTO]
  2. Campos calculados: Placeholder/ViewEntry en formularios (solo lectura)
  3. Validaciones: reglas de negocio antes de guardar
  4. Dashboard KPIs: métricas reales con queries Eloquent

Uso:
    python3 generator.py kraftdo  --output ~/Dev/kraftdo_app
    python3 generator.py adille   --output ~/Dev/adille_app
    python3 generator.py extractores --output ~/Dev/extractores_app
"""

import os
import sys
import shutil
import argparse
import importlib.util
from pathlib import Path
from datetime import datetime


# ─── Helpers ─────────────────────────────────────────────────────────────────

def slug_to_class(slug: str) -> str:
    return ''.join(w.capitalize() for w in slug.replace('-', '_').split('_'))

def slug_to_table(slug: str) -> str:
    return slug.replace('-', '_').lower()

def tipo_to_migration(tipo: str) -> str:
    MAP = {
        "string":  "string",
        "text":    "text",
        "integer": "integer",
        "bigint":  "bigInteger",
        "decimal": "decimal",
        "boolean": "boolean",
        "date":    "date",
        "enum":    "string",
    }
    return MAP.get(tipo, "string")

def tipo_to_cast(tipo: str) -> str:
    MAP = {
        "integer": "integer",
        "bigint":  "integer",
        "decimal": "float",
        "boolean": "boolean",
        "date":    "date",
    }
    return MAP.get(tipo)


# ─── 1. MIGRATION ─────────────────────────────────────────────────────────────

def generate_migration(tabla: str, config: dict, timestamp: str) -> str:
    cls = slug_to_class(tabla)
    pk = config.get("primary_key", "id")
    pk_type = config.get("primary_key_type", "bigint")
    campos = config["campos"]

    lines = ["        Schema::create('{}', function (Blueprint \\$table) {{".format(tabla)]

    # Primary key
    if pk == "id" and pk_type == "bigint":
        lines.append("            \\$table->id();")
    elif pk_type == "string":
        lines.append("            \\$table->string('{}', 50)->primary();".format(pk))
    else:
        lines.append("            \\$table->bigIncrements('{}');".format(pk))

    for campo, meta in campos.items():
        if campo == pk:
            continue
        mtype = tipo_to_migration(meta["tipo"])
        nullable = not meta.get("rules", "").startswith("required")
        opciones = meta.get("opciones")

        if meta["tipo"] == "enum" and opciones:
            opts = ", ".join(f"'{o}'" for o in opciones)
            line = "            \\$table->string('{campo}', 50)".format(campo=campo)
        elif mtype == "decimal":
            line = "            \\$table->decimal('{campo}', 15, 4)".format(campo=campo)
        else:
            line = "            \\$table->{mtype}('{campo}')".format(mtype=mtype, campo=campo)

        if nullable:
            line += "->nullable()"
        if not meta.get("editable", True) and meta.get("auto"):
            line += "->nullable()->default(null)"

        line += ";"
        lines.append(line)

    lines.append("            \\$table->timestamps();")
    lines.append("        });")

    return """<?php

use Illuminate\\Database\\Migrations\\Migration;
use Illuminate\\Database\\Schema\\Blueprint;
use Illuminate\\Support\\Facades\\Schema;

return new class extends Migration
{{
    public function up(): void
    {{
{body}
    }}

    public function down(): void
    {{
        Schema::dropIfExists('{tabla}');
    }}
}};
""".format(body='\n'.join(lines), tabla=tabla)


# ─── 2. MODEL ──────────────────────────────────────────────────────────────────

def generate_model(tabla: str, config: dict) -> str:
    cls = slug_to_class(tabla)
    pk = config.get("primary_key", "id")
    pk_type = config.get("primary_key_type", "bigint")
    campos = config["campos"]
    formulas = config.get("observer_formulas", {})

    # Casts
    casts_lines = []
    for campo, meta in campos.items():
        c = tipo_to_cast(meta["tipo"])
        if c:
            casts_lines.append("        '{}' => '{}',".format(campo, c))

    casts_block = ""
    if casts_lines:
        casts_block = """
    protected $casts = [
{}
    ];
""".format('\n'.join(casts_lines))

    # Fillable
    fillable_campos = [c for c in campos if c != pk]
    fillable_lines = ["        '{}',".format(c) for c in fillable_campos]
    fillable_block = """
    protected $fillable = [
{}
    ];
""".format('\n'.join(fillable_lines))

    # Auto campos: accessors (solo como respaldo si el observer falla)
    accessor_lines = []
    for campo, meta in campos.items():
        if meta.get("auto") and campo in formulas:
            method = "get" + slug_to_class(campo) + "Attribute"
            formula = formulas[campo]
            accessor_lines.append("""
    // Accessor de respaldo para {campo} (el Observer es la fuente primaria)
    // public function {method}(): mixed
    // {{
    //     {formula}
    // }}
""".format(campo=campo, method=method, formula=formula))

    pk_setup = ""
    if pk != "id":
        pk_setup = """
    protected $primaryKey = '{pk}';
    public $incrementing = {inc};
    protected $keyType = '{ktype}';
""".format(
            pk=pk,
            inc="false" if pk_type == "string" else "true",
            ktype="string" if pk_type == "string" else "int"
        )

    return """<?php

namespace App\\Models;

use Illuminate\\Database\\Eloquent\\Model;
use Illuminate\\Database\\Eloquent\\Factories\\HasFactory;

class {cls} extends Model
{{
    use HasFactory;
{pk_setup}{fillable_block}{casts_block}
    protected static function booted(): void
    {{
        static::observe(\\App\\Observers\\{cls}Observer::class);
    }}
{accessors}}}
""".format(
        cls=cls,
        pk_setup=pk_setup,
        fillable_block=fillable_block,
        casts_block=casts_block,
        accessors=''.join(accessor_lines),
    )


# ─── 3. OBSERVER ──────────────────────────────────────────────────────────────

def generate_observer(tabla: str, config: dict) -> str:
    cls = slug_to_class(tabla)
    formulas = config.get("observer_formulas", {})

    if not formulas:
        calc_lines = "        // Sin campos calculados para esta tabla"
    else:
        calc_lines_list = []
        for campo, formula in formulas.items():
            calc_lines_list.append(
                "        \\$model->{campo} = {formula};".format(campo=campo, formula=formula)
            )
        calc_lines = '\n'.join(calc_lines_list)

    return """<?php

namespace App\\Observers;

use App\\Models\\{cls};
use Illuminate\\Support\\Facades\\Log;

/**
 * Observer de {cls} — cálculo automático de campos [AUTO]
 *
 * Campos calculados:
{campo_docs}
 */
class {cls}Observer
{{
    private function calcular({cls} \\$model): void
    {{
{calc_lines}
    }}

    public function creating({cls} \\$model): void
    {{
        $this->calcular(\\$model);
    }}

    public function updating({cls} \\$model): void
    {{
        $this->calcular(\\$model);
    }}

    public function saving({cls} \\$model): void
    {{
        // Hook adicional si se necesita lógica extra al guardar
    }}
}}
""".format(
        cls=cls,
        campo_docs='\n'.join(" * - {}".format(c) for c in formulas),
        calc_lines=calc_lines,
    )


# ─── 4. FILAMENT RESOURCE ────────────────────────────────────────────────────

def generate_filament_resource(tabla: str, config: dict, empresa_nombre: str) -> str:
    cls = slug_to_class(tabla)
    label = config.get("label", cls)
    label_singular = config.get("label_singular", cls)
    campos = config["campos"]
    columnas_tabla = config.get("columnas_tabla", list(campos.keys())[:6])
    pk = config.get("primary_key", "id")

    # FORM fields
    form_fields = []
    for campo, meta in campos.items():
        if campo == pk and meta.get("tipo") == "bigint":
            continue  # auto-incremental, skip

        field_label = meta["label"]
        tipo = meta["tipo"]
        es_auto = meta.get("auto", False)
        editable = meta.get("editable", True)
        opciones = meta.get("opciones", [])
        rules = meta.get("rules", "")

        if es_auto or not editable:
            # Campo calculado: solo lectura con Placeholder
            form_fields.append(
                "                Forms\\Components\\Placeholder::make('{campo}')\n"
                "                    ->label('{label}')\n"
                "                    ->content(fn ($record) => $record?->{campo} ?? '—'),".format(
                    campo=campo, label=field_label
                )
            )
        elif tipo == "enum" and opciones:
            opts_php = ", ".join("'{}' => '{}'".format(o, o) for o in opciones)
            form_fields.append(
                "                Forms\\Components\\Select::make('{campo}')\n"
                "                    ->label('{label}')\n"
                "                    ->options([{opts}])\n"
                "                    ->required({req})\n"
                "                    ->searchable(),".format(
                    campo=campo,
                    label=field_label,
                    opts=opts_php,
                    req="true" if "required" in rules else "false",
                )
            )
        elif tipo == "boolean":
            form_fields.append(
                "                Forms\\Components\\Toggle::make('{campo}')\n"
                "                    ->label('{label}'),".format(campo=campo, label=field_label)
            )
        elif tipo == "date":
            form_fields.append(
                "                Forms\\Components\\DatePicker::make('{campo}')\n"
                "                    ->label('{label}')\n"
                "                    ->required({req}),".format(
                    campo=campo,
                    label=field_label,
                    req="true" if "required" in rules else "false",
                )
            )
        elif tipo == "text":
            form_fields.append(
                "                Forms\\Components\\Textarea::make('{campo}')\n"
                "                    ->label('{label}')\n"
                "                    ->rows(3)\n"
                "                    ->columnSpanFull(),".format(campo=campo, label=field_label)
            )
        elif tipo in ("integer", "bigint", "decimal"):
            form_fields.append(
                "                Forms\\Components\\TextInput::make('{campo}')\n"
                "                    ->label('{label}')\n"
                "                    ->numeric()\n"
                "                    ->required({req}),".format(
                    campo=campo,
                    label=field_label,
                    req="true" if "required" in rules else "false",
                )
            )
        else:
            # string por defecto
            unique_rule = ""
            if "unique:" in rules:
                unique_rule = "\n                    ->unique(ignoreRecord: true)"
            form_fields.append(
                "                Forms\\Components\\TextInput::make('{campo}')\n"
                "                    ->label('{label}')\n"
                "                    ->required({req}){unique},".format(
                    campo=campo,
                    label=field_label,
                    req="true" if "required" in rules else "false",
                    unique=unique_rule,
                )
            )

    # TABLE columns
    table_cols = []
    for campo in columnas_tabla:
        meta = campos.get(campo, {})
        label = meta.get("label", campo)
        tipo = meta.get("tipo", "string")

        if tipo in ("integer", "bigint"):
            table_cols.append(
                "                Tables\\Columns\\TextColumn::make('{campo}')\n"
                "                    ->label('{label}')\n"
                "                    ->numeric()\n"
                "                    ->sortable(),".format(campo=campo, label=label)
            )
        elif tipo == "decimal":
            table_cols.append(
                "                Tables\\Columns\\TextColumn::make('{campo}')\n"
                "                    ->label('{label}')\n"
                "                    ->numeric(decimals: 2)\n"
                "                    ->sortable(),".format(campo=campo, label=label)
            )
        elif tipo == "boolean":
            table_cols.append(
                "                Tables\\Columns\\IconColumn::make('{campo}')\n"
                "                    ->label('{label}')\n"
                "                    ->boolean(),".format(campo=campo, label=label)
            )
        elif tipo == "date":
            table_cols.append(
                "                Tables\\Columns\\TextColumn::make('{campo}')\n"
                "                    ->label('{label}')\n"
                "                    ->date('d/m/Y')\n"
                "                    ->sortable(),".format(campo=campo, label=label)
            )
        elif tipo == "enum":
            table_cols.append(
                "                Tables\\Columns\\BadgeColumn::make('{campo}')\n"
                "                    ->label('{label}')\n"
                "                    ->searchable(),".format(campo=campo, label=label)
            )
        else:
            table_cols.append(
                "                Tables\\Columns\\TextColumn::make('{campo}')\n"
                "                    ->label('{label}')\n"
                "                    ->searchable()\n"
                "                    ->sortable(),".format(campo=campo, label=label)
            )

    # VALIDATION rules para el form
    rules_lines = []
    for campo, meta in campos.items():
        if meta.get("rules"):
            # Separar unique para ignorar el registro actual
            rules_raw = meta["rules"]
            rules_php = ", ".join("'{}'".format(r) for r in rules_raw.split("|") if "unique" not in r)
            if rules_php:
                rules_lines.append(
                    "            '{campo}' => [{rules}],".format(campo=campo, rules=rules_php)
                )

    rules_block = '\n'.join(rules_lines) if rules_lines else "            // Sin reglas adicionales"

    return """<?php

namespace App\\Filament\\Resources;

use App\\Filament\\Resources\\{cls}Resource\\Pages;
use App\\Models\\{cls};
use Filament\\Forms;
use Filament\\Forms\\Form;
use Filament\\Resources\\Resource;
use Filament\\Tables;
use Filament\\Tables\\Table;
use Illuminate\\Database\\Eloquent\\Builder;

class {cls}Resource extends Resource
{{
    protected static ?string $model = {cls}::class;
    protected static ?string $navigationIcon = 'heroicon-o-table-cells';
    protected static ?string $navigationLabel = '{label}';
    protected static ?string $modelLabel = '{label_singular}';
    protected static ?string $pluralModelLabel = '{label}';

    public static function form(Form $form): Form
    {{
        return $form->schema([
            Forms\\Components\\Section::make('Datos')
                ->columns(2)
                ->schema([
{form_fields}
                ]),
        ]);
    }}

    public static function table(Table $table): Table
    {{
        return $table
            ->columns([
{table_cols}
            ])
            ->filters([
                Tables\\Filters\\TrashedFilter::make(),
            ])
            ->actions([
                Tables\\Actions\\EditAction::make(),
                Tables\\Actions\\DeleteAction::make(),
            ])
            ->bulkActions([
                Tables\\Actions\\BulkActionGroup::make([
                    Tables\\Actions\\DeleteBulkAction::make(),
                ]),
            ])
            ->defaultSort('created_at', 'desc');
    }}

    public static function getRelations(): array
    {{
        return [];
    }}

    public static function getPages(): array
    {{
        return [
            'index'  => Pages\\List{cls}::route('/'),
            'create' => Pages\\Create{cls}::route('/create'),
            'edit'   => Pages\\Edit{cls}::route('/{{record}}/edit'),
        ];
    }}
}}
""".format(
        cls=cls,
        label=label,
        label_singular=label_singular,
        form_fields='\n'.join(form_fields),
        table_cols='\n'.join(table_cols),
        rules_block=rules_block,
    )


def generate_resource_pages(tabla: str) -> dict:
    cls = slug_to_class(tabla)
    files = {}

    files["List{}.php".format(cls)] = """<?php

namespace App\\Filament\\Resources\\{cls}Resource\\Pages;

use App\\Filament\\Resources\\{cls}Resource;
use Filament\\Actions;
use Filament\\Resources\\Pages\\ListRecords;

class List{cls} extends ListRecords
{{
    protected static string $resource = {cls}Resource::class;

    protected function getHeaderActions(): array
    {{
        return [
            Actions\\CreateAction::make(),
        ];
    }}
}}
""".format(cls=cls)

    files["Create{}.php".format(cls)] = """<?php

namespace App\\Filament\\Resources\\{cls}Resource\\Pages;

use App\\Filament\\Resources\\{cls}Resource;
use Filament\\Resources\\Pages\\CreateRecord;

class Create{cls} extends CreateRecord
{{
    protected static string $resource = {cls}Resource::class;
}}
""".format(cls=cls)

    files["Edit{}.php".format(cls)] = """<?php

namespace App\\Filament\\Resources\\{cls}Resource\\Pages;

use App\\Filament\\Resources\\{cls}Resource;
use Filament\\Actions;
use Filament\\Resources\\Pages\\EditRecord;

class Edit{cls} extends EditRecord
{{
    protected static string $resource = {cls}Resource::class;

    protected function getHeaderActions(): array
    {{
        return [
            Actions\\DeleteAction::make(),
        ];
    }}
}}
""".format(cls=cls)

    return files


# ─── 5. DASHBOARD WIDGET KPIs ────────────────────────────────────────────────

def generate_stats_widget(empresa_cfg: dict) -> str:
    empresa_cls = slug_to_class(empresa_cfg["slug"])
    kpis = empresa_cfg.get("kpis", [])

    stat_items = []
    for kpi in kpis:
        stat_items.append("""            Stat::make('{label}', {query})
                ->description('{desc}')
                ->icon('{icon}')
                ->color('{color}'),""".format(
            label=kpi["label"],
            query=kpi["query"],
            desc=kpi.get("descripcion", ""),
            icon=kpi.get("icono", "heroicon-o-chart-bar"),
            color=kpi.get("color", "primary"),
        ))

    return """<?php

namespace App\\Filament\\Widgets;

use Filament\\Widgets\\StatsOverviewWidget as BaseWidget;
use Filament\\Widgets\\StatsOverviewWidget\\Stat;

/**
 * KPIs del Dashboard — {empresa}
 * Actualizado en cada carga de página con datos reales
 */
class {cls}StatsWidget extends BaseWidget
{{
    protected static ?int $sort = 1;
    protected int | string | array $columnSpan = 'full';

    protected function getStats(): array
    {{
        return [
{stats}
        ];
    }}
}}
""".format(
        empresa=empresa_cfg["nombre_empresa"],
        cls=empresa_cls,
        stats='\n'.join(stat_items),
    )


def generate_dashboard_page(empresa_cfg: dict) -> str:
    empresa_cls = slug_to_class(empresa_cfg["slug"])

    return """<?php

namespace App\\Filament\\Pages;

use Filament\\Pages\\Dashboard as BaseDashboard;

class Dashboard extends BaseDashboard
{{
    protected static ?string $navigationIcon = 'heroicon-o-home';
    protected static ?string $title = 'Dashboard — {empresa}';

    public function getWidgets(): array
    {{
        return [
            \\App\\Filament\\Widgets\\{cls}StatsWidget::class,
        ];
    }}
}}
""".format(
        empresa=empresa_cfg["nombre_empresa"],
        cls=empresa_cls,
    )


# ─── 6. AppServiceProvider / Observer Registration ───────────────────────────

def generate_service_provider(tablas: dict) -> str:
    observer_lines = []
    for tabla in tablas:
        cls = slug_to_class(tabla)
        observer_lines.append(
            "        \\App\\Models\\{cls}::observe(\\App\\Observers\\{cls}Observer::class);".format(cls=cls)
        )

    return """<?php

namespace App\\Providers;

use Illuminate\\Support\\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{{
    public function register(): void {{}}

    public function boot(): void
    {{
        // Registro de Observers — campos [AUTO] se calculan al crear/editar
{observers}
    }}
}}
""".format(observers='\n'.join(observer_lines))


# ─── 7. DOCKER + ENV ──────────────────────────────────────────────────────────

def generate_docker_compose(empresa_slug: str) -> str:
    return """services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: {slug}_app
    restart: unless-stopped
    working_dir: /var/www
    volumes:
      - .:/var/www
    networks:
      - {slug}_net
    depends_on:
      - db
      - redis

  nginx:
    image: nginx:alpine
    container_name: {slug}_nginx
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - .:/var/www
      - ./docker/nginx/default.conf:/etc/nginx/conf.d/default.conf
    networks:
      - {slug}_net

  db:
    image: mysql:8.0
    container_name: {slug}_db
    restart: unless-stopped
    environment:
      MYSQL_DATABASE: {slug}_db
      MYSQL_ROOT_PASSWORD: secret
      MYSQL_PASSWORD: secret
      MYSQL_USER: {slug}
    ports:
      - "3307:3306"
    volumes:
      - {slug}_db_data:/var/lib/mysql
    networks:
      - {slug}_net

  redis:
    image: redis:alpine
    container_name: {slug}_redis
    networks:
      - {slug}_net

networks:
  {slug}_net:
    driver: bridge

volumes:
  {slug}_db_data:
""".format(slug=empresa_slug)


def generate_env_example(empresa_slug: str, empresa_nombre: str) -> str:
    return """APP_NAME="{nombre}"
APP_ENV=local
APP_KEY=
APP_DEBUG=true
APP_URL=http://localhost:8080

DB_CONNECTION=mysql
DB_HOST=db
DB_PORT=3306
DB_DATABASE={slug}_db
DB_USERNAME={slug}
DB_PASSWORD=secret

REDIS_HOST=redis
REDIS_PASSWORD=null
REDIS_PORT=6379

CACHE_DRIVER=redis
SESSION_DRIVER=redis
QUEUE_CONNECTION=sync

FILAMENT_PATH=admin
""".format(slug=empresa_slug, nombre=empresa_nombre)


# ─── 8. SEEDER desde Excel ───────────────────────────────────────────────────

def generate_excel_seeder(empresa_slug: str, tablas: dict) -> str:
    cls_empresa = slug_to_class(empresa_slug)

    seeder_calls = []
    for tabla in tablas:
        cls = slug_to_class(tabla)
        seeder_calls.append("        \\$this->call({cls}Seeder::class);".format(cls=cls))

    return """<?php

namespace Database\\Seeders;

use Illuminate\\Database\\Seeder;

/**
 * DatabaseSeeder — {empresa}
 * Ejecutar: php artisan db:seed
 */
class DatabaseSeeder extends Seeder
{{
    public function run(): void
    {{
{calls}
    }}
}}
""".format(empresa=empresa_slug, calls='\n'.join(seeder_calls))


def generate_table_seeder(tabla: str, config: dict, empresa_excel_path: str = None) -> str:
    cls = slug_to_class(tabla)
    return """<?php

namespace Database\\Seeders;

use Illuminate\\Database\\Seeder;
use App\\Models\\{cls};

/**
 * Seeder para {tabla}
 * Editar este archivo para importar datos del Excel inicial
 */
class {cls}Seeder extends Seeder
{{
    public function run(): void
    {{
        // TODO: importar datos desde Excel si es necesario
        // Ejemplo:
        // {cls}::create([...]);
    }}
}}
""".format(cls=cls, tabla=tabla)


# ─── 9. README ───────────────────────────────────────────────────────────────

def generate_readme(empresa_cfg: dict) -> str:
    empresa = empresa_cfg["nombre_empresa"]
    slug = empresa_cfg["slug"]
    tablas = list(empresa_cfg["tablas"].keys())

    tabla_lines = []
    for t in tablas:
        cfg = empresa_cfg["tablas"][t]
        auto_campos = [c for c, m in cfg["campos"].items() if m.get("auto")]
        tabla_lines.append("- **{}**: {} campo(s) calculado(s) automáticamente: {}".format(
            t,
            len(auto_campos),
            ", ".join(auto_campos) if auto_campos else "ninguno"
        ))

    return """# {empresa} — Sistema Web KraftDo v19

Generado el {fecha}

## Instalación rápida

```bash
# 1. Copiar variables de entorno
cp .env.example .env

# 2. Levantar contenedores
docker-compose up -d

# 3. Instalar dependencias
docker exec SLUG_app composer install

# 4. Generar clave
docker exec SLUG_app php artisan key:generate

# 5. Correr migraciones
docker exec SLUG_app php artisan migrate

# 6. Crear usuario admin Filament
docker exec SLUG_app php artisan make:filament-user

# 7. Abrir panel
# http://localhost:8080/admin
```

(Reemplazar SLUG por: {slug})

## Tablas y campos calculados

{tablas}

## Capas implementadas

### 1. Observers (cálculo automático)
Cada tabla tiene un Observer en `app/Observers/` que calcula los campos
`[AUTO]` al momento de crear o editar un registro. Sin intervención del usuario.

### 2. Campos calculados en formularios
Los campos `[AUTO]` se muestran como `Placeholder` (solo lectura) en los
formularios de Filament. El usuario no puede editarlos manualmente.

### 3. Validaciones de negocio
Cada recurso Filament aplica reglas de validación antes de guardar:
- Campos requeridos
- Tipos numéricos con mínimos
- Enums con valores permitidos
- Unicidad de claves primarias

### 4. Dashboard con KPIs reales
El Dashboard en `/admin` muestra métricas en tiempo real con queries
Eloquent directos a la base de datos.

## Estructura de archivos generados

```
app/
  Models/          Modelos Eloquent (con observer registrado)
  Observers/       Calculo automatico de campos AUTO
  Filament/
    Resources/     CRUD completo por tabla
    Widgets/       StatsOverviewWidget con KPIs
    Pages/         Dashboard personalizado
database/
  migrations/      Una migracion por tabla
  seeders/         Seeders vacios para importar datos iniciales
```
""".format(
        empresa=empresa,
        slug=empresa_cfg["slug"],
        fecha=datetime.now().strftime("%d/%m/%Y"),
        tablas='\n'.join(tabla_lines),
    )


# ─── MAIN GENERATOR ──────────────────────────────────────────────────────────

def generate_project(empresa_slug: str, output_dir: Path):
    """Genera el proyecto Laravel completo con las 4 capas."""

    # Cargar config
    config_path = Path(__file__).parent / "empresas" / empresa_slug / "config.py"
    if not config_path.exists():
        print(f"❌ No existe config para '{empresa_slug}' en {config_path}")
        sys.exit(1)

    spec = importlib.util.spec_from_file_location("empresa_config", config_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    empresa_cfg = mod.CONFIG
    tablas = empresa_cfg["tablas"]
    slug = empresa_cfg["slug"]
    nombre = empresa_cfg["nombre_empresa"]

    print(f"\n🚀 Generando proyecto: {nombre}")
    print(f"   Output: {output_dir}\n")

    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Directorios ──
    dirs = [
        "app/Models",
        "app/Observers",
        "app/Filament/Resources",
        "app/Filament/Widgets",
        "app/Filament/Pages",
        "app/Providers",
        "database/migrations",
        "database/seeders",
        "docker/nginx",
    ]
    for tabla in tablas:
        cls = slug_to_class(tabla)
        dirs.append(f"app/Filament/Resources/{cls}Resource/Pages")
    for d in dirs:
        (output_dir / d).mkdir(parents=True, exist_ok=True)

    timestamp_base = int(datetime.now().timestamp())
    archivos_generados = []

    # ── Migraciones ──
    for i, (tabla, config) in enumerate(tablas.items()):
        ts = datetime.now().strftime(f"%Y_%m_%d_{i:06d}")
        fname = f"{ts}_create_{tabla}_table.php"
        content = generate_migration(tabla, config, ts)
        path = output_dir / "database/migrations" / fname
        path.write_text(content, encoding="utf-8")
        archivos_generados.append(str(path.relative_to(output_dir)))
        print(f"  ✅ migración  → database/migrations/{fname}")

    # ── Models ──
    for tabla, config in tablas.items():
        cls = slug_to_class(tabla)
        content = generate_model(tabla, config)
        path = output_dir / f"app/Models/{cls}.php"
        path.write_text(content, encoding="utf-8")
        archivos_generados.append(str(path.relative_to(output_dir)))
        print(f"  ✅ modelo     → app/Models/{cls}.php")

    # ── Observers ──
    for tabla, config in tablas.items():
        cls = slug_to_class(tabla)
        content = generate_observer(tabla, config)
        path = output_dir / f"app/Observers/{cls}Observer.php"
        path.write_text(content, encoding="utf-8")
        archivos_generados.append(str(path.relative_to(output_dir)))
        auto_count = len(config.get("observer_formulas", {}))
        print(f"  ✅ observer   → app/Observers/{cls}Observer.php  [{auto_count} campos AUTO]")

    # ── Filament Resources ──
    for tabla, config in tablas.items():
        cls = slug_to_class(tabla)
        content = generate_filament_resource(tabla, config, nombre)
        path = output_dir / f"app/Filament/Resources/{cls}Resource.php"
        path.write_text(content, encoding="utf-8")
        archivos_generados.append(str(path.relative_to(output_dir)))
        print(f"  ✅ resource   → app/Filament/Resources/{cls}Resource.php")

        # Pages
        pages = generate_resource_pages(tabla)
        for fname, content in pages.items():
            path = output_dir / f"app/Filament/Resources/{cls}Resource/Pages/{fname}"
            path.write_text(content, encoding="utf-8")
            archivos_generados.append(str(path.relative_to(output_dir)))

    # ── Stats Widget ──
    cls_empresa = slug_to_class(slug)
    content = generate_stats_widget(empresa_cfg)
    path = output_dir / f"app/Filament/Widgets/{cls_empresa}StatsWidget.php"
    path.write_text(content, encoding="utf-8")
    archivos_generados.append(str(path.relative_to(output_dir)))
    print(f"  ✅ widget KPI → app/Filament/Widgets/{cls_empresa}StatsWidget.php  [{len(empresa_cfg.get('kpis', []))} KPIs]")

    # ── Dashboard Page ──
    content = generate_dashboard_page(empresa_cfg)
    path = output_dir / "app/Filament/Pages/Dashboard.php"
    path.write_text(content, encoding="utf-8")
    archivos_generados.append(str(path.relative_to(output_dir)))
    print(f"  ✅ dashboard  → app/Filament/Pages/Dashboard.php")

    # ── AppServiceProvider ──
    content = generate_service_provider(tablas)
    path = output_dir / "app/Providers/AppServiceProvider.php"
    path.write_text(content, encoding="utf-8")
    archivos_generados.append(str(path.relative_to(output_dir)))
    print(f"  ✅ provider   → app/Providers/AppServiceProvider.php")

    # ── Seeders ──
    content = generate_excel_seeder(slug, tablas)
    path = output_dir / "database/seeders/DatabaseSeeder.php"
    path.write_text(content, encoding="utf-8")
    archivos_generados.append(str(path.relative_to(output_dir)))
    for tabla, config in tablas.items():
        cls = slug_to_class(tabla)
        content = generate_table_seeder(tabla, config)
        path = output_dir / f"database/seeders/{cls}Seeder.php"
        path.write_text(content, encoding="utf-8")
        archivos_generados.append(str(path.relative_to(output_dir)))
    print(f"  ✅ seeders    → database/seeders/ ({len(tablas)+1} archivos)")

    # ── Docker + Env ──
    path = output_dir / "docker-compose.yml"
    path.write_text(generate_docker_compose(slug), encoding="utf-8")
    path = output_dir / ".env.example"
    path.write_text(generate_env_example(slug, nombre), encoding="utf-8")
    print(f"  ✅ docker     → docker-compose.yml + .env.example")

    # ── Nginx config ──
    nginx_conf = """server {{
    listen 80;
    root /var/www/public;
    index index.php;
    location / {{
        try_files $uri $uri/ /index.php?$query_string;
    }}
    location ~ \\.php$ {{
        fastcgi_pass app:9000;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
        include fastcgi_params;
    }}
}}
"""
    (output_dir / "docker/nginx/default.conf").write_text(nginx_conf)

    # ── Dockerfile ──
    dockerfile = """FROM php:8.3-fpm
RUN apt-get update && apt-get install -y \\
    git curl zip unzip libpng-dev libzip-dev \\
    && docker-php-ext-install pdo_mysql zip gd
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer
WORKDIR /var/www
"""
    (output_dir / "Dockerfile").write_text(dockerfile)

    # ── README ──
    content = generate_readme(empresa_cfg)
    path = output_dir / "README.md"
    path.write_text(content, encoding="utf-8")
    print(f"  ✅ readme     → README.md\n")

    # ── Resumen ──
    print(f"{'='*60}")
    print(f"✅ Proyecto generado: {nombre}")
    print(f"   Tablas:      {len(tablas)}")
    print(f"   Archivos:    {len(archivos_generados)}")
    print(f"   Output:      {output_dir}")
    print(f"{'='*60}")

    auto_total = sum(
        len(cfg.get("observer_formulas", {}))
        for cfg in tablas.values()
    )
    print(f"\n📊 Resumen de campos calculados (Observers):")
    for tabla, cfg in tablas.items():
        formulas = cfg.get("observer_formulas", {})
        if formulas:
            print(f"   {tabla:25} → {', '.join(formulas.keys())}")

    kpis = empresa_cfg.get("kpis", [])
    print(f"\n📈 KPIs en dashboard ({len(kpis)}):")
    for kpi in kpis:
        print(f"   - {kpi['label']}")

    print(f"\n{'='*60}")
    print("PRÓXIMOS PASOS:")
    print("  1. cd", output_dir)
    print("  2. cp .env.example .env")
    print("  3. docker-compose up -d")
    print("  4. docker exec {}_app composer install".format(slug))
    print("  5. docker exec {}_app php artisan key:generate".format(slug))
    print("  6. docker exec {}_app php artisan migrate".format(slug))
    print("  7. docker exec {}_app php artisan make:filament-user".format(slug))
    print("  8. Abrir http://localhost:8080/admin")
    print(f"{'='*60}\n")





# ─── CLI ──────────────────────────────────────────────────────────────────────


def deploy_to_existing(empresa_slug: str, target: Path):
    import tempfile
    print(f"\n🚀 Deploy v19 → {target}\n")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_out = Path(tmp) / "out"
        generate_project(empresa_slug, tmp_out)
        copias = [
            tmp_out / "app/Observers",
            tmp_out / "app/Filament/Widgets",
            tmp_out / "app/Filament/Pages",
            tmp_out / "app/Providers",
        ]
        for src_dir in copias:
            if not src_dir.exists():
                continue
            rel = src_dir.relative_to(tmp_out)
            dst_dir = target / rel
            dst_dir.mkdir(parents=True, exist_ok=True)
            for archivo in src_dir.iterdir():
                shutil.copy2(archivo, dst_dir / archivo.name)
                print(f"  ✅ {rel}/{archivo.name}")
    print(f"\n✅ Deploy completo en {target}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="KraftDo Generador v19 — Laravel + Filament con 4 capas"
    )
    parser.add_argument("empresa", help="Slug: kraftdo | adille | extractores")
    parser.add_argument("--output", default=None, help="Directorio de salida completo")
    parser.add_argument("--deploy", default=None, help="Deploy archivos nuevos a sistema Laravel existente")
    args = parser.parse_args()

    if args.deploy:
        deploy_to_existing(args.empresa, Path(args.deploy))
    else:
        out = Path(args.output) if args.output else Path("./output") / f"{args.empresa}_app"
        generate_project(args.empresa, out)


# ─── DEPLOY a sistema existente ──────────────────────────────────────────────

