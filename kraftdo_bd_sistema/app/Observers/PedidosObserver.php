<?php

namespace App\Observers;

use App\Models\Pedidos;
use Illuminate\Support\Facades\Log;

/**
 * Observer de Pedidos — cálculo automático de campos [AUTO]
 *
 * Campos calculados:
 * - nombre_cliente
 * - producto
 * - costo_unit
 * - precio_unit_calc
 * - total
 * - ganancia
 * - margen_pct
 * - anticipo
 * - saldo
 */
class PedidosObserver
{
    private function calcular(Pedidos \$model): void
    {
        \$model->nombre_cliente = optional(\App\Models\Cliente::where('id_cliente', $model->id_cliente)->first())->nombre_empresa ?? '';
        \$model->producto = optional(\App\Models\Producto::where('sku', $model->sku)->first())->nombre ?? '';
        \$model->costo_unit = optional(\App\Models\Producto::where('sku', $model->sku)->first())->costo_total ?? 0;
        \$model->precio_unit_calc = (function() use ($model) { $p = \App\Models\Producto::where('sku', $model->sku)->first(); if (!$p) return 0; return ($model->cantidad >= 15) ? $p->precio_mayor : $p->precio_unit; })();
        \$model->total = ($model->precio_unit_calc ?? 0) * ($model->cantidad ?? 0);
        \$model->ganancia = ($model->total ?? 0) - (($model->costo_unit ?? 0) * ($model->cantidad ?? 0));
        \$model->margen_pct = ($model->total > 0) ? round($model->ganancia / $model->total, 4) : 0;
        \$model->anticipo = (int)round(($model->total ?? 0) * 0.5);
        \$model->saldo = ($model->total ?? 0) - ($model->anticipo ?? 0);
    }

    public function creating(Pedidos \$model): void
    {
        $this->calcular(\$model);
    }

    public function updating(Pedidos \$model): void
    {
        $this->calcular(\$model);
    }

    public function saving(Pedidos \$model): void
    {
        // Hook adicional si se necesita lógica extra al guardar
    }
}
