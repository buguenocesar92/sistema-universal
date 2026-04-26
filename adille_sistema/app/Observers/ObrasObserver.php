<?php

namespace App\Observers;

use App\Models\Obras;
use Illuminate\Support\Facades\Log;

/**
 * Observer de Obras — cálculo automático de campos [AUTO]
 *
 * Campos calculados:
 * - dias_restantes
 * - cobrado
 * - materiales
 * - mano_obra
 * - otros
 * - total_gastado
 * - resultado
 * - margen
 */
class ObrasObserver
{
    private function calcular(Obras \$model): void
    {
        \$model->dias_restantes = ($model->fecha_plazo) ? (int)\Carbon\Carbon::today()->diffInDays($model->fecha_plazo, false) : 0;
        \$model->cobrado = \App\Models\Facturacion::where('obra_id', $model->id)->sum('monto_cobrado');
        \$model->materiales = \App\Models\Material::where('obra_id', $model->id)->sum('costo');
        \$model->mano_obra = \App\Models\Liquidacion::where('obra_id', $model->id)->sum('a_pagar');
        \$model->otros = \App\Models\BencinaTransporte::where('obra_id', $model->id)->sum('total');
        \$model->total_gastado = ($model->materiales ?? 0) + ($model->mano_obra ?? 0) + ($model->otros ?? 0);
        \$model->resultado = ($model->cobrado ?? 0) - ($model->total_gastado ?? 0);
        \$model->margen = ($model->cobrado > 0) ? round($model->resultado / $model->cobrado, 4) : 0;
    }

    public function creating(Obras \$model): void
    {
        $this->calcular(\$model);
    }

    public function updating(Obras \$model): void
    {
        $this->calcular(\$model);
    }

    public function saving(Obras \$model): void
    {
        // Hook adicional si se necesita lógica extra al guardar
    }
}
