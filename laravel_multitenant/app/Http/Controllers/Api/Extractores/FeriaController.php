<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use \App\Models\Feria;
use \App\Http\Requests\FeriaRequest;

class FeriaController extends Controller
{
    public function index()
    {
        return Feria::all();
    }

    public function store(FeriaRequest $request)
    {
        return Feria::create($request->validated());
    }

    public function show(Feria $record)
    {
        return $record;
    }

    public function update(FeriaRequest $request, Feria $record)
    {
        $record->update($request->validated());
        return $record;
    }

    public function destroy(Feria $record)
    {
        $record->delete();
        return response()->noContent();
    }
}
