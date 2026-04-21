<?php

namespace Database\Seeders;

use App\Models\Insumo;
use Illuminate\Database\Seeder;

class InsumoSeeder extends Seeder
{
    public function run(): void
    {
        Insumo::factory(10)->create();
        // O datos de ejemplo fijos:
        // Insumo::create([
            'nombre' => fake()->words(3, true),
            'unidad' => fake()->word(),
            'stock' => fake()->numberBetween(1000, 100000),
            'stock_min' => fake()->word(),
            'alerta' => fake()->word(),
            'costo' => fake()->numberBetween(1000, 100000),
            'proveedor' => fake()->word(),
        // ]);
    }
}
