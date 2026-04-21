<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class FeriaRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'evento' => 'nullable|string|max:255',
            'fecha' => 'nullable|date',
            'lugar' => 'nullable|string|max:255',
            'region' => 'nullable|string|max:255',
            'tipo' => 'nullable|string|max:255',
            'relevancia' => 'nullable|string|max:255',
            'publico' => 'nullable|string|max:255',
            'costo_stand' => 'required|numeric|min:0',
            'contacto' => 'nullable|string|max:255',
            'estado' => 'nullable|string|max:255',
        ];
    }
}
