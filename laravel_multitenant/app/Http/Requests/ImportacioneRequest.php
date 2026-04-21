<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class ImportacioneRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'item' => 'nullable|string|max:255',
            'modelo' => 'nullable|string|max:255',
            'unidades' => 'nullable|string|max:255',
            'pi_numero' => 'nullable|string|max:255',
            'empresa' => 'nullable|string|max:255',
            'rut' => 'nullable|string|max:255',
            'factura' => 'nullable|string|max:255',
            'costo_china' => 'required|numeric|min:0',
            'embarcadero' => 'nullable|string|max:255',
            'agente_aduana' => 'nullable|string|max:255',
            'total_neto' => 'required|numeric|min:0',
            'iva_servicio' => 'nullable|string|max:255',
        ];
    }
}
