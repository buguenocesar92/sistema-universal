<?php

namespace App\Observers;

use App\Models\Promociones;
use Illuminate\Support\Facades\Log;

/**
 * Observer de Promociones — cálculo automático de campos [AUTO]
 *
 * Campos calculados:
 * - iva
 * - total
 */
class PromocionesObserver
{
    private function calcular(Promociones \$model): void
    {
        \$model->iva = (int)round($model->neto * 0.19);
        \$model->total = ($model->neto ?? 0) + ($model->iva ?? 0);
    }

    public function creating(Promociones \$model): void
    {
        $this->calcular(\$model);
    }

    public function updating(Promociones \$model): void
    {
        $this->calcular(\$model);
    }

    public function saving(Promociones \$model): void
    {
        // Hook adicional si se necesita lógica extra al guardar
    }
}
