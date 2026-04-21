<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class ProductoRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'sku' => 'nullable|string|max:255',
            'categoria' => 'nullable|string|max:255',
            'nombre' => 'nullable|string|max:255',
            'variante' => 'nullable|string|max:255',
            'costo_insumo' => 'required|numeric|min:0',
            'costo_prod' => 'required|numeric|min:0',
            'costo_total' => 'required|numeric|min:0',
            'margen' => 'required|numeric|min:0',
            'precio_unit' => 'required|numeric|min:0',
            'precio_mayor' => 'required|numeric|min:0',
            'stock' => 'required|numeric|min:0',
            'dias_prod' => 'required|numeric|min:0',
        ];
    }
}
