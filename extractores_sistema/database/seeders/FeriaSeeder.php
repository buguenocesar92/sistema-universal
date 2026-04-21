<?php

namespace Database\Seeders;

use App\Models\Feria;
use Illuminate\Database\Seeder;

class FeriaSeeder extends Seeder
{
    public function run(): void
    {
        Feria::factory(10)->create();
        // O datos de ejemplo fijos:
        // Feria::create([
            'evento' => fake()->word(),
            'fecha' => fake()->dateTimeBetween('-1 year', 'now'),
            'lugar' => fake()->word(),
            'region' => fake()->word(),
            'tipo' => fake()->word(),
            'relevancia' => fake()->word(),
            'publico' => fake()->word(),
            'costo_stand' => fake()->numberBetween(1000, 100000),
        // ]);
    }
}
