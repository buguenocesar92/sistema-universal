# KraftDo Sistema Universal — v24b

## Qué es
Generador Python que convierte Excel de PYMEs en paneles Laravel + Filament 4.
Un comando produce un proyecto Laravel completo con migraciones, modelos, observers, Filament Resources, FormRequests, Seeders, API REST, dashboard y comandos artisan, todo a partir de un JSON por empresa que mapea las hojas del Excel.

## Empresas activas
| Empresa | Panel | Login |
|--|--|--|
| KraftDo | http://192.168.1.11:8385/admin | hola@kraftdo.cl / kraftdo2026 |
| Adille | http://192.168.1.11:8467/admin | contacto@adille.cl / kraftdo2026 |
| Extractores | http://192.168.1.11:8397/admin | ventas@extractoreschile.cl / kraftdo2026 |

## Comandos clave
```bash
python3 generator.py kraftdo_bd  --output /tmp/kraftdo_bd_test
python3 generator.py adille      --output /tmp/adille_test
python3 generator.py extractores --output /tmp/extractores_test
~/Dev/sistema-universal/levantar.sh                # levanta los 3 paneles
php artisan kraftdo:recalcular                     # fuerza recálculo (dispara observers)
```

## Capas que genera (en orden)

### 1. Migraciones (`database/migrations/*.php`)
Inferencia de tipos por nombre vía `REGLAS_TIPO`: timestamp/decimal/integer/text/string. `decimal(15,2)` para montos; `decimal(5,4)` solo para `^margen$`/`_pct`/`porcentaje`. Índices automáticos en fecha/estado/sku/email/etc.

### 2. Modelos (`app/Models/*.php`)
- `$table`, `$fillable`, `$casts` desde el JSON.
- `$appends` para `campos_accessor`.
- `scopeActivos()` si la hoja tiene `estado` con valores activos definidos.
- Relaciones `belongsTo`/`hasMany` desde `relations.detectar_relaciones`. **Sufijo `Rel` cuando colisionan con la columna FK** (ej. campo `cliente` → método `clienteRel()`).
- Accessors de fórmulas Excel (`getXxxComputedAttribute`) desde `formula_parser`.
- Accessors `campos_accessor` (vista lateral, sin DB): `getWhatsappAttribute()` lee desde el padre.
- `#[ObservedBy([...])]` cuando hay observer.
- Método estático `recalcularModelo($valor)` para hojas `tipo: agregado`.

### 3. Observers (`app/Observers/*.php`)
Generado por `gen_observer()` cuando aplica al menos uno de:
- **Reglas de cálculo declarativas** (`REGLAS_CALCULO`) — fórmulas PHP con deps; ej. `costo_total = costo_insumo + hora_trabajo`.
- **`formato_id`** auto-numeración — `creatingAutoId()` busca el máximo sufijo numérico y emite el siguiente. Ej. `KDO-{:03d}`.
- **`snapshot_at_create`** — `creatingSnapshot()` carga el padre vía FK y copia campos. NO toca en `update` (preserva histórico). Soporta `fn: fecha_plus_dias`.
- **`auto_aggregate`** — `aggregate()` rellena campos desde `count`/`sum:campo`/`avg:campo` con `where_match` (copia del modelo) + `where_extra` (literales). Corre antes de `recalcular()`.
- **Cascada agregada** — hooks `saved/deleted` que invocan `Stock::recalcularModelo($model->modelo)` en hojas que son fuente de un agregado.

