# KraftDo Sistema Universal v18

Convierte cualquier Excel de PYME en un sistema web completo con panel admin,
API REST, automaciones y backups. Sin reemplazar el Excel del cliente — entendiendolo.

## El problema que resuelve

Toda PYME tiene su sistema en Excel. Lleno de formulas y colores que documentan
años de logica de negocio. Este sistema lo lee, lo entiende, y genera todo lo demas.

    Excel del cliente
          |
    config.py (mapeo de columnas)
          |
    Sistema Universal v18
          |
    ┌─────┴──────┬──────────┬──────────┐
    API REST   Admin     PWA       Automaciones
    FastAPI    Filament  HTML/JS   Prefect + cron

## Que genera automaticamente

- Panel de administracion (Laravel + Filament 4)
- API REST documentada (Python + FastAPI)
- Formularios dinamicos para captura de datos
- Reportes PDF automaticos por email
- Backups versionados (MinIO)
- Scheduler de tareas (Prefect)
- Bot de Telegram/WhatsApp (opcional)

## Stack

    Python 3.12     FastAPI, Pandas, DuckDB, Pydantic v2
    Laravel 11      Filament 4, MySQL, Redis
    Docker          24 servicios en docker-compose
    Prefect         Scheduler de automaciones
    MinIO           Backups versionados
    n8n             Integraciones visuales

## Instalacion

    git clone https://github.com/buguenocesar92/sistema-universal.git
    cd sistema-universal/sistema_v18_patched
    cp .env.example .env
    # Editar .env con tus valores
    docker compose up -d

## Configurar una empresa nueva

Crear empresas/mi_empresa/config.py:

    EMPRESA = {
        "nombre": "Mi Empresa SpA",
        "archivo_excel": "datos.xlsx",
        "hojas": {
            "productos": {"fila_inicio": 7, "columnas": {...}},
            "pedidos":   {"fila_inicio": 2, "columnas": {...}},
        }
    }

El sistema genera migraciones, modelos, recursos Filament y endpoints API
automaticamente desde ese archivo.

## Empresas incluidas como ejemplo

| Empresa | Descripcion |
|---------|-------------|
| kraftdo_bd | Productos, pedidos y caja de KraftDo SpA |
| adille | Control de obras de Constructora Adille |
| extractores | Catalogo de Extractores Chile |

## Tests

    cd sistema_v18_patched
    python3 -m pytest tests/ -v
    # 92/92 tests pasando

## Documentacion

- KraftDo_Manual_Usuario.pdf — guia paso a paso para el usuario final
- KraftDo_Documentacion_Tecnica.pdf — referencia tecnica completa (20 secciones)

---

Parte del ecosistema KraftDo SpA — digitalizamos PYMEs chilenas.
https://kraftdo.cl
