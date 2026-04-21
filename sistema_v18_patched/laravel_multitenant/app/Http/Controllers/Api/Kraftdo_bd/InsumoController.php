<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use \App\Models\Insumo;
use \App\Http\Requests\InsumoRequest;

class InsumoController extends Controller
{
    public function index()
    {
        return Insumo::all();
    }

    public function store(InsumoRequest $request)
    {
        return Insumo::create($request->validated());
    }

    public function show(Insumo $record)
    {
        return $record;
    }

    public function update(InsumoRequest $request, Insumo $record)
    {
        $record->update($request->validated());
        return $record;
    }

    public function destroy(Insumo $record)
    {
        $record->delete();
        return response()->noContent();
    }
}
