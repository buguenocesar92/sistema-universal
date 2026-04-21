<?php

namespace Database\Seeders;

use App\Models\Producto;
use Illuminate\Database\Seeder;

class ProductoSeeder extends Seeder
{
    public function run(): void
    {
        Producto::factory(10)->create();
        // O datos de ejemplo fijos:
        // Producto::create([
            'modelo' => fake()->word(),
            'sku' => strtoupper(fake()->lexify('???##')),
            'precio' => fake()->numberBetween(1000, 100000),
            'panel' => fake()->word(),
            'flujo_aire' => fake()->word(),
            'cobertura' => fake()->word(),
            'motor' => fake()->word(),
            'garantia' => fake()->word(),
        // ]);
    }
}
