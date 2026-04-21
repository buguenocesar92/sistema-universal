<?php

use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| API Routes — Generadas automáticamente desde el JSON de configuración
|--------------------------------------------------------------------------
*/

Route::apiResource('ventas', \App\Http\Controllers\Api\VentaController::class);
Route::apiResource('stock', \App\Http\Controllers\Api\StockController::class);
Route::apiResource('promociones', \App\Http\Controllers\Api\PromocioneController::class);
Route::apiResource('importaciones', \App\Http\Controllers\Api\ImportacioneController::class);
Route::apiResource('productos', \App\Http\Controllers\Api\ProductoController::class);
Route::apiResource('ferias', \App\Http\Controllers\Api\FeriaController::class);
