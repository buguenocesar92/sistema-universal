<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use \App\Models\Proveedore;
use \App\Http\Requests\ProveedoreRequest;

class ProveedoreController extends Controller
{
    public function index()
    {
        return Proveedore::all();
    }

    public function store(ProveedoreRequest $request)
    {
        return Proveedore::create($request->validated());
    }

    public function show(Proveedore $record)
    {
        return $record;
    }

    public function update(ProveedoreRequest $request, Proveedore $record)
    {
        $record->update($request->validated());
        return $record;
    }

    public function destroy(Proveedore $record)
    {
        $record->delete();
        return response()->noContent();
    }
}
