<?php

namespace Database\Seeders;

use App\Models\Kraftdo_bd\Producto;
use Illuminate\Database\Seeder;

class ProductoSeeder extends Seeder
{
    public function run(): void
    {
        Producto::factory(10)->create();
        // O datos de ejemplo fijos:
        // Producto::create([
            'sku' => strtoupper(fake()->lexify('???##')),
            'categoria' => fake()->word(),
            'nombre' => fake()->words(3, true),
            'variante' => fake()->word(),
            'costo_insumo' => fake()->numberBetween(1000, 100000),
            'costo_prod' => fake()->numberBetween(1000, 100000),
            'costo_total' => fake()->numberBetween(1000, 100000),
            'margen' => fake()->numberBetween(1000, 100000),
        // ]);
    }
}
