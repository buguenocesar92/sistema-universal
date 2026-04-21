<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use \App\Models\Bencina;
use \App\Http\Requests\BencinaRequest;

class BencinaController extends Controller
{
    public function index()
    {
        return Bencina::all();
    }

    public function store(BencinaRequest $request)
    {
        return Bencina::create($request->validated());
    }

    public function show(Bencina $record)
    {
        return $record;
    }

    public function update(BencinaRequest $request, Bencina $record)
    {
        $record->update($request->validated());
        return $record;
    }

    public function destroy(Bencina $record)
    {
        $record->delete();
        return response()->noContent();
    }
}
