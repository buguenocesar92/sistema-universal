<?php

use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| API Routes — Generadas automáticamente desde el JSON de configuración
|--------------------------------------------------------------------------
*/

Route::apiResource('materiales', \App\Http\Controllers\Api\MaterialeController::class);
Route::apiResource('liquidacion', \App\Http\Controllers\Api\LiquidacionController::class);
Route::apiResource('bencina', \App\Http\Controllers\Api\BencinaController::class);
Route::apiResource('facturacion', \App\Http\Controllers\Api\FacturacionController::class);
