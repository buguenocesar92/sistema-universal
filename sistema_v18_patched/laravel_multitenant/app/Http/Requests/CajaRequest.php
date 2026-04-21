<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class CajaRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'fecha' => 'nullable|date',
            'tipo' => 'nullable|string|max:255',
            'subcategoria' => 'nullable|string|max:255',
            'monto' => 'required|numeric|min:0',
            'saldo' => 'required|numeric|min:0',
            'id_pedido' => 'nullable|string|max:255',
            'detalle' => 'nullable|string|max:255',
        ];
    }
}
