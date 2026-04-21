<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Cliente extends Model
{
    use HasFactory;

    protected $table = 'clientes';

    protected $fillable = [
        'nombre',
        'tipo',
        'whatsapp',
        'ciudad',
        'correo',
        'rubro',
        'canal',
        'fecha',
        'notas',
    ];

    protected $casts = [
        'fecha' => 'datetime',
    ];

    public function pedidos()
    {
        return $this->hasMany(\App\Models\Pedido::class,
            'id_cliente', 'id');
    }

    public function pedidos()
    {
        return $this->hasMany(\App\Models\Pedido::class,
            'cliente', 'id');
    }
}
