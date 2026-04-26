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
        \App\Models\Clientes::observe(\App\Observers\ClientesObserver::class);
        \App\Models\Pedidos::observe(\App\Observers\PedidosObserver::class);
        \App\Models\Caja::observe(\App\Observers\CajaObserver::class);
        \App\Models\Insumos::observe(\App\Observers\InsumosObserver::class);
        \App\Models\Proveedores::observe(\App\Observers\ProveedoresObserver::class);
    }
}
