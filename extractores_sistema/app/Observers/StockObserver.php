<?php

namespace App\Observers;

use App\Models\Stock;
use Illuminate\Support\Facades\Log;

/**
 * Observer de Stock — cálculo automático de campos [AUTO]
 *
 * Campos calculados:
 * - ventas_und
 * - promociones_und
 * - stock_disponible
 */
class StockObserver
{
    private function calcular(Stock \$model): void
    {
        \$model->ventas_und = \App\Models\Venta::where('modelo', $model->modelo)->sum('cantidad');
        \$model->promociones_und = \App\Models\Promocion::where('modelo', $model->modelo)->sum('cantidad');
        \$model->stock_disponible = ($model->importacion_und ?? 0) - ($model->ventas_und ?? 0) - ($model->promociones_und ?? 0);
    }

    public function creating(Stock \$model): void
    {
        $this->calcular(\$model);
    }

    public function updating(Stock \$model): void
    {
        $this->calcular(\$model);
    }

    public function saving(Stock \$model): void
    {
        // Hook adicional si se necesita lógica extra al guardar
    }
}
