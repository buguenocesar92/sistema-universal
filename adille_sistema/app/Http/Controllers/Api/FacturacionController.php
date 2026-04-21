<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use \App\Models\Facturacion;
use \App\Http\Requests\FacturacionRequest;

class FacturacionController extends Controller
{
    public function index()
    {
        return Facturacion::all();
    }

    public function store(FacturacionRequest $request)
    {
        return Facturacion::create($request->validated());
    }

    public function show(Facturacion $record)
    {
        return $record;
    }

    public function update(FacturacionRequest $request, Facturacion $record)
    {
        $record->update($request->validated());
        return $record;
    }

    public function destroy(Facturacion $record)
    {
        $record->delete();
        return response()->noContent();
    }
}
