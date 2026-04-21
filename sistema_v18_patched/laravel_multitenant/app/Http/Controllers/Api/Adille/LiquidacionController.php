<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use \App\Models\Liquidacion;
use \App\Http\Requests\LiquidacionRequest;

class LiquidacionController extends Controller
{
    public function index()
    {
        return Liquidacion::all();
    }

    public function store(LiquidacionRequest $request)
    {
        return Liquidacion::create($request->validated());
    }

    public function show(Liquidacion $record)
    {
        return $record;
    }

    public function update(LiquidacionRequest $request, Liquidacion $record)
    {
        $record->update($request->validated());
        return $record;
    }

    public function destroy(Liquidacion $record)
    {
        $record->delete();
        return response()->noContent();
    }
}
