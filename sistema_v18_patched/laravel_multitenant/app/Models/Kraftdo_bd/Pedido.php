<?php

namespace App\Models\Kraftdo_bd;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Pedido extends Model
{
    protected $connection = 'kraftdo_bd';

    use HasFactory;

    protected $table = 'pedidos';

    protected $fillable = [
        'id_pedido',
        'fecha',
        'id_cliente',
        'cliente',
        'sku',
        'producto',
        'cantidad',
        'precio_unit',
        'costo_unit',
        'total',
        'ganancia',
        'margen',
    ];

    protected $casts = [
        'fecha' => 'datetime',
        'cantidad' => 'integer',
        'precio_unit' => 'decimal:2',
        'costo_unit' => 'decimal:2',
        'total' => 'decimal:2',
        'ganancia' => 'decimal:2',
        'margen' => 'decimal:2',
    ];

    public function id_cliente()
    {
        return $this->belongsTo(\App\Models\Cliente::class,
            'id_cliente', 'id');
    }

    public function cliente()
    {
        return $this->belongsTo(\App\Models\Cliente::class,
            'cliente', 'id');
    }

    public function sku()
    {
        return $this->belongsTo(\App\Models\Producto::class,
            'sku', 'sku');
    }

    public function producto()
    {
        return $this->belongsTo(\App\Models\Producto::class,
            'producto', 'sku');
    }

    public function caja()
    {
        return $this->hasMany(\App\Models\Caja::class,
            'id_pedido', 'id_pedido');
    }

    /**
     * Valor condicional: si AND(ISNUMBER(G6) → ISNUMBER(H6), sino G6>0),G6*H6,""
     * Fórmula Excel: =IF(AND(ISNUMBER(G6),ISNUMBER(H6),G6>0),G6*H6,"")
     */
    public function getTotalComputedAttribute()
    {
        return (AND(ISNUMBER($this->cantidad)) ? (ISNUMBER($this->precio_unit)) : ($this->cantidad>0),$this->cantidad*$this->precio_unit,"");
    }

    /**
     * Valor condicional: si AND(ISNUMBER(H6) → ISNUMBER(I6), sino ISNUMBER(G6),G6>0),(H6-I6)*G6,""
     * Fórmula Excel: =IF(AND(ISNUMBER(H6),ISNUMBER(I6),ISNUMBER(G6),G6>0),(H6-I6)*G6,"")
     */
    public function getGananciaComputedAttribute()
    {
        return (AND(ISNUMBER($this->precio_unit)) ? (ISNUMBER($this->costo_unit)) : (ISNUMBER($this->cantidad),$this->cantidad>0),($this->precio_unit-$this->costo_unit)*$this->cantidad,"");
    }

    /**
     * Cálculo: IFERROR(IF(AND(ISNUMBER(H6),H6>0),(H6-I6)/H6),"")
     * Fórmula Excel: =IFERROR(IF(AND(ISNUMBER(H6),H6>0),(H6-I6)/H6),"")
     */
    public function getMargenComputedAttribute()
    {
        return IFERROR(IF(AND(ISNUMBER($this->precio_unit),$this->precio_unit>0),($this->precio_unit-$this->costo_unit)/$this->precio_unit),"");
    }
}
