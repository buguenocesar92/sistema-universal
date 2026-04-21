<?php

namespace App\Models\Extractores;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Venta extends Model
{
    protected $connection = 'extractores';

    use HasFactory;

    protected $table = 'ventas';

    protected $fillable = [
        'item',
        'contacto',
        'tipo_estructura',
        'empresa',
        'rut',
        'factura',
        'fecha',
        'modelo',
        'cantidad',
        'neto',
        'neto_dsto',
        'iva',
    ];

    protected $casts = [
        'fecha' => 'datetime',
        'cantidad' => 'integer',
        'iva' => 'decimal:2',
    ];

    public function item()
    {
        return $this->belongsTo(\App\Models\Promocione::class,
            'item', 'item');
    }

    public function item()
    {
        return $this->belongsTo(\App\Models\Importacione::class,
            'item', 'item');
    }

    public function modelo()
    {
        return $this->belongsTo(\App\Models\Stock::class,
            'modelo', 'modelo');
    }

    public function modelo()
    {
        return $this->belongsTo(\App\Models\Producto::class,
            'modelo', 'modelo');
    }

    public function stock()
    {
        return $this->hasMany(\App\Models\Stock::class,
            'ventas', 'item');
    }

    public function promociones()
    {
        return $this->hasMany(\App\Models\Promocione::class,
            'item', 'item');
    }

    public function importaciones()
    {
        return $this->hasMany(\App\Models\Importacione::class,
            'item', 'item');
    }

    /**
     * Suma de 410418 y 85000
     * Fórmula Excel: =410418+85000
     */
    public function getIvaComputedAttribute()
    {
        return 410418+85000;
    }

    /**
     * Multiplicar 482845 por 4
     * Fórmula Excel: =482845*4
     */
    public function getNetoDstoComputedAttribute()
    {
        return 482845*4;
    }
}
