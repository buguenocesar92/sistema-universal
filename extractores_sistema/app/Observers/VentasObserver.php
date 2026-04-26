<?php

namespace App\Observers;

use App\Models\Ventas;
use Illuminate\Support\Facades\Log;

/**
 * Observer de Ventas — cálculo automático de campos [AUTO]
 *
 * Campos calculados:
 * - iva
 * - total
 */
class VentasObserver
{
    private function calcular(Ventas \$model): void
    {
        \$model->iva = (int)round($model->neto * 0.19);
        \$model->total = ($model->neto ?? 0) + ($model->iva ?? 0);
    }

    public function creating(Ventas \$model): void
    {
        $this->calcular(\$model);
    }

    public function updating(Ventas \$model): void
    {
        $this->calcular(\$model);
    }

    public function saving(Ventas \$model): void
    {
        // Hook adicional si se necesita lógica extra al guardar
    }
}
