<?php

namespace App\Observers;

use App\Models\Importaciones;
use Illuminate\Support\Facades\Log;

/**
 * Observer de Importaciones — cálculo automático de campos [AUTO]
 *
 * Campos calculados:
 * - total_neto
 * - iva_embarcadero
 * - iva_aduanero
 * - total_iva
 * - total
 * - costo_unit_import
 */
class ImportacionesObserver
{
    private function calcular(Importaciones \$model): void
    {
        \$model->total_neto = ($model->costo_china ?? 0) + ($model->embarcadero ?? 0) + ($model->agente_aduana ?? 0);
        \$model->iva_embarcadero = (int)round(($model->embarcadero ?? 0) * 0.19);
        \$model->iva_aduanero = (int)round(($model->agente_aduana ?? 0) * 0.19);
        \$model->total_iva = ($model->iva_embarcadero ?? 0) + ($model->iva_aduanero ?? 0);
        \$model->total = ($model->total_neto ?? 0) + ($model->total_iva ?? 0);
        \$model->costo_unit_import = ($model->unidades > 0) ? (int)round($model->total / $model->unidades) : 0;
    }

    public function creating(Importaciones \$model): void
    {
        $this->calcular(\$model);
    }

    public function updating(Importaciones \$model): void
    {
        $this->calcular(\$model);
    }

    public function saving(Importaciones \$model): void
    {
        // Hook adicional si se necesita lógica extra al guardar
    }
}
