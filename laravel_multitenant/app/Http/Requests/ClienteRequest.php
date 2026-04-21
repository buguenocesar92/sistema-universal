<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class ClienteRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'nombre' => 'nullable|string|max:255',
            'tipo' => 'nullable|string|max:255',
            'whatsapp' => 'nullable|string|max:255',
            'ciudad' => 'nullable|string|max:255',
            'correo' => 'nullable|email',
            'rubro' => 'nullable|string|max:255',
            'canal' => 'nullable|string|max:255',
            'fecha' => 'nullable|date',
            'notas' => 'nullable|string|max:255',
        ];
    }
}
