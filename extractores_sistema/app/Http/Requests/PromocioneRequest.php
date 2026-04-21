<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class PromocioneRequest extends FormRequest
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
            'empresa' => 'nullable|string|max:255',
            'rut' => 'nullable|string|max:255',
            'modelo' => 'nullable|string|max:255',
            'cantidad' => 'required|numeric|min:0',
            'neto' => 'nullable|string|max:255',
            'iva' => 'required|numeric|min:0',
            'total' => 'required|numeric|min:0',
        ];
    }
}
