<?php

namespace App\Models\Kraftdo_bd;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Producto extends Model
{
    protected $connection = 'kraftdo_bd';

    use HasFactory;

    protected $table = 'productos';

    protected $fillable = [
        'sku',
        'categoria',
        'nombre',
        'variante',
        'costo_insumo',
        'costo_prod',
        'costo_total',
        'margen',
        'precio_unit',
        'precio_mayor',
        'stock',
        'dias_prod',
    ];

    protected $casts = [
        'costo_insumo' => 'decimal:2',
        'costo_prod' => 'decimal:2',
        'costo_total' => 'decimal:2',
        'margen' => 'decimal:2',
        'precio_unit' => 'decimal:2',
        'precio_mayor' => 'decimal:2',
        'stock' => 'integer',
        'dias_prod' => 'integer',
    ];

    public function costo_insumo()
    {
        return $this->belongsTo(\App\Models\Insumo::class,
            'costo_insumo', 'id');
    }

    public function pedidos()
    {
        return $this->hasMany(\App\Models\Pedido::class,
            'sku', 'sku');
    }

    public function pedidos()
    {
        return $this->hasMany(\App\Models\Pedido::class,
            'producto', 'sku');
    }

    /**
     * Valor condicional: si ISNUMBER(E7) → E7+IF(ISNUMBER(F7), sino F7,0),""
     * Fórmula Excel: =IF(ISNUMBER(E7),E7+IF(ISNUMBER(F7),F7,0),"")
     */
    public function getCostoTotalComputedAttribute()
    {
        return (ISNUMBER($this->costo_insumo)) ? ($this->costo_insumo+IF(ISNUMBER($this->costo_prod)) : ($this->costo_prod,0),"");
    }

    /**
     * Valor condicional: si AND(ISNUMBER(G7) → G7>0, sino H7>0),ROUND(G7/(1-H7),0),""
     * Fórmula Excel: =IF(AND(ISNUMBER(G7),G7>0,H7>0),ROUND(G7/(1-H7),0),"")
     */
    public function getPrecioUnitComputedAttribute()
    {
        return (AND(ISNUMBER($this->costo_total)) ? ($this->costo_total>0) : ($this->margen>0),ROUND($this->costo_total/(1-$this->margen),0),"");
    }

    /**
     * Valor condicional: si AND(ISNUMBER(G7) → G7>0, sino H7>0.05),ROUND(G7/(1-(H7-0.05)),0),""
     * Fórmula Excel: =IF(AND(ISNUMBER(G7),G7>0,H7>0.05),ROUND(G7/(1-(H7-0.05)),0),"")
     */
    public function getPrecioMayorComputedAttribute()
    {
        return (AND(ISNUMBER($this->costo_total)) ? ($this->costo_total>0) : ($this->margen>0.05),ROUND($this->costo_total/(1-($this->margen-0.05)),0),"");
    }
}
