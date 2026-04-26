<?php

namespace App\Filament\Widgets;

use Filament\Widgets\StatsOverviewWidget as BaseWidget;
use Filament\Widgets\StatsOverviewWidget\Stat;

/**
 * KPIs del Dashboard — KraftDo SpA
 * Actualizado en cada carga de página con datos reales
 */
class KraftdoStatsWidget extends BaseWidget
{
    protected static ?int $sort = 1;
    protected int | string | array $columnSpan = 'full';

    protected function getStats(): array
    {
        return [
            Stat::make('Ventas del mes', '$'.number_format(\App\Models\Pedido::whereMonth('fecha', now()->month)->whereYear('fecha', now()->year)->sum('total'), 0, ',', '.'))
                ->description('Total facturado en el mes actual')
                ->icon('heroicon-o-banknotes')
                ->color('success'),
            Stat::make('Pedidos activos', \App\Models\Pedido::whereIn('estado', ['Pendiente', 'En producción', 'Confirmado'])->count().' pedidos')
                ->description('En producción o pendientes')
                ->icon('heroicon-o-clipboard-document-list')
                ->color('warning'),
            Stat::make('Saldo en caja', '$'.number_format(\App\Models\Caja::latest('id')->value('saldo') ?? 0, 0, ',', '.'))
                ->description('Saldo actual del libro de caja')
                ->icon('heroicon-o-currency-dollar')
                ->color('info'),
            Stat::make('Insumos críticos', \App\Models\Insumo::whereColumn('stock_actual', '<=', 'stock_minimo')->count().' insumos')
                ->description('Insumos bajo stock mínimo')
                ->icon('heroicon-o-exclamation-triangle')
                ->color('danger'),
            Stat::make('Ganancia del mes', '$'.number_format(\App\Models\Pedido::whereMonth('fecha', now()->month)->whereYear('fecha', now()->year)->sum('ganancia'), 0, ',', '.'))
                ->description('Ganancia neta pedidos del mes')
                ->icon('heroicon-o-arrow-trending-up')
                ->color('success'),
            Stat::make('Productos activos', \App\Models\Producto::where('estado', 'Activo')->count().' productos')
                ->description('Productos en catálogo activo')
                ->icon('heroicon-o-squares-2x2')
                ->color('primary'),
        ];
    }
}
