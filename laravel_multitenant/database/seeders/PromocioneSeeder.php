<?php

namespace Database\Seeders;

use App\Models\Extractores\Promocione;
use Illuminate\Database\Seeder;

class PromocioneSeeder extends Seeder
{
    public function run(): void
    {
        Promocione::factory(10)->create();
        // O datos de ejemplo fijos:
        // Promocione::create([
            'item' => fake()->word(),
            'contacto' => fake()->word(),
            'empresa' => fake()->word(),
            'rut' => fake()->word(),
            'modelo' => fake()->word(),
            'cantidad' => fake()->numberBetween(1000, 100000),
            'neto' => fake()->word(),
            'iva' => fake()->numberBetween(1000, 100000),
        // ]);
    }
}
