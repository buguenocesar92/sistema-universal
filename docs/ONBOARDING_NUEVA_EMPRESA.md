# Onboarding — agregar una empresa nueva al sistema universal

Esta guía describe cómo añadir una empresa al generador. Asume que ya
tienes el repo clonado y los 3 sistemas existentes (`kraftdo_bd`, `adille`,
`extractores`) funcionando como referencia.

---

## 1. Qué necesita el Excel para que funcione bien

El archivo Excel es la fuente de verdad. Debe cumplir:

- **Formato**: `.xlsx` (OpenXML).
- **Una hoja por entidad**: catálogos (productos, clientes, proveedores) +
  hojas de transacciones (pedidos, ventas, caja). Si la hoja contiene varias
  tablas concatenadas (`multi_tabla`) o headers en 2 filas (`multi_header`),
  el sistema lo detecta y advierte (ver `normalizer.py`); idealmente, separa
  los bloques en hojas distintas antes de mapear.
- **Headers consistentes**: la fila inmediatamente anterior a `fila_datos`
  debe tener los nombres de columna. Las primeras N filas pueden ser título
  de la hoja, instrucciones o totales — `fila_datos` apunta a la primera
  fila de datos reales.
- **Identificador estable**: cada hoja necesita una columna que sirva como
  identificador (`sku`, `id`, `n_pedido`, etc.) o un valor textual único
  como nombre/concepto. Las filas con identificador vacío se descartan
  durante la importación; las filas continuación heredan el último
  identificador (útil para sub-líneas de un pedido).
- **Valores limpios**: filas con texto tipo `TOTAL`, `SUBTOTAL`, `[AUTO]`,
  `[INGRESAR]`, `AMARILLO` en el identificador se descartan automáticamente.
  Las filas cuyo identificador empieza con `=` (notas a pie con fórmula) o
  cuyo largo > 50 caracteres también se filtran.

Si una columna del Excel tiene varios "alias" del mismo valor (`25W`,
`EXT-25W`, `25w`), declárala en `sinonimos_modelo` para canonizar.

---

## 2. Crear el JSON de configuración paso a paso

### Paso 1 — esqueleto mínimo

`empresas/mi_empresa.json`:

```json
{
  "empresa": {
    "nombre": "Mi Empresa SpA",
    "rut": "",
    "email": "admin@mi-empresa.cl",
    "color_primary": "1A1A2E",
    "color_accent":  "E94560"
  },
  "fuente": {
    "tipo": "local",
    "archivo": "empresas/mi_empresa.xlsx"
  },
  "logica_negocios": {
    "iva": 0.19,
    "moneda": "CLP"
  },
  "hojas": {}
}
```

Coloca el Excel en `empresas/mi_empresa.xlsx`.

### Paso 2 — mapear cada hoja

Por cada hoja del Excel agrega una entrada bajo `hojas`. Cuatro tipos:

#### `catalogo` — tablas de referencia (productos, proveedores)
```json
"productos": {
  "nombre":      "Productos NFC",
  "tipo":        "catalogo",
  "fila_datos":  5,
  "columnas": {
    "sku":          "A",
    "categoria":    "B",
    "nombre":       "C",
    "costo_insumo": "E",
    "hora_trabajo": "F",
    "costo_total":  "G",
    "precio_unit":  "H"
  },
  "identificador": "sku"
}
```

#### `registros` — transacciones
```json
"pedidos": {
  "nombre":      "Pedidos",
  "tipo":        "registros",
  "fila_datos":  5,
  "columnas": {
    "n_pedido":  "A",
    "fecha":     "B",
    "cliente":   "C",
    "sku":       "F",
    "cantidad":  "I",
    "precio_unit":"J"
  },
  "identificador":     "n_pedido",
  "formato_id":        "MIEMP-{:03d}",
  "campos_accessor":   ["whatsapp", "ciudad"],
  "snapshot_at_create": ["precio_unit", "categoria"]
}
```

