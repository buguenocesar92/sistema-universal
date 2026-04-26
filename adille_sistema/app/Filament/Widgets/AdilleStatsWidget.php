<?php

namespace App\Filament\Widgets;

use Filament\Widgets\StatsOverviewWidget as BaseWidget;
use Filament\Widgets\StatsOverviewWidget\Stat;

/**
 * KPIs del Dashboard — Constructora Adille
 * Actualizado en cada carga de página con datos reales
 */
class AdilleStatsWidget extends BaseWidget
{
    protected static ?int $sort = 1;
    protected int | string | array $columnSpan = 'full';

    protected function getStats(): array
    {
        return [
            Stat::make('Resultado global', '$'.number_format(\App\Models\Obra::sum('cobrado') - \App\Models\Obra::sum('total_gastado'), 0, ',', '.'))
                ->description('Cobrado menos gastado en todas las obras')
                ->icon('heroicon-o-scale')
                ->color('info'),
            Stat::make('Obras activas', \App\Models\Obra::whereIn('estado', ['En curso', 'Atrasada'])->count().' obras')
                ->description('Obras en curso actualmente')
                ->icon('heroicon-o-building-office-2')
                ->color('primary'),
            Stat::make('Gasto materiales', '$'.number_format(\App\Models\Material::sum('costo'), 0, ',', '.'))
                ->description('Total materiales todas las obras')
                ->icon('heroicon-o-cube')
                ->color('warning'),
            Stat::make('Costo personal', '$'.number_format(\App\Models\Personal::sum('a_pagar'), 0, ',', '.'))
                ->description('Total liquidaciones a pagar')
                ->icon('heroicon-o-users')
                ->color('danger'),
            Stat::make('Total cobrado', '$'.number_format(\App\Models\Facturacion::sum('monto_cobrado'), 0, ',', '.'))
                ->description('Suma de todas las facturas cobradas')
                ->icon('heroicon-o-banknotes')
                ->color('success'),
            Stat::make('Obras atrasadas', \App\Models\Obra::where('estado', 'Atrasada')->count().' obras')
                ->description('Obras con días restantes negativos')
                ->icon('heroicon-o-exclamation-triangle')
                ->color('danger'),
        ];
    }
}
