<?php

namespace App\Observers;

use App\Models\Personal;
use Illuminate\Support\Facades\Log;

/**
 * Observer de Personal — cálculo automático de campos [AUTO]
 *
 * Campos calculados:
 * - faltas
 * - valor_dia
 * - descuento_faltas
 * - a_pagar
 * - saldo
 */
class PersonalObserver
{
    private function calcular(Personal \$model): void
    {
        \$model->faltas = max(0, ($model->dias_laborales ?? 0) - ($model->dias_trabajados ?? 0));
        \$model->valor_dia = ($model->dias_laborales > 0) ? (int)round($model->sueldo_base / $model->dias_laborales) : 0;
        \$model->descuento_faltas = ($model->valor_dia ?? 0) * ($model->faltas ?? 0);
        \$model->a_pagar = ($model->sueldo_base ?? 0) - ($model->descuento_faltas ?? 0);
        \$model->saldo = ($model->a_pagar ?? 0) - ($model->quincena_pagada ?? 0);
    }

    public function creating(Personal \$model): void
    {
        $this->calcular(\$model);
    }

    public function updating(Personal \$model): void
    {
        $this->calcular(\$model);
    }

    public function saving(Personal \$model): void
    {
        // Hook adicional si se necesita lógica extra al guardar
    }
}