### 4. Filament Resources (`app/Filament/Resources/*.php`)
- Form: 10 primeros campos, excluye `id`/calculados/auto.
- Inputs: `Select` (estado/enum auto/FK), `DatePicker` con `displayFormat('d/m/Y')`, `TextInput numeric prefix('$')` para `CAMPOS_MONEDA`.
- `Placeholder` readonly para campos calculados.
- Tabla: `money('clp', locale: 'es_CL')`, `date('d/m/Y')`, `badge()` para enums/estado.
- Filtros: `SelectFilter` por estado/enum (con `->filter()->toArray()` para evitar nulls), `Filter` con dos DatePicker (rango) por fecha.
- `getGloballySearchableAttributes()` con los primeros 3 campos string.
- Pages: `ListXxx` con `CreateAction` + Export CSV nativo (`streamDownload`, BOM UTF-8, separador `;`).

### 5. FormRequests
- `required` en identificador.
- Calculados (observer) excluidos.
- `numeric|min:0`, `date`, `boolean`, `email|max:255`, `in:val1,val2` para enum/estado.

### 6. Seeders
Datos fake con Faker, contextual al nombre del campo (nombre/cliente/email/etc).

### 7. API REST (`app/Http/Controllers/Api/*.php` + `routes/api.php`)
`apiResource` por tabla con FormRequest.

### 8. Widget de KPIs
Orden: KPIs custom (`cfg.logica_negocios.kpis_custom`) → stock crítico (`stock|cantidad|disponible < 5` color danger) → conteo + sum financiero por hoja.

### 9. Comando `kraftdo:recalcular`
Itera modelos con observer, fuerza dirty (`updated_at = now()`) y `save()` para que aggregates/snapshots/cascadas corran sobre datos importados. Se ejecuta tras importar Excel.

### 10. Tablas auxiliares de `matriz_asistencia` (solo si la empresa la define)
Cuando una hoja tiene `tipo: matriz_asistencia`, además se generan:
- Migrations + modelos `Asistencia` y `PagoQuincena`.
- Resources Filament básicos (CRUD).
- **`app/Filament/Pages/MatrizAsistencia.php` + Blade** — vista pivotada interactiva: trabajadores × días, celdas clickeables que ciclan `· → A → F → L → ·` con `wire:click="toggleAsistencia($trab, $dia)"`.

## Arquitectura del `generator.py` (~1500 líneas)

| Función | Propósito |
|--|--|
| `inferir_tipo(nombre)` | Mapea nombre de campo → (tipo Laravel, modificador) por regex. |
| `nombre_tabla / nombre_modelo` | Convenciones snake/Pascal singular. |
| `_calculos_aplicables(cols)` | Filtra `REGLAS_CALCULO` por columnas presentes. |
| `_nombre_relacion_php(campo_origen)` | Espeja la lógica de `relations.gen_eloquent_relationships` (rstrip `s`, añade `Rel` si no cambió). |
| `_resolver_accessor(campo, alias, hojas, rels)` | Para `campos_accessor`/`snapshot_at_create` strings: encuentra qué FK y qué columna del padre usar. Prioriza FK cuyo padre singular = nombre del campo. |
| `_resolver_snapshot(item, ...)` | Acepta string o dict (`campo`, `desde`, `campo_padre`, `fn`, `base`). |
| `_detectar_enums_excel(excel, cfg)` | Lee Excel, detecta cols string con 2..7 valores únicos. Excluye `NO_ENUM` y `CAMPOS_MONEDA`. |
| `gen_migracion`, `gen_modelo`, `gen_observer`, `gen_filament_resource`, `gen_form_request`, `gen_seeder`, `gen_filament_pages`, `gen_filament_widget`, `gen_recalcular_command`, `gen_install_script` | Generadores por capa. |
| `gen_metodo_recalcular_modelo(...)` | Genera el método estático `recalcularModelo()` para hojas `tipo: agregado`. |
| `gen_archivos_matriz_asistencia(idx_base, matriz_cfg)` | Genera todos los archivos de la matriz: migrations, modelos, Resources, Page pivot, Blade. |
| `_crear_base_laravel(output_dir, empresa, cfg)` | `composer create-project laravel/laravel`, instala Filament, configura `.env` con MySQL local. |
| `generar(empresa, output_dir, preview, solo)` | Orquestador principal. |

