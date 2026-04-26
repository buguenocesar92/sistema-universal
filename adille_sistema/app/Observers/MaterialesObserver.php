<?php

namespace App\Observers;

use App\Models\Materiales;
use Illuminate\Support\Facades\Log;

/**
 * Observer de Materiales — cálculo automático de campos [AUTO]
 *
 * Campos calculados:

 */
class MaterialesObserver
{
    private function calcular(Materiales \$model): void
    {
        // Sin campos calculados para esta tabla
    }

    public function creating(Materiales \$model): void
    {
        $this->calcular(\$model);
    }

    public function updating(Materiales \$model): void
    {
        $this->calcular(\$model);
    }

    public function saving(Materiales \$model): void
    {
        // Hook adicional si se necesita lógica extra al guardar
    }
}
