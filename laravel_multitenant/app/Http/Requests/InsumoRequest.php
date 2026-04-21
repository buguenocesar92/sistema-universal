<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class InsumoRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'nombre' => 'nullable|string|max:255',
            'unidad' => 'nullable|string|max:255',
            'stock' => 'required|numeric|min:0',
            'stock_min' => 'nullable|string|max:255',
            'alerta' => 'nullable|string|max:255',
            'costo' => 'required|numeric|min:0',
            'proveedor' => 'nullable|string|max:255',
            'actualizado' => 'nullable|string|max:255',
            'notas' => 'nullable|string|max:255',
        ];
    }
}
