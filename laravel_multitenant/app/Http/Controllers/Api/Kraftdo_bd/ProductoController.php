<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use \App\Models\Producto;
use \App\Http\Requests\ProductoRequest;

class ProductoController extends Controller
{
    public function index()
    {
        return Producto::all();
    }

    public function store(ProductoRequest $request)
    {
        return Producto::create($request->validated());
    }

    public function show(Producto $record)
    {
        return $record;
    }

    public function update(ProductoRequest $request, Producto $record)
    {
        $record->update($request->validated());
        return $record;
    }

    public function destroy(Producto $record)
    {
        $record->delete();
        return response()->noContent();
    }
}
