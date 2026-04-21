<?php

namespace App\Models\Extractores;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Importacione extends Model
{
    protected $connection = 'extractores';

    use HasFactory;

    protected $table = 'importaciones';

    protected $fillable = [
        'item',
        'modelo',
        'unidades',
        'pi_numero',
        'empresa',
        'rut',
        'factura',
        'costo_china',
        'embarcadero',
        'agente_aduana',
        'total_neto',
        'iva_servicio',
    ];

    protected $casts = [
        'costo_china' => 'decimal:2',
        'total_neto' => 'decimal:2',
    ];

    public function item()
    {
        return $this->belongsTo(\App\Models\Venta::class,
            'item', 'item');
    }

    public function item()
    {
        return $this->belongsTo(\App\Models\Promocione::class,
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

    public function promociones()
    {
        return $this->hasMany(\App\Models\Promocione::class,
            'item', 'item');
    }

    /**
     * Multiplicar 5707 por 959
     * Fórmula Excel: =5707*959
     */
    public function getEmbarcaderoComputedAttribute()
    {
        return 5707*959;
    }

    /**
     * Suma de 309446 y 202300
     * Fórmula Excel: =309446+202300+168534
     */
    public function getAgenteAduanaComputedAttribute()
    {
        return 309446+202300+168534;
    }

    /**
     * Cálculo: 1106438-N4
     * Fórmula Excel: =1106438-N4
     */
    public function getTotalNetoComputedAttribute()
    {
        return 1106438-$this->col_n;
    }
}
