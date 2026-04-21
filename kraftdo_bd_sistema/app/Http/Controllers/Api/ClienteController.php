<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use \App\Models\Cliente;
use \App\Http\Requests\ClienteRequest;

class ClienteController extends Controller
{
    public function index()
    {
        return Cliente::all();
    }

    public function store(ClienteRequest $request)
    {
        return Cliente::create($request->validated());
    }

    public function show(Cliente $record)
    {
        return $record;
    }

    public function update(ClienteRequest $request, Cliente $record)
    {
        $record->update($request->validated());
        return $record;
    }

    public function destroy(Cliente $record)
    {
        $record->delete();
        return response()->noContent();
    }
}
