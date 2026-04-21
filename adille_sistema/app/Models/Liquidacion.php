<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Liquidacion extends Model
{
    use HasFactory;

    protected $table = 'liquidacion';

    protected $fillable = [
        'codigo',
        'obra',
        'trabajador',
        'sueldo_base',
        'dias_laborales',
        'dias_trabajados',
        'faltas',
        'valor_dia',
        'descuento_faltas',
        'a_pagar',
        'quincena_pagada',
        'saldo',
    ];

    protected $casts = [
        'dias_laborales' => 'integer',
        'dias_trabajados' => 'integer',
        'descuento_faltas' => 'decimal:2',
        'saldo' => 'decimal:2',
    ];

    /**
     * Cálculo: 'CONTROL PERSONAL'!B5
     * Fórmula Excel: ='CONTROL PERSONAL'!B5
     */
    public function getCodigoComputedAttribute()
    {
        return '$this->col_control $this->col_personal'!$this->codigo;
    }

    /**
     * Cálculo: 'CONTROL PERSONAL'!C5
     * Fórmula Excel: ='CONTROL PERSONAL'!C5
     */
    public function getObraComputedAttribute()
    {
        return '$this->col_control $this->col_personal'!$this->obra;
    }

    /**
     * Cálculo: 'CONTROL PERSONAL'!D5
     * Fórmula Excel: ='CONTROL PERSONAL'!D5
     */
    public function getTrabajadorComputedAttribute()
    {
        return '$this->col_control $this->col_personal'!$this->trabajador;
    }

    /**
     * Cálculo: 'CONTROL PERSONAL'!AI5
     * Fórmula Excel: ='CONTROL PERSONAL'!AI5
     */
    public function getSueldoBaseComputedAttribute()
    {
        return '$this->col_control $this->col_personal'!$this->col_ai;
    }

    /**
     * Valor condicional: si F5=0 → 0, sino ROUND(E5/F5,0)
     * Fórmula Excel: =IF(F5=0,0,ROUND(E5/F5,0))
     */
    public function getValorDiaComputedAttribute()
    {
        return ($this->dias_laborales=0) ? (0) : (ROUND($this->sueldo_base/$this->dias_laborales,0));
    }

    /**
     * Cálculo: H5*I5
     * Fórmula Excel: =H5*I5
     */
    public function getDescuentoFaltasComputedAttribute()
    {
        return $this->faltas*$this->valor_dia;
    }

    /**
     * Cálculo: E5-J5
     * Fórmula Excel: =E5-J5
     */
    public function getAPagarComputedAttribute()
    {
        return $this->sueldo_base-$this->descuento_faltas;
    }

    /**
     * Valor condicional: si DAY(TODAY())>=15 → IF('CONTROL PERSONAL'!T5="", sino 0,'CONTROL PERSONAL'!T5),0
     * Fórmula Excel: =IF(DAY(TODAY())>=15,IF('CONTROL PERSONAL'!T5="",0,'CONTROL PERSONAL'!T5),0)
     */
    public function getQuincenaPagadaComputedAttribute()
    {
        return (DAY(TODAY())>=15) ? (IF('$this->col_control $this->col_personal'!$this->col_t="") : (0,'$this->col_control $this->col_personal'!$this->col_t),0);
    }

    /**
     * Cálculo: K5-L5
     * Fórmula Excel: =K5-L5
     */
    public function getSaldoComputedAttribute()
    {
        return $this->a_pagar-$this->quincena_pagada;
    }
}
