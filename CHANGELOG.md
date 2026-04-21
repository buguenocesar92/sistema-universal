# Changelog — KraftDo Sistema Universal

Todas las versiones siguen [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

---

## [v17] — 2026-03-31 — Herramientas inteligentes

### Agregado
- **Pandas** en `AdaptadorLocal` — carga Excel con cache por mtime, 10-100x más rápido en archivos grandes
- **DuckDB** en `buscar_filtros` — SQL real sobre cualquier hoja. Nuevo método `query(alias, sql_where)`
- **Endpoint `/query/{alias}`** — SQL directo desde la API REST
- **Pydantic v2** en `importer.py` — validación tipada de cada fila antes de insertar
- **Instructor** en `classifier.py` — respuestas tipadas de Claude en la Fase 0
- **SQLGlot** en `differ.py` — validación de nombres de columna antes de generar ALTER TABLE
- **Prefect** (`pipeline.py`) — 6 flows: sync, validar, generar, backup, sync_periodico, notificar
- **MinIO** en `docker-compose.yml` — backups automáticos versionados con consola web
- **Filament Excel** en generator — ExportAction en cada Resource (exportar a .xlsx con un clic)
- **Filament Shield, Charts, Media** en `install.sh`
- **normalizer → generator** conectados — advierte sobre patrones raros al generar
- Documentación técnica completa (20 secciones, tablas de referencia, FAQ)
- `.gitignore` y `CHANGELOG.md`
- GitHub Actions CI/CD (`tests.yml`)

### Corregido
- `gen_filament_resource` reescrito sin f-strings — 0 SyntaxWarnings
- `AdaptadorLocal.filas()` usaba Pandas incorrectamente como header — datos vacíos en Proveedores
- `gen_filament_resource` no recibía `empresa_cfg` ni `rels` — TypeError al generar

---

## [v16] — 2026-03-31 — 0 SyntaxWarnings

### Corregido
- `gen_filament_resource` tenía backslashes PHP en f-strings → 1 SyntaxWarning restante
- Reescritura completa de la función usando concatenación pura
- Bug `filas()` de Pandas: usaba `fila_inicio` como fila de headers → 0 filas retornadas
- `gen_filament_resource()` llamada sin argumentos requeridos

---

## [v15] — 2026-03-31 — Soporte completo Google Sheets

### Corregido
- **Bug crítico Sheets**: `sheets_id` se leía ANTES de aplicar `SHEETS_ID` del entorno → siempre modo local
- Fallback silencioso si Sheets no está disponible (sin crashear)
- `normalizer.py` solo funcionaba con Excel local — agregado `analizar_sheets_completo()` y `analizar_fuente()`

### Agregado
- Tests de regresión para Sheets (`TestSheets`: 6 tests)
- `analizar_fuente(sistema)` como punto de entrada unificado para normalizar cualquier fuente

---

## [v14] — 2026-03-31 — 5 bugs críticos corregidos

### Corregido
- **Bug 1 (crítico)**: `importar_hoja_consolidada` buscaba hojas fuente en el JSON consolidado donde ya no existen — ahora carga el JSON original del disco
- **Bug 2**: `_slug()` perdía tildes (`Sublimación` → `sublimaci_n`) — normalización unicode con NFKD
- **Bug 3**: Doble upload en classifier — `/normalizar` ahora acepta `filename` para reusar archivo ya subido
- **Bug 4**: Migración consolidada generaba `string('tipo')` en lugar de `enum('tipo', [...])`  
- **Bug 5**: `differ.py` fallaba si se ejecutaba desde otro directorio — agrega `SCRIPT_DIR` al `sys.path`

---

## [v13] — 2026-03-31 — Normalización y consolidación

### Agregado
- `normalizer.py` — detecta 8 patrones de Excel (horizontal, multi-header, formulario, multi-tabla, sparse, con_totales)
- `consolidator.py` — agrupa hojas en entidades únicas con campo `tipo` discriminador
- Fase 0 en `classifier.py` — textarea descripción negocio + Claude sugiere consolidaciones
- UI de consolidación visual en el classifier (paso entre clasificar y generar)
- `analizar_sheets_completo()` para Google Sheets
- Tests para normalizer (8) y consolidator (8)

---

## [v12] — 2026-03-31 — CRUD completo sobre Excel/Sheets

### Agregado
- `core.py`: métodos `crear()`, `actualizar()`, `eliminar()`, `buscar_filtros()`, `schema()`, `query()`
- `AdaptadorLocal`: `append_fila()`, `update_fila()`, `delete_fila()`
- `AdaptadorSheets`: `append_fila()`, `update_fila()`, `delete_fila()`
- Endpoints POST, PUT, DELETE en `api.py`
- GET con filtros dinámicos en query params (`?estado=Activo&total__gt=50000`)
- Formularios dinámicos HTML en `classifier.py` (`/form/{empresa}/{alias}`)
- Rate limiting con Redis + fallback en memoria
- `--dry-run` en `importer.py` con validación por campo
- Modo `--watch` en `differ.py` — detecta cambios automáticamente

---

## [v11] — 2026-03-31 — Sistema completo de punta a punta

### Agregado
- `setup.sh` — instalación completa de cero en Ubuntu con variables auto-generadas
- Workflow El Pilar (`el_pilar_apoderados.json`) — formulario apoderados → Notion → Gmail → Telegram
- `kraftdo.py` CLI unificado con todos los comandos y colores
- 50 tests en la suite

### Corregido
- Doble upload en classifier
- Búsqueda `__in` sin `strip()` en cada valor

---

## [v10] — 2026-03-31 — Módulos adicionales

### Agregado
- `relations.py` — detecta `belongsTo` y `hasMany` automáticamente
- `formula_parser.py` — convierte fórmulas Excel a PHP accessors
- `n8n_generator.py` — 3 workflows (bot, alertas, reporte)
- `differ.py` — detecta cambios JSON y genera ALTER TABLE
- `classifier.py` con plantillas por nombre de hoja e historial automático
- 40 tests

### Corregido
- `classifier.py` usaba Flask en lugar de FastAPI (migrado)

---

## [v9] — 2026-03-31 — Sistema universal

### Agregado
- `classifier.py` — UI web para clasificar hojas y generar JSON
- `importer.py` — importa Excel → MySQL con dry-run
- Formularios dinámicos desde el schema del JSON
- Docker completo con Nginx + SSL + n8n + MySQL + Redis
- `docker-compose.yml`, `Dockerfile.api`, `Dockerfile.laravel`

---

## [v8] — 2026-03-31 — Google Sheets + API completa

### Agregado
- `AdaptadorSheets` con gspread
- Endpoints API: GET catálogo, precio, cotizar, registros, KPIs
- Autenticación por API key
- Modo `--preview` en importer

---

## [v7] — 2026-03-31 — Base del sistema

### Primer release
- `core.py` — lector Excel/Sheets universal
- `api.py` — FastAPI básico con catálogo y cotizador
- `generator.py` — genera código Laravel+Filament
- `empresas/kraftdo.json` — primera empresa configurada
