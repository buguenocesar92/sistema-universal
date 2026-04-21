<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Stock extends Model
{
    use HasFactory;

    protected $table = 'stock';

    protected $fillable = [
        'modelo',
        'importacion',
        'ventas',
        'promociones',
        'stock_disponible',
    ];

    protected $casts = [
        ,
    ];

    public function modelo()
    {
        return $this->belongsTo(\App\Models\Producto::class,
            'modelo', 'modelo');
    }

    public function venta()
    {
        return $this->belongsTo(\App\Models\Venta::class,
            'ventas', 'item');
    }

    public function promocione()
    {
        return $this->belongsTo(\App\Models\Promocione::class,
            'promociones', 'item');
    }

    public function ventas()
    {
        return $this->hasMany(\App\Models\Venta::class,
            'modelo', 'modelo');
    }

    public function promociones()
    {
        return $this->hasMany(\App\Models\Promocione::class,
            'modelo', 'modelo');
    }

    public function importaciones()
    {
        return $this->hasMany(\App\Models\Importacione::class,
            'modelo', 'modelo');
    }

    public function productos()
    {
        return $this->hasMany(\App\Models\Producto::class,
            'modelo', 'modelo');
    }

    /**
     * Cálculo: C5-D5-E5
     * Fórmula Excel: =C5-D5-E5
     */
    public function getStockDisponibleComputedAttribute()
    {
        return $this->importacion-$this->ventas-$this->promociones;
    }
}
