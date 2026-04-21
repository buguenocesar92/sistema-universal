<?php

namespace App\Models\Adille;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Facturacion extends Model
{
    protected $connection = 'adille';

    use HasFactory;

    protected $table = 'facturacion';

    protected $fillable = [
        'concepto',
        'abril',
        'mayo',
        'julio',
        'agosto',
        'septiembre',
        'octubre',
        'noviembre',
        'diciembre',
        'enero',
        'febrero',
        'marzo',
        'acumulado',
    ];

    protected $casts = [
        ,
    ];

    /**
     * Multiplicar abril por 0
     * Fórmula Excel: =+I7*0.03
     */
    public function getAbrilComputedAttribute()
    {
        return +$this->abril*0.03;
    }

    /**
     * Multiplicar mayo por 0
     * Fórmula Excel: =+J7*0.03
     */
    public function getMayoComputedAttribute()
    {
        return +$this->mayo*0.03;
    }

    /**
     * Multiplicar julio por 0
     * Fórmula Excel: =+K7*0.03
     */
    public function getJulioComputedAttribute()
    {
        return +$this->julio*0.03;
    }

    /**
     * Multiplicar agosto por 0
     * Fórmula Excel: =+L7*0.03
     */
    public function getAgostoComputedAttribute()
    {
        return +$this->agosto*0.03;
    }

    /**
     * Multiplicar septiembre por 0
     * Fórmula Excel: =+M7*0.03
     */
    public function getSeptiembreComputedAttribute()
    {
        return +$this->septiembre*0.03;
    }

    /**
     * Multiplicar octubre por 0
     * Fórmula Excel: =+N7*0.03
     */
    public function getOctubreComputedAttribute()
    {
        return +$this->octubre*0.03;
    }

    /**
     * Multiplicar noviembre por 0
     * Fórmula Excel: =+O7*0.03
     */
    public function getNoviembreComputedAttribute()
    {
        return +$this->noviembre*0.03;
    }

    /**
     * Multiplicar diciembre por 0
     * Fórmula Excel: =+P7*0.03
     */
    public function getDiciembreComputedAttribute()
    {
        return +$this->diciembre*0.03;
    }

    /**
     * Multiplicar enero por 0
     * Fórmula Excel: =+Q7*0.03
     */
    public function getEneroComputedAttribute()
    {
        return +$this->enero*0.03;
    }

    /**
     * Multiplicar febrero por 0
     * Fórmula Excel: =+R7*0.03
     */
    public function getFebreroComputedAttribute()
    {
        return +$this->febrero*0.03;
    }

    /**
     * Multiplicar marzo por 0
     * Fórmula Excel: =+S7*0.03
     */
    public function getMarzoComputedAttribute()
    {
        return +$this->marzo*0.03;
    }
}
