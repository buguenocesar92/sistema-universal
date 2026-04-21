<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class FacturacionRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'concepto' => 'nullable|string|max:255',
            'abril' => 'nullable|string|max:255',
            'mayo' => 'nullable|string|max:255',
            'julio' => 'nullable|string|max:255',
            'agosto' => 'nullable|string|max:255',
            'septiembre' => 'nullable|string|max:255',
            'octubre' => 'nullable|string|max:255',
            'noviembre' => 'nullable|string|max:255',
            'diciembre' => 'nullable|string|max:255',
            'enero' => 'nullable|string|max:255',
            'febrero' => 'nullable|string|max:255',
            'marzo' => 'nullable|string|max:255',
            'acumulado' => 'nullable|string|max:255',
        ];
    }
}
