<?php

namespace App\Observers;

use App\Models\Caja;
use Illuminate\Support\Facades\Log;

/**
 * Observer de Caja — cálculo automático de campos [AUTO]
 *
 * Campos calculados:
 * - saldo
 */
class CajaObserver
{
    private function calcular(Caja \$model): void
    {
        \$model->saldo = (function() use ($model) { $anterior = \App\Models\Caja::where('id', '<', $model->id)->orderBy('id', 'desc')->value('saldo') ?? 0; return $anterior + (($model->tipo === 'Ingreso') ? $model->monto : -$model->monto); })();
    }

    public function creating(Caja \$model): void
    {
        $this->calcular(\$model);
    }

    public function updating(Caja \$model): void
    {
        $this->calcular(\$model);
    }

    public function saving(Caja \$model): void
    {
        // Hook adicional si se necesita lógica extra al guardar
    }
}
