<?php

namespace App\Observers;

use App\Models\Productos;
use Illuminate\Support\Facades\Log;

/**
 * Observer de Productos — cálculo automático de campos [AUTO]
 *
 * Campos calculados:
 * - costo_total
 * - precio_unit
 * - precio_mayor
 */
class ProductosObserver
{
    private function calcular(Productos \$model): void
    {
        \$model->costo_total = ($model->costo_insumo ?? 0) + ($model->costo_produccion ?? 0);
        \$model->precio_unit = ($model->margen > 0 && $model->margen < 1) ? (int)round(($model->costo_insumo + $model->costo_produccion) / (1 - $model->margen)) : ($model->costo_insumo + $model->costo_produccion);
        \$model->precio_mayor = (int)round($model->precio_unit * 0.895);
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
