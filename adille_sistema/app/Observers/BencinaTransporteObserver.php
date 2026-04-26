<?php

namespace App\Observers;

use App\Models\BencinaTransporte;
use Illuminate\Support\Facades\Log;

/**
 * Observer de BencinaTransporte — cálculo automático de campos [AUTO]
 *
 * Campos calculados:
 * - total
 */
class BencinaTransporteObserver
{
    private function calcular(BencinaTransporte \$model): void
    {
        \$model->total = \App\Models\BencinaTransporte::where('obra_id', $model->obra_id)->sum('monto');
    }

    public function creating(BencinaTransporte \$model): void
    {
        $this->calcular(\$model);
    }

    public function updating(BencinaTransporte \$model): void
    {
        $this->calcular(\$model);
    }

    public function saving(BencinaTransporte \$model): void
    {
        // Hook adicional si se necesita lógica extra al guardar
    }
}
