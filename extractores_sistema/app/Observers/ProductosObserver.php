<?php

namespace App\Observers;

use App\Models\Productos;
use Illuminate\Support\Facades\Log;

/**
 * Observer de Productos — cálculo automático de campos [AUTO]
 *
 * Campos calculados:
 * - precio_neto
 */
class ProductosObserver
{
    private function calcular(Productos \$model): void
    {
        \$model->precio_neto = (int)round($model->precio_clp_iva / 1.19);
    }

    public function creating(Productos \$model): void
    {
        $this->calcular(\$model);
    }

    public function updating(Productos \$model): void
    {
        $this->calcular(\$model);
    }

    public function saving(Productos \$model): void
    {
        // Hook adicional si se necesita lógica extra al guardar
    }
}
