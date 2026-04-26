<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void {}

    public function boot(): void
    {
        // Registro de Observers — campos [AUTO] se calculan al crear/editar
        \App\Models\Obras::observe(\App\Observers\ObrasObserver::class);
        \App\Models\Materiales::observe(\App\Observers\MaterialesObserver::class);
        \App\Models\Personal::observe(\App\Observers\PersonalObserver::class);
        \App\Models\Facturacion::observe(\App\Observers\FacturacionObserver::class);
        \App\Models\BencinaTransporte::observe(\App\Observers\BencinaTransporteObserver::class);
    }
}
