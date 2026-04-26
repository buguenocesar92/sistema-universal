<?php

namespace App\Observers;

use App\Models\Insumos;
use Illuminate\Support\Facades\Log;

/**
 * Observer de Insumos — cálculo automático de campos [AUTO]
 *
 * Campos calculados:
 * - alerta_stock
 */
class InsumosObserver
{
    private function calcular(Insumos \$model): void
    {
        \$model->alerta_stock = ($model->stock_actual <= $model->stock_minimo) ? '⚠️ REPONER' : '✅ OK';
    }

    public function creating(Insumos \$model): void
    {
        $this->calcular(\$model);
    }

    public function updating(Insumos \$model): void
    {
        $this->calcular(\$model);
    }

    public function saving(Insumos \$model): void
    {
        // Hook adicional si se necesita lógica extra al guardar
    }
}
