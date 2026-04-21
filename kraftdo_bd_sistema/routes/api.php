<?php

use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| API Routes — Generadas automáticamente desde el JSON de configuración
|--------------------------------------------------------------------------
*/

Route::apiResource('productos', \App\Http\Controllers\Api\ProductoController::class);
Route::apiResource('proveedores', \App\Http\Controllers\Api\ProveedoreController::class);
Route::apiResource('insumos', \App\Http\Controllers\Api\InsumoController::class);
Route::apiResource('clientes', \App\Http\Controllers\Api\ClienteController::class);
Route::apiResource('pedidos', \App\Http\Controllers\Api\PedidoController::class);
Route::apiResource('caja', \App\Http\Controllers\Api\CajaController::class);
