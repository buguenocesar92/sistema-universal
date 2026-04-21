<?php

namespace App\Filament\Widgets\;

use Filament\Widgets\StatsOverviewWidget as BaseWidget;
use Filament\Widgets\StatsOverviewWidget\Stat;

class KraftDoStatsWidget extends BaseWidget
{
    protected function getStats(): array
    {
        return [
        Stat::make('Proveedores', fn() => \App\Models\Proveedore::count())
            ->description('Total registros')
            ->color('success'),
        Stat::make('Insumos', fn() => \App\Models\Insumo::count())
            ->description('Total registros')
            ->color('success'),
        Stat::make('Clientes', fn() => \App\Models\Cliente::count())
            ->description('Total registros')
            ->color('success'),
        Stat::make('Pedidos', fn() => \App\Models\Pedido::count())
            ->description('Total registros')
            ->color('success'),
        Stat::make('Caja', fn() => \App\Models\Caja::count())
            ->description('Total registros')
            ->color('success'),
        ];
    }
}
