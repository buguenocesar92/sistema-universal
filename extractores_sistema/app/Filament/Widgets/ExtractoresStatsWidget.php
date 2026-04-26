<?php

namespace App\Filament\Widgets;

use Filament\Widgets\StatsOverviewWidget as BaseWidget;
use Filament\Widgets\StatsOverviewWidget\Stat;

/**
 * KPIs del Dashboard — Extractores Chile Ltda
 * Actualizado en cada carga de página con datos reales
 */
class ExtractoresStatsWidget extends BaseWidget
{
    protected static ?int $sort = 1;
    protected int | string | array $columnSpan = 'full';

    protected function getStats(): array
    {
        return [
            Stat::make('Stock total', \App\Models\Stock::sum('stock_disponible').' unidades')
                ->description('Unidades disponibles en bodega')
                ->icon('heroicon-o-archive-box')
                ->color('primary'),
            Stat::make('Ventas del mes', '$'.number_format(\App\Models\Venta::whereMonth('fecha', now()->month)->sum('total'), 0, ',', '.'))
                ->description('Total neto facturado este mes')
                ->icon('heroicon-o-banknotes')
                ->color('success'),
            Stat::make('Unidades vendidas', \App\Models\Venta::whereMonth('fecha', now()->month)->sum('cantidad').' unidades')
                ->description('Extractores vendidos este mes')
                ->icon('heroicon-o-shopping-cart')
                ->color('info'),
            Stat::make('Inversión importaciones', '$'.number_format(\App\Models\Importacion::sum('total'), 0, ',', '.'))
                ->description('Total invertido en importaciones')
                ->icon('heroicon-o-globe-alt')
                ->color('warning'),
            Stat::make('Costo unit. promedio', '$'.number_format(\App\Models\Importacion::avg('costo_unit_import') ?? 0, 0, ',', '.'))
                ->description('Costo promedio por unidad importada')
                ->icon('heroicon-o-calculator')
                ->color('info'),
            Stat::make('Modelo más vendido', optional(\App\Models\Venta::select('modelo', \Illuminate\Support\Facades\DB::raw('SUM(cantidad) as total_und'))->groupBy('modelo')->orderByDesc('total_und')->first())->modelo ?? 'Sin datos')
                ->description('Modelo con más unidades vendidas')
                ->icon('heroicon-o-star')
                ->color('success'),
        ];
    }
}
