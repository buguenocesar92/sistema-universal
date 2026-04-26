<?php

namespace App\Observers;

use App\Models\Facturacion;
use Illuminate\Support\Facades\Log;

/**
 * Observer de Facturacion — cálculo automático de campos [AUTO]
 *
 * Campos calculados:
 * - ppm
 */
class FacturacionObserver
{
    private function calcular(Facturacion \$model): void
    {
        \$model->ppm = round($model->monto_cobrado * 0.025252, 2);
    }

    public function creating(Facturacion \$model): void
    {
        $this->calcular(\$model);
    }

    public function updating(Facturacion \$model): void
    {
        $this->calcular(\$model);
    }

    public function saving(Facturacion \$model): void
    {
        // Hook adicional si se necesita lógica extra al guardar
    }
}
