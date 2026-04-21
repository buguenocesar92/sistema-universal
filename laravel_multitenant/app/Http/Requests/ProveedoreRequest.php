<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class ProveedoreRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'nombre' => 'nullable|string|max:255',
            'contacto' => 'nullable|string|max:255',
            'tipo' => 'nullable|string|max:255',
            'despacho' => 'nullable|string|max:255',
            'minimo' => 'nullable|string|max:255',
            'envio_gratis' => 'nullable|string|max:255',
            'notas' => 'nullable|string|max:255',
            'actualizado' => 'nullable|string|max:255',
        ];
    }
}
