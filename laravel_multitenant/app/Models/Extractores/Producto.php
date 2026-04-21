<?php

namespace App\Models\Extractores;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Producto extends Model
{
    protected $connection = 'extractores';

    use HasFactory;

    protected $table = 'productos';

    protected $fillable = [
        'modelo',
        'sku',
        'precio',
        'panel',
        'flujo_aire',
        'cobertura',
        'motor',
        'garantia',
        'aplicaciones',
    ];

    protected $casts = [
        'precio' => 'decimal:2',
    ];

    public function modelo()
    {
        return $this->belongsTo(\App\Models\Stock::class,
            'modelo', 'modelo');
    }

    public function ventas()
    {
        return $this->hasMany(\App\Models\Venta::class,
            'modelo', 'modelo');
    }

    public function stock()
    {
        return $this->hasMany(\App\Models\Stock::class,
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
}
