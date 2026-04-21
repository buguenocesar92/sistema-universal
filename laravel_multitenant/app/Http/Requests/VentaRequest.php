<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class VentaRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'item' => 'nullable|string|max:255',
            'contacto' => 'nullable|string|max:255',
            'tipo_estructura' => 'nullable|string|max:255',
            'empresa' => 'nullable|string|max:255',
            'rut' => 'nullable|string|max:255',
            'factura' => 'nullable|string|max:255',
            'fecha' => 'nullable|date',
            'modelo' => 'nullable|string|max:255',
            'cantidad' => 'required|numeric|min:0',
            'neto' => 'nullable|string|max:255',
            'neto_dsto' => 'nullable|string|max:255',
            'iva' => 'required|numeric|min:0',
        ];
    }
}
