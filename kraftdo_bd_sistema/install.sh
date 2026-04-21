#!/bin/bash
# KraftDo — install.sh
# Instala el sistema generado para: kraftdo_bd
# Ejecutar desde la raíz del proyecto Laravel

set -e
echo "🚀 Instalando sistema kraftdo_bd..."

# 1. Dependencias
composer require filament/filament\ncomposer require bezhansalleh/filament-shield\ncomposer require pxlrbt/filament-excel\ncomposer require leandrocfe/filament-apex-charts\ncomposer require spatie/laravel-medialibrary\ncomposer require filament/spatie-laravel-media-library-plugin\necho "✅ Dependencias + plugins Filament instalados"

# 2. Migraciones
php artisan migrate --force
echo "✅ Tablas creadas"

# 3. Seeders (datos de ejemplo)
php artisan db:seed --class=ProductoSeeder
php artisan db:seed --class=ProveedoreSeeder
php artisan db:seed --class=InsumoSeeder
php artisan db:seed --class=ClienteSeeder
php artisan db:seed --class=PedidoSeeder
php artisan db:seed --class=CajaSeeder
echo "✅ Datos de ejemplo cargados"

# 4. Recursos Filament
php artisan make:filament-resource Producto --generate --force
php artisan make:filament-resource Proveedore --generate --force
php artisan make:filament-resource Insumo --generate --force
php artisan make:filament-resource Cliente --generate --force
php artisan make:filament-resource Pedido --generate --force
php artisan make:filament-resource Caja --generate --force
echo "✅ Recursos Filament generados"

# 5. Compilar assets
npm install && npm run build
echo "✅ Assets compilados"

# 6. Crear usuario admin
php artisan make:filament-user
echo "✅ Listo! Abre /admin en tu navegador"