Capacidades opcionales sobre `registros`:
- `formato_id: "PREFIJO-{:03d}"` → genera el siguiente ID al crear.
- `campos_accessor: [...]` → expone campos del padre como accessors
  (`getWhatsappAttribute`), sin columna física. NO los pongas en
  `columnas`.
- `snapshot_at_create: [...]` → al crear, congela en este registro
  los campos indicados copiados del padre. Strings o dicts:
  `{ "campo": "f_entrega", "desde": "sku", "campo_padre": "tiempo_produccion", "fn": "fecha_plus_dias", "base": "fecha" }`.

#### `agregado` — datos derivados de otras hojas vía SUM
```json
"stock": {
  "nombre":      "Control Stock",
  "tipo":        "agregado",
  "fila_datos":  5,
  "columnas": {
    "modelo":          "B",
    "importacion":     "C",
    "ventas":          "D",
    "promociones":     "E",
    "stock_disponible":"F"
  },
  "identificador": "modelo",
  "agrupar_por":   "modelo",
  "fuentes": [
    { "hoja": "importaciones", "campo_grupo": "modelo", "campo_valor": "unidades", "destino": "importacion" },
    { "hoja": "ventas",        "campo_grupo": "modelo", "campo_valor": "cantidad", "destino": "ventas" },
    { "hoja": "promociones",   "campo_grupo": "modelo", "campo_valor": "cantidad", "destino": "promociones" }
  ]
}
```

El generator crea `Stock::recalcularModelo($valor)` y observers en cada hoja
fuente que la disparan al guardar/borrar. La cascada es en tiempo real.

Si los códigos de modelo varían entre hojas (`25W` en importaciones,
`EXT-25W` en ventas), añade `sinonimos_modelo` al nivel raíz del JSON:
```json
"sinonimos_modelo": {
  "25W": ["EXT-25W", "25w"],
  "60W": ["EXT-60W", "60w"]
}
```
El importer canoniza al insertar y todas las hojas convergen al canónico.

#### `matriz_asistencia` — matriz pivotada (trabajador × día)
```json
"control_personal": {
  "tipo":                 "matriz_asistencia",
  "nombre":               "CONTROL PERSONAL",
  "fila_inicio":          5,
  "fila_fin":             18,
  "col_codigo_obra":      "B",
  "col_obra":             "C",
  "col_trabajador":       "D",
  "cols_quincena1":       ["E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S"],
  "col_pago_quincena":    "T",
  "cols_quincena2":       ["U","V","W","X","Y","Z","AA","AB","AC","AD","AE","AF","AG"],
  "col_pago_liquidacion": "AH",
  "mes_actual":           "2026-03"
}
```
Genera tablas `asistencias` y `pagos_quincena`, modelos, Resources Filament
y una página pivotada interactiva en `/admin/matriz-asistencia` (celdas
clickeables con ciclo `· → A → F → L → ·`).

Para que `liquidacion` lea de estas tablas declara en su hoja:
```json
"auto_aggregate": [
  { "campo": "dias_trabajados", "modelo": "Asistencia",   "where_match": ["trabajador"], "where_extra": [["mes","2026-03"],["estado","A"]], "fn": "count" },
  { "campo": "faltas",          "modelo": "Asistencia",   "where_match": ["trabajador"], "where_extra": [["mes","2026-03"],["estado","F"]], "fn": "count" },
  { "campo": "quincena_pagada", "modelo": "PagoQuincena", "where_match": ["trabajador"], "where_extra": [["mes","2026-03"]],                "fn": "sum:monto" }
]
```

### Paso 3 — KPIs custom del dashboard

```json
"logica_negocios": {
  "iva": 0.19,
  "moneda": "CLP",
  "kpis_custom": [
    { "label": "Pedidos del mes", "modelo": "Pedido", "agregacion": "count",
      "where": [["fecha", ">=", "today"]], "color": "warning", "formato": "numero",
      "descripcion": "Pedidos desde hoy" },
    { "label": "Saldo Caja", "modelo": "Caja", "agregacion": "sum:monto",
      "color": "success", "formato": "moneda", "descripcion": "Suma de movimientos" }
  ]
}
```
`agregacion` puede ser `count`, `sum:campo`, `avg:campo`. `formato`:
`numero` o `moneda`. El literal `"today"` en `where` se traduce a
`now()->startOfDay()`.

