<?php

namespace App\Models\Extractores;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Promocione extends Model
{
    protected $connection = 'extractores';

    use HasFactory;

    protected $table = 'promociones';

    protected $fillable = [
        'item',
        'contacto',
        'empresa',
        'rut',
        'modelo',
        'cantidad',
        'neto',
        'iva',
        'total',
    ];

    protected $casts = [
        'cantidad' => 'integer',
        'iva' => 'decimal:2',
        'total' => 'decimal:2',
    ];

    public function item()
    {
        return $this->belongsTo(\App\Models\Venta::class,
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

    public function ventas()
    {
        return $this->hasMany(\App\Models\Venta::class,
            'item', 'item');
    }

    public function stock()
    {
        return $this->hasMany(\App\Models\Stock::class,
            'promociones', 'item');
    }

    public function importaciones()
    {
        return $this->hasMany(\App\Models\Importacione::class,
            'item', 'item');
    }

    /**
     * Cálculo: 380355*G4
     * Fórmula Excel: =380355*G4
     */
    public function getIvaComputedAttribute()
    {
        return 380355*$this->neto;
    }

    /**
     * IVA (19%) sobre iva
     * Fórmula Excel: =+H4*0.19
     */
    public function getTotalComputedAttribute()
    {
        return +$this->iva*0.19;
    }
}
