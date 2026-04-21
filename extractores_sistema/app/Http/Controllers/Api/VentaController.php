<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use \App\Models\Venta;
use \App\Http\Requests\VentaRequest;

class VentaController extends Controller
{
    public function index()
    {
        return Venta::all();
    }

    public function store(VentaRequest $request)
    {
        return Venta::create($request->validated());
    }

    public function show(Venta $record)
    {
        return $record;
    }

    public function update(VentaRequest $request, Venta $record)
    {
        $record->update($request->validated());
        return $record;
    }

    public function destroy(Venta $record)
    {
        $record->delete();
        return response()->noContent();
    }
}