## JSONs por empresa (`empresas/*.json`)

```json
{
  "empresa": { "nombre", "rut", "email", "color_primary", "color_accent" },
  "fuente":  { "tipo": "local", "archivo": "empresas/X.xlsx" },
  "logica_negocios": {
    "iva": 0.19, "moneda": "CLP",
    "kpis_custom": [...]
  },
  "sinonimos_modelo": {
    "25W": ["EXT-25W", "25w"]
  },
  "hojas": {
    "alias": {
      "nombre": "Hoja del Excel",
      "tipo": "registros|catalogo|agregado|matriz_asistencia|kpis|consolidado",
      "fila_datos": 5,
      "columnas": { "campo": "B", ... },
      "identificador": "campo",

      "formato_id": "KDO-{:03d}",
      "campos_accessor": ["whatsapp", "ciudad"],
      "snapshot_at_create": ["precio_unit", {...}],
      "auto_aggregate": [...],
      "agrupar_por": "modelo",
      "fuentes": [{...}]
    }
  }
}
```

Diferencias por empresa:
- **kraftdo_bd**: pedidos con `formato_id` + `campos_accessor` + `snapshot_at_create`. `kpis_custom` con 3 ejemplos.
- **adille**: liquidacion con `auto_aggregate` que lee de Asistencia/PagoQuincena. control_personal con `tipo: matriz_asistencia`.
- **extractores**: stock con `tipo: agregado` + fuentes desde importaciones/ventas/promociones. `sinonimos_modelo` para normalizar 25W/EXT-25W/25w → 25W canónico.

## Reglas críticas (NO romper)

- **Filament 4** actualmente (`composer require filament/filament:^4.0`).
- **Modelos en SINGULAR** (`Producto`, `Cliente`, `Pedido`).
- **`$model` SIN backslash** en typehint de Observers.
- **NO tocar `/tmp/{empresa}_test` directamente** — regenerar con `generator.py`.
- **Excel en `empresas/X.xlsx`** — la ruta va en el JSON (`fuente.archivo`).
- **Relaciones con sufijo `Rel`** cuando colisionan con la columna FK. Cualquier código que use `$model->{nombre}()` debe pasar por `_nombre_relacion_php()`.
- **`decimal(15,2)` para campos monetarios**, NO `decimal(5,4)` (eso solo para `^margen$|_pct|porcentaje`).
- **Sinónimos canónicos en hojas `tipo: agregado`** — sus fuentes deben canonizar el `campo_grupo` para que las cascadas converjan a una sola fila por canónico.
- **El observer no dispara sobre records limpios** — `kraftdo:recalcular` setea `updated_at = now()` antes de `save()`.

## Archivos importantes
- `generator.py` — generador principal (v24b)
- `relations.py` — detección de FKs
- `formula_parser.py` — fórmulas Excel → accessors PHP
- `consolidator.py` — soporte hojas `tipo: consolidado`
- `normalizer.py` — análisis de patrones de hojas (multi_header, multi_tabla)
- `importar_excel_a_mysql.py` — importer con sinónimos y despivot de matriz
- `empresas/*.json` — config por empresa
- `empresas/*.xlsx` — Excel fuente
- `levantar.sh` — levanta los 3 paneles
- `docs/ONBOARDING_NUEVA_EMPRESA.md` — guía para añadir empresas

## Versiones
- v18 — base estable
- v19 — observers + KPI widgets básicos
- v20 — enums auto + relaciones por nombre + formato CLP + comando recalcular
- v21 — stock crítico + filtros + global search + export CSV + KPIs custom
- v22 — fix `decimal(5,4)`, importer pierde-filas, `formato_id`, JSONs faltantes
- v23 — accessors VLOOKUP, snapshot_at_create, cascada agregada
- v24 — sinónimos canónicos, matriz_asistencia, auto_aggregate
- v24b — vista pivotada interactiva de asistencia
