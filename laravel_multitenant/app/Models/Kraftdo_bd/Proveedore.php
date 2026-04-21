<?php

namespace App\Models\Kraftdo_bd;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Proveedore extends Model
{
    protected $connection = 'kraftdo_bd';

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
