<?php

namespace App\Filament\Widgets\;

use Filament\Widgets\StatsOverviewWidget as BaseWidget;
use Filament\Widgets\StatsOverviewWidget\Stat;

class KraftDoStatsWidget extends BaseWidget
{
    protected function getStats(): array
    {
        return [
        Stat::make('Ventas', fn() => \App\Models\Venta::count())
            ->description('Total registros')
            ->color('success'),
        Stat::make('Stock', fn() => \App\Models\Stock::count())
            ->description('Total registros')
            ->color('success'),
        Stat::make('Promociones', fn() => \App\Models\Promocione::count())
            ->description('Total registros')
            ->color('success'),
        Stat::make('Importaciones', fn() => \App\Models\Importacione::count())
            ->description('Total registros')
            ->color('success'),
        Stat::make('Ferias', fn() => \App\Models\Feria::count())
            ->description('Total registros')
            ->color('success'),
        ];
    }
}
