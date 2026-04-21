<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use \App\Models\Caja;
use \App\Http\Requests\CajaRequest;

class CajaController extends Controller
{
    public function index()
    {
        return Caja::all();
    }

    public function store(CajaRequest $request)
    {
        return Caja::create($request->validated());
    }

    public function show(Caja $record)
    {
        return $record;
    }

    public function update(CajaRequest $request, Caja $record)
    {
        $record->update($request->validated());
        return $record;
    }

    public function destroy(Caja $record)
    {
        $record->delete();
        return response()->noContent();
    }
}
