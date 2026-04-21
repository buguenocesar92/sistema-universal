<?php

namespace App\Filament\Widgets\;

use Filament\Widgets\StatsOverviewWidget as BaseWidget;
use Filament\Widgets\StatsOverviewWidget\Stat;

class KraftDoStatsWidget extends BaseWidget
{
    protected function getStats(): array
    {
        return [
        Stat::make('Materiales', fn() => \App\Models\Materiale::count())
            ->description('Total registros')
            ->color('success'),
        Stat::make('Liquidacion', fn() => \App\Models\Liquidacion::count())
            ->description('Total registros')
            ->color('success'),
        Stat::make('Bencina', fn() => \App\Models\Bencina::count())
            ->description('Total registros')
            ->color('success'),
        Stat::make('Facturacion', fn() => \App\Models\Facturacion::count())
            ->description('Total registros')
            ->color('success'),
        ];
    }
}
