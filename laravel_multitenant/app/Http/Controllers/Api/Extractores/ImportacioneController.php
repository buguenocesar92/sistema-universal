<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use \App\Models\Importacione;
use \App\Http\Requests\ImportacioneRequest;

class ImportacioneController extends Controller
{
    public function index()
    {
        return Importacione::all();
    }

    public function store(ImportacioneRequest $request)
    {
        return Importacione::create($request->validated());
    }

    public function show(Importacione $record)
    {
        return $record;
    }

    public function update(ImportacioneRequest $request, Importacione $record)
    {
        $record->update($request->validated());
        return $record;
    }

    public function destroy(Importacione $record)
    {
        $record->delete();
        return response()->noContent();
    }
}
