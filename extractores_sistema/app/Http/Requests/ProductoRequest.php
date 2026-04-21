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
            'modelo' => 'nullable|string|max:255',
            'sku' => 'nullable|string|max:255',
            'precio' => 'required|numeric|min:0',
            'panel' => 'nullable|string|max:255',
            'flujo_aire' => 'nullable|string|max:255',
            'cobertura' => 'nullable|string|max:255',
            'motor' => 'nullable|string|max:255',
            'garantia' => 'nullable|string|max:255',
            'aplicaciones' => 'nullable|string|max:255',
        ];
    }
}