---

## 3. Generar y verificar

```bash
cd ~/Dev/sistema-universal
python3 generator.py mi_empresa --output /tmp/mi_empresa_test
```

El generator hace:
1. `composer create-project laravel/laravel` (la primera vez).
2. Instala Filament y configura `.env` con MySQL local.
3. Genera todos los archivos PHP.
4. Crea la BD `mi_empresa` en MySQL (host 127.0.0.1, port 3307, user `kraftdo`).
5. Ejecuta `php artisan migrate:fresh`.
6. Crea usuario admin (email del JSON, password `kraftdo2026`).
7. Importa el Excel a la BD.
8. Corre `php artisan kraftdo:recalcular` para que los observers
   procesen los datos importados (snapshots, aggregates, cascadas).
9. Imprime el puerto único asignado (`8080 + hash(empresa) % 900`) y la URL.

Levanta el panel:
```bash
cd /tmp/mi_empresa_test
php artisan serve --host=0.0.0.0 --port=$PUERTO
```

O añade `mi_empresa` al loop de `levantar.sh` y úsalo.

---

## 4. Iterar

Si algo no calza:
- Re-ejecuta `python3 generator.py mi_empresa --output /tmp/mi_empresa_test`. Sobrescribe los archivos generados sin recrear la base Laravel (que es lenta).
- Para regenerar desde cero borra `/tmp/mi_empresa_test` y vuelve a correr.
- Ejecuta `php artisan kraftdo:recalcular` después de importar si modificaste reglas de cálculo o agregaciones.
- Si un Resource da error 500 al cargar, revisa Laravel logs en
  `storage/logs/laravel.log`.

---

## 5. Lista de verificación antes de dar el panel al cliente

- [ ] El Excel está en `empresas/{empresa}.xlsx` y el JSON apunta ahí en `fuente.archivo`.
- [ ] Cada hoja tiene `identificador` y `fila_datos` correctos.
- [ ] Las letras de columna en `columnas` coinciden con el Excel real (probar con openpyxl si hay duda — un off-by-one es muy común).
- [ ] Si hay sinónimos de modelo entre hojas, declarados en `sinonimos_modelo`.
- [ ] Los campos calculados (`costo_total`, `precio_unit`, `iva`, etc.) están en `columnas` para que existan como columnas de DB; el observer los rellenará.
- [ ] El identificador de un padre (ej. `clientes.identificador`) es la natural key real (lo que VLOOKUP busca en el Excel) — no `id` numérico si las referencias son por nombre.
- [ ] Tras `kraftdo:recalcular`, los datos importados tienen los campos derivados llenos.
- [ ] HTTP 200 en `/admin/login`. El login funciona con `password=kraftdo2026`.
- [ ] El widget del dashboard muestra los KPIs custom y el conteo por hoja.
- [ ] Los SelectFilter, búsqueda global y export CSV funcionan.

---

## 6. Comandos de referencia rápida

```bash
# Generar
python3 generator.py mi_empresa --output /tmp/mi_empresa_test

# Generar solo una capa (útil al iterar)
python3 generator.py mi_empresa --output /tmp/mi_empresa_test --solo modelos
python3 generator.py mi_empresa --output /tmp/mi_empresa_test --solo observers
python3 generator.py mi_empresa --output /tmp/mi_empresa_test --solo filament

# Preview sin escribir
python3 generator.py mi_empresa --preview

# Forzar recálculo (dispara observers)
cd /tmp/mi_empresa_test && php artisan kraftdo:recalcular

# Levantar todos los paneles
~/Dev/sistema-universal/levantar.sh
```

Para más contexto sobre la arquitectura, ver `CLAUDE.md` en la raíz.
