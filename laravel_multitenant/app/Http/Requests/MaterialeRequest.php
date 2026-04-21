<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class MaterialeRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'obra' => 'nullable|string|max:255',
            'fecha' => 'nullable|date',
            'detalle' => 'nullable|string|max:255',
            'costo_gym' => 'required|numeric|min:0',
            'costo_nogales' => 'required|numeric|min:0',
            'gastos_generales' => 'nullable|string|max:255',
        ];
    }
}
