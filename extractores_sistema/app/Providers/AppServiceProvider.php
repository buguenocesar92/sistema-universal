<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void {}

    public function boot(): void
    {
        // Registro de Observers — campos [AUTO] se calculan al crear/editar
        \App\Models\Productos::observe(\App\Observers\ProductosObserver::class);
        \App\Models\Stock::observe(\App\Observers\StockObserver::class);
        \App\Models\Ventas::observe(\App\Observers\VentasObserver::class);
        \App\Models\Importaciones::observe(\App\Observers\ImportacionesObserver::class);
        \App\Models\Promociones::observe(\App\Observers\PromocionesObserver::class);
    }
}
