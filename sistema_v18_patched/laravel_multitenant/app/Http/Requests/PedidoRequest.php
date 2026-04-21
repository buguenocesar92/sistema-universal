<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class PedidoRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'id_pedido' => 'nullable|string|max:255',
            'fecha' => 'nullable|date',
            'id_cliente' => 'nullable|string|max:255',
            'cliente' => 'nullable|string|max:255',
            'sku' => 'nullable|string|max:255',
            'producto' => 'nullable|string|max:255',
            'cantidad' => 'required|numeric|min:0',
            'precio_unit' => 'required|numeric|min:0',
            'costo_unit' => 'required|numeric|min:0',
            'total' => 'required|numeric|min:0',
            'ganancia' => 'required|numeric|min:0',
            'margen' => 'required|numeric|min:0',
        ];
    }
}
