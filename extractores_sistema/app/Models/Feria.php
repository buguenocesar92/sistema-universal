<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Feria extends Model
{
    use HasFactory;

    protected $table = 'ferias';

    protected $fillable = [
        'evento',
        'fecha',
        'lugar',
        'region',
        'tipo',
        'relevancia',
        'publico',
        'costo_stand',
        'contacto',
        'estado',
    ];

    protected $casts = [
        'fecha' => 'datetime',
        'costo_stand' => 'decimal:2',
    ];
    public function scopeActivos($query)
    {
        return $query->whereIn('estado', ['Activo']);
    }
}
