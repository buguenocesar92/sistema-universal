<?php

namespace App\Models\Kraftdo_bd;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Caja extends Model
{
    protected $connection = 'kraftdo_bd';

    use HasFactory;

    protected $table = 'caja';

    protected $fillable = [
        'numero',
        'fecha',
        'tipo',
        'subcategoria',
        'monto',
        'saldo',
        'id_pedido',
        'detalle',
    ];

    protected $casts = [
        'fecha' => 'datetime',
        'monto' => 'decimal:2',
        'saldo' => 'decimal:2',
    ];

    public function id_pedido()
    {
        return $this->belongsTo(\App\Models\Pedido::class,
            'id_pedido', 'id_pedido');
    }

    /**
     * Valor condicional: si B10<>"" → 1, sino ""
     * Fórmula Excel: =IF(B10<>"",1,"")
     */
    public function getNumeroComputedAttribute()
    {
        return ($this->fecha<>"") ? (1) : ("");
    }

    /**
     * Valor condicional: si B10<>"" → IF(C10="Ingreso", sino E10,-E10),""
     * Fórmula Excel: =IF(B10<>"",IF(C10="Ingreso",E10,-E10),"")
     */
    public function getSaldoComputedAttribute()
    {
        return ($this->fecha<>"") ? (IF($this->tipo="Ingreso") : ($this->monto,-$this->monto),"");
    }
}
