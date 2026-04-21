<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Insumo extends Model
{
    use HasFactory;

    protected $table = 'insumos';

    protected $fillable = [
        'nombre',
        'unidad',
        'stock',
        'stock_min',
        'alerta',
        'costo',
        'proveedor',
        'actualizado',
        'notas',
    ];

    protected $casts = [
        'stock' => 'integer',
        'costo' => 'decimal:2',
    ];

    public function productos()
    {
        return $this->hasMany(\App\Models\Producto::class,
            'costo_insumo', 'id');
    }

    /**
     * Valor condicional: si AND(ISNUMBER(D6) → ISNUMBER(E6)), sino IF(D6<=E6,"⚠️ REPONER","✅ OK"),"-"
     * Fórmula Excel: =IF(AND(ISNUMBER(D6),ISNUMBER(E6)),IF(D6<=E6,"⚠️ REPONER","✅ OK"),"-")
     */
    public function getAlertaComputedAttribute()
    {
        return (AND(ISNUMBER($this->stock)) ? (ISNUMBER($this->stock_min))) : (IF($this->stock<=$this->stock_min,"⚠️ $this->col_reponer","✅ $this->col_ok"),"-");
    }
}
