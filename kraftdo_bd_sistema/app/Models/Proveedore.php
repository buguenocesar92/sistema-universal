<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Proveedore extends Model
{
    use HasFactory;

    protected $table = 'proveedores';

    protected $fillable = [
        'nombre',
        'contacto',
        'tipo',
        'despacho',
        'minimo',
        'envio_gratis',
        'notas',
        'actualizado',
    ];

    protected $casts = [
        ,
    ];
}
