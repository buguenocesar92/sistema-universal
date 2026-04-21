<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use \App\Models\Materiale;
use \App\Http\Requests\MaterialeRequest;

class MaterialeController extends Controller
{
    public function index()
    {
        return Materiale::all();
    }

    public function store(MaterialeRequest $request)
    {
        return Materiale::create($request->validated());
    }

    public function show(Materiale $record)
    {
        return $record;
    }

    public function update(MaterialeRequest $request, Materiale $record)
    {
        $record->update($request->validated());
        return $record;
    }

    public function destroy(Materiale $record)
    {
        $record->delete();
        return response()->noContent();
    }
}
