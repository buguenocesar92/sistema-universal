<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class StockRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'modelo' => 'nullable|string|max:255',
            'importacion' => 'nullable|string|max:255',
            'ventas' => 'nullable|string|max:255',
            'promociones' => 'nullable|string|max:255',
            'stock_disponible' => 'nullable|string|max:255',
        ];
    }
}
