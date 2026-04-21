#!/bin/bash
# KraftDo — install.sh
# Instala el sistema generado para: adille
# Ejecutar desde la raíz del proyecto Laravel

set -e
echo "🚀 Instalando sistema adille..."

# 1. Dependencias
composer require filament/filament\ncomposer require bezhansalleh/filament-shield\ncomposer require pxlrbt/filament-excel\ncomposer require leandrocfe/filament-apex-charts\ncomposer require spatie/laravel-medialibrary\ncomposer require filament/spatie-laravel-media-library-plugin\necho "✅ Dependencias + plugins Filament instalados"

# 2. Migraciones
php artisan migrate --force
echo "✅ Tablas creadas"

# 3. Seeders (datos de ejemplo)
php artisan db:seed --class=MaterialeSeeder
php artisan db:seed --class=LiquidacionSeeder
php artisan db:seed --class=BencinaSeeder
php artisan db:seed --class=FacturacionSeeder
echo "✅ Datos de ejemplo cargados"

# 4. Recursos Filament
php artisan make:filament-resource Materiale --generate --force
php artisan make:filament-resource Liquidacion --generate --force
php artisan make:filament-resource Bencina --generate --force
php artisan make:filament-resource Facturacion --generate --force
echo "✅ Recursos Filament generados"

# 5. Compilar assets
npm install && npm run build
echo "✅ Assets compilados"

# 6. Crear usuario admin
php artisan make:filament-user
echo "✅ Listo! Abre /admin en tu navegador"
