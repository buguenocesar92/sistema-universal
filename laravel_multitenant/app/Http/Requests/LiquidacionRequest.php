<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class LiquidacionRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'codigo' => 'nullable|string|max:255',
            'obra' => 'nullable|string|max:255',
            'trabajador' => 'nullable|string|max:255',
            'sueldo_base' => 'nullable|string|max:255',
            'dias_laborales' => 'required|numeric|min:0',
            'dias_trabajados' => 'required|numeric|min:0',
            'faltas' => 'nullable|string|max:255',
            'valor_dia' => 'nullable|string|max:255',
            'descuento_faltas' => 'required|numeric|min:0',
            'a_pagar' => 'nullable|string|max:255',
            'quincena_pagada' => 'nullable|string|max:255',
            'saldo' => 'required|numeric|min:0',
        ];
    }
}
