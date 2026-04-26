<?php

namespace App\Observers;

use App\Models\Proveedores;
use Illuminate\Support\Facades\Log;

/**
 * Observer de Proveedores — cálculo automático de campos [AUTO]
 *
 * Campos calculados:

 */
class ProveedoresObserver
{
    private function calcular(Proveedores \$model): void
    {
        // Sin campos calculados para esta tabla
    }

    public function creating(Proveedores \$model): void
    {
        $this->calcular(\$model);
    }

    public function updating(Proveedores \$model): void
    {
        $this->calcular(\$model);
    }

    public function saving(Proveedores \$model): void
    {
        // Hook adicional si se necesita lógica extra al guardar
    }
}
