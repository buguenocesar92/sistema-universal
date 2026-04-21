<?php

namespace App\Models\Adille;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Bencina extends Model
{
    protected $connection = 'adille';

    use HasFactory;

    protected $table = 'bencina';

    protected $fillable = [
        'numero',
        'fecha',
        'vehiculo',
        'obra',
        'monto',
        'litros',
        'km',
        'detalle',
    ];

    protected $casts = [
        'fecha' => 'datetime',
        'monto' => 'decimal:2',
    ];

    public function detalle()
    {
        return $this->belongsTo(\App\Models\Materiale::class,
            'detalle', 'detalle');
    }
}
