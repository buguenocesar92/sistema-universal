"""
merge_multitenant.py — Combina los 3 sistemas Laravel generados en un solo multi-tenant
Uso: python3 merge_multitenant.py
"""
import os, shutil, re
from pathlib import Path

BASE     = Path("/tmp")
SISTEMAS = {
    "adille":      BASE / "adille_sistema",
    "extractores": BASE / "extractores_sistema",
    "kraftdo_bd":  BASE / "kraftdo_bd_sistema",
}
OUTPUT   = Path("/tmp/sistema_v18_patched/laravel_multitenant")

COLORES  = {
    "adille":      {"primary": "0D1B3E", "accent": "C8A951", "nombre": "Constructora Adille"},
    "extractores": {"primary": "1A3A5C", "accent": "E8A020", "nombre": "Extractores Chile Ltda"},
    "kraftdo_bd":  {"primary": "1A1A2E", "accent": "E94560", "nombre": "KraftDo SpA"},
}

def slug(s):
    return re.sub(r'[^a-z0-9]', '_', s.lower())

def copiar_con_prefijo(src_dir, dest_dir, empresa):
    """Copia archivos Laravel agregando prefijo de empresa donde corresponde."""
    src  = Path(src_dir)
    dest = Path(dest_dir)

    for archivo in src.rglob("*.php"):
        rel  = archivo.relative_to(src)
        partes = list(rel.parts)

        # Agregar prefijo de empresa en el nombre del archivo/directorio
        if len(partes) >= 2 and partes[0] in ("app", "database"):
            # app/Models/Producto.php → app/Models/Adille/Producto.php
            if partes[1] == "Models":
                partes.insert(2, empresa.capitalize())
            # app/Filament/Resources/ProductoResource.php → .../Adille/ProductoResource.php
            elif partes[1] == "Filament" and len(partes) >= 3:
                partes.insert(3, empresa.capitalize())
            # app/Http/Controllers/Api/ → .../Api/Adille/
            elif partes[1] == "Http" and len(partes) >= 4 and partes[3] == "Api":
                partes.insert(4, empresa.capitalize())

        dest_archivo = dest / Path(*partes)
        dest_archivo.parent.mkdir(parents=True, exist_ok=True)

        contenido = archivo.read_text(encoding="utf-8", errors="ignore")
        # Actualizar namespaces para incluir empresa
        contenido = contenido.replace(
            "namespace App\\Models;",
            f"namespace App\\Models\\{empresa.capitalize()};"
        ).replace(
            "namespace App\\Filament\\Resources;",
            f"namespace App\\Filament\\Resources\\{empresa.capitalize()};"
        ).replace(
            "use App\\Models\\",
            f"use App\\Models\\{empresa.capitalize()}\\"
        )
        dest_archivo.write_text(contenido, encoding="utf-8")

    # Copiar migraciones con prefijo de empresa
    mig_src  = src / "database" / "migrations"
    mig_dest = dest / "database" / "migrations"
    mig_dest.mkdir(parents=True, exist_ok=True)
    if mig_src.exists():
        for mig in mig_src.glob("*.php"):
            nuevo_nombre = mig.name.replace("create_", f"create_{slug(empresa)}_")
            contenido = mig.read_text(encoding="utf-8", errors="ignore")
            # Renombrar tabla en la migración
            contenido = re.sub(
                r"Schema::create\('(\w+)'",
                lambda m: f"Schema::create('{slug(empresa)}_{m.group(1)}'",
                contenido
            )
            (mig_dest / nuevo_nombre).write_text(contenido, encoding="utf-8")

# Crear estructura base
OUTPUT.mkdir(parents=True, exist_ok=True)
(OUTPUT / "app" / "Models").mkdir(parents=True, exist_ok=True)
(OUTPUT / "app" / "Filament" / "Resources").mkdir(parents=True, exist_ok=True)
(OUTPUT / "database" / "migrations").mkdir(parents=True, exist_ok=True)

# Combinar los 3 sistemas
for empresa, src_dir in SISTEMAS.items():
    if src_dir.exists():
        print(f"Procesando {empresa}...")
        copiar_con_prefijo(src_dir, OUTPUT, empresa)
        print(f"  ✅ {empresa} integrado")
    else:
        print(f"  ⚠️  {src_dir} no existe, saltando")

# Crear Panel de empresas en Filament
panel_html = """<?php
// app/Filament/Pages/Dashboard.php — Dashboard multi-tenant personalizado
namespace App\\Filament\\Pages;

use Filament\\Pages\\Dashboard as BaseDashboard;

class Dashboard extends BaseDashboard
{
    protected static ?string $navigationIcon = 'heroicon-o-home';
    protected static string $view = 'filament.pages.dashboard';
}
"""
(OUTPUT / "app" / "Filament" / "Pages").mkdir(parents=True, exist_ok=True)
(OUTPUT / "app" / "Filament" / "Pages" / "Dashboard.php").write_text(panel_html)

print(f"\n✅ Multi-tenant generado en {OUTPUT}")
print(f"   Empresas integradas: {', '.join(SISTEMAS.keys())}")

# Contar archivos
total = sum(1 for _ in OUTPUT.rglob("*.php"))
print(f"   Total archivos PHP: {total}")
