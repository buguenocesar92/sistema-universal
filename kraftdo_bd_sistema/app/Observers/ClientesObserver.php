<?php

namespace App\Observers;

use App\Models\Clientes;
use Illuminate\Support\Facades\Log;

/**
 * Observer de Clientes — cálculo automático de campos [AUTO]
 *
 * Campos calculados:

 */
class ClientesObserver
{
    private function calcular(Clientes \$model): void
    {
        // Sin campos calculados para esta tabla
    }

    public function creating(Clientes \$model): void
    {
        $this->calcular(\$model);
    }

    public function updating(Clientes \$model): void
    {
        $this->calcular(\$model);
    }

    public function saving(Clientes \$model): void
    {
        // Hook adicional si se necesita lógica extra al guardar
    }
}
