<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use \App\Models\Stock;
use \App\Http\Requests\StockRequest;

class StockController extends Controller
{
    public function index()
    {
        return Stock::all();
    }

    public function store(StockRequest $request)
    {
        return Stock::create($request->validated());
    }

    public function show(Stock $record)
    {
        return $record;
    }

    public function update(StockRequest $request, Stock $record)
    {
        $record->update($request->validated());
        return $record;
    }

    public function destroy(Stock $record)
    {
        $record->delete();
        return response()->noContent();
    }
}
