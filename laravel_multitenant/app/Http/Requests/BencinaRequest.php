<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class BencinaRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'fecha' => 'nullable|date',
            'vehiculo' => 'nullable|string|max:255',
            'obra' => 'nullable|string|max:255',
            'monto' => 'required|numeric|min:0',
            'litros' => 'nullable|string|max:255',
            'km' => 'nullable|string|max:255',
            'detalle' => 'nullable|string|max:255',
        ];
    }
}
