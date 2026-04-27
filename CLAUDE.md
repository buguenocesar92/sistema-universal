# KraftDo Sistema Universal — v24b

## Arquitectura y Capacidades
Sistema de generación de software basado en metadatos (JSON) que transforma estructuras de Excel en aplicaciones empresariales Laravel + Filament.

- **Capa de Datos**: Modelos Eloquent con tipado estricto, casts automáticos y scopes de negocio.
- **Capa de Lógica (Observers)**: Automatización de cálculos, snapshots de datos históricos y mantenimiento de integridad referencial.
- **Capa de Agregación**: Recálculo en cascada (`_cascadas`) y agregaciones automáticas (`auto_aggregate`) para KPIs en tiempo real.
- **Capa de Interfaz**: Generación dinámica de Filament Resources, incluyendo la nueva **Matriz de Asistencia** interactiva y vistas pivotadas.
- **Capa de Integración**: API REST auto-generada y sincronización bidireccional con Excel/Google Sheets.

## Funciones Principales (generator.py)
- `gen_modelo`: Construye modelos con soporte para `belongsTo`, `hasMany` y `appends`.
- `gen_observer`: Implementa hooks `creating`, `updating`, `saved` y `deleted` para automatización.
- `gen_filament_resource`: Crea interfaces administrativas con filtros avanzados y exportación CSV.
- `_resolver_accessor`: Motor de resolución de alias y sinónimos para VLOOKUPs en PHP.
- `gen_matriz_asistencia`: (v24b) Genera vistas de matriz para gestión de asistencia y cuadrantes.

## Configuración por Empresa
- **Adille (`adille.json`)**: Foco en logística de materiales y control de costos de obras.
- **Extractores (`extractores.json`)**: Gestión de ciclo de vida de producto: Importación -> Stock -> Venta -> Promoción.
- **KraftDo (`kraftdo.json`)**: Sistema core de pedidos NFC, gestión de clientes y catálogo dinámico.

## Comandos de Operación
```bash
# Generación de sistemas (orden recomendado)
python generator.py --config adille.json
python generator.py --config extractores.json
python generator.py --config kraftdo.json

# Gestión de servicios
./levantar.sh        # Inicia todos los contenedores y paneles
./setup_cron.sh      # Configura backups y sincronización periódica
```

## Reglas Críticas de Desarrollo
1. **Nomenclatura de Relaciones**: Si el nombre de la relación coincide con la Foreign Key, añadir sufijo `Rel` (ej: `clienteRel()`).
2. **Typehinting PHP**: Usar `$model` (sin backslash) en los métodos de los Observers.
3. **Persistencia**: Las modificaciones manuales en los sistemas generados se perderán; cualquier cambio debe realizarse en `generator.py` o en el JSON de configuración.
4. **Excel Sync**: Mantener correspondencia exacta entre las letras de columnas en JSON y el archivo Excel físico.
5. **Filament**: Seguir las directrices de la versión v4 adaptada mediante `mega_fix_filament_v4.py`.
