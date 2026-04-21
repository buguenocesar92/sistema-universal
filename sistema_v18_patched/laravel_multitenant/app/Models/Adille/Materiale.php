<?php

namespace App\Models\Adille;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Materiale extends Model
{
    protected $connection = 'adille';

    use HasFactory;

    protected $table = 'materiales';

    protected $fillable = [
        'obra',
        'fecha',
        'detalle',
        'costo_gym',
        'costo_nogales',
        'gastos_generales',
    ];

    protected $casts = [
        'fecha' => 'datetime',
        'costo_gym' => 'decimal:2',
        'costo_nogales' => 'decimal:2',
    ];

    public function bencina()
    {
        return $this->hasMany(\App\Models\Bencina::class,
            'detalle', 'detalle');
    }
}
