<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use \App\Models\Promocione;
use \App\Http\Requests\PromocioneRequest;

class PromocioneController extends Controller
{
    public function index()
    {
        return Promocione::all();
    }

    public function store(PromocioneRequest $request)
    {
        return Promocione::create($request->validated());
    }

    public function show(Promocione $record)
    {
        return $record;
    }

    public function update(PromocioneRequest $request, Promocione $record)
    {
        $record->update($request->validated());
        return $record;
    }

    public function destroy(Promocione $record)
    {
        $record->delete();
        return response()->noContent();
    }
}
