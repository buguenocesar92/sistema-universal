<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use \App\Models\Pedido;
use \App\Http\Requests\PedidoRequest;

class PedidoController extends Controller
{
    public function index()
    {
        return Pedido::all();
    }

    public function store(PedidoRequest $request)
    {
        return Pedido::create($request->validated());
    }

    public function show(Pedido $record)
    {
        return $record;
    }

    public function update(PedidoRequest $request, Pedido $record)
    {
        $record->update($request->validated());
        return $record;
    }

    public function destroy(Pedido $record)
    {
        $record->delete();
        return response()->noContent();
    }
}
